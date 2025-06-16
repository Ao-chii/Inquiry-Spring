import logging
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .models import Quiz, Question, QuizAttempt, Answer
from ..ai_services.rag_engine import RAGEngine
from ..ai_services import process_document_for_rag
from ..documents.models import Document

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class TestGenerationView(View):
    """测验生成视图 - 完全基于ai_services路线"""

    def get(self, request):
        """获取测验历史"""
        try:
            attempts = QuizAttempt.objects.filter(is_completed=True).order_by('-completed_at')[:10]
            quiz_list = []

            for attempt in attempts:
                quiz_list.append({
                    'id': attempt.id,
                    'quiz_title': attempt.quiz.title,
                    'score': attempt.score,
                    'total_points': attempt.total_points,
                    'percentage': (attempt.score / attempt.total_points * 100) if attempt.total_points > 0 else 0,
                    'completed_at': attempt.completed_at.isoformat() if attempt.completed_at else None
                })

            return JsonResponse({
                'quizzes': quiz_list,
                'message': '获取测验列表成功'
            })

        except Exception as e:
            logger.error(f"获取测验列表失败: {e}")
            return JsonResponse({'error': str(e)}, status=500)

    def post(self, request):
        """生成测验 - 统一入口，完全依赖ai_services"""
        try:
            # 检查是否有文件上传
            if request.FILES.get('file'):
                return self._handle_document_upload_quiz(request)
            else:
                return self._handle_standard_quiz(request)

        except Exception as e:
            logger.error(f"测验生成失败: {e}")
            return JsonResponse({'error': f'生成失败: {str(e)}'}, status=500)

    def _handle_document_upload_quiz(self, request):
        """处理文档上传并生成测验 - 严格按照ai_services路线"""
        try:
            uploaded_file = request.FILES['file']

            # 解析参数 - 兼容前端格式
            question_count = int(request.POST.get('num', 5))
            difficulty = request.POST.get('difficulty', 'medium')
            question_types_str = request.POST.get('types', 'MC,TF')
            question_types = question_types_str.split(',') if isinstance(question_types_str, str) else question_types_str
            topic = request.POST.get('topic', '')

            logger.info(f"文档上传测验生成: 文件={uploaded_file.name}, 题目数量={question_count}")

            # 1. 创建文档记录
            document = Document.objects.create(
                title=uploaded_file.name,
                file=uploaded_file,
                file_type=self._get_file_type(uploaded_file.name),
                file_size=uploaded_file.size,
                is_processed=False
            )

            # 2. 提取文档内容
            logger.info(f"开始提取文档内容: {document.id}")
            content_extracted = self._extract_document_content(document)

            if not content_extracted:
                logger.error(f"文档内容提取失败: {document.id}")
                return JsonResponse({
                    'error': f'文档内容提取失败，无法生成测验。文档ID: {document.id}'
                }, status=500)

            # 3. RAG处理 - 使用ai_services统一入口
            logger.info(f"开始RAG处理文档: {document.id}")
            rag_success = process_document_for_rag(document.id, force_reprocess=True)

            if not rag_success:
                logger.error(f"文档RAG处理失败: {document.id}")
                return JsonResponse({
                    'error': f'文档处理失败，无法生成测验。文档ID: {document.id}'
                }, status=500)

            # 3. 调用ai_services生成测验 - 完全依赖RAGEngine.handle_quiz
            rag_engine = RAGEngine(document_id=document.id)

            user_query = f"基于文档《{document.title}》生成{question_count}道{difficulty}难度的测验题目"
            if topic:
                user_query += f"，重点关注{topic}相关内容"

            quiz_result = rag_engine.handle_quiz(
                user_query=user_query,
                document_id=document.id,
                question_count=question_count,
                question_types=question_types,
                difficulty=difficulty
            )

            # 4. 处理ai_services返回结果
            return self._process_ai_services_result(quiz_result, document)

        except Exception as e:
            logger.error(f"文档上传测验生成失败: {e}")
            return JsonResponse({'error': f'文档上传生成失败: {str(e)}'}, status=500)

    def _handle_standard_quiz(self, request):
        """处理标准测验生成 - 基于现有文档或主题"""
        try:
            data = json.loads(request.body)

            # 解析参数 - 兼容前端testReq格式
            question_count = data.get('num', 5)
            difficulty = data.get('difficulty', 'medium')
            question_types = data.get('types', ['MC', 'TF'])
            topic = data.get('topic', '')
            document_id = data.get('document_id')  # 可选：指定文档ID

            logger.info(f"标准测验生成: 题目数量={question_count}, 难度={difficulty}, 类型={question_types}")

            # 确定目标文档
            target_document = None
            if document_id:
                try:
                    target_document = Document.objects.get(id=document_id, is_processed=True)
                    logger.info(f"使用指定文档: {target_document.title}")
                except Document.DoesNotExist:
                    logger.warning(f"指定的文档ID {document_id} 不存在或未处理")

            if not target_document:
                # 获取最新的已处理文档
                target_document = Document.objects.filter(
                    is_processed=True
                ).order_by('-uploaded_at').first()

                if target_document:
                    logger.info(f"使用最新文档: {target_document.title}")

            # 调用ai_services生成测验
            if target_document:
                # 基于文档生成
                rag_engine = RAGEngine(document_id=target_document.id)
                user_query = f"基于文档《{target_document.title}》生成{question_count}道{difficulty}难度的测验题目"
                if topic:
                    user_query += f"，重点关注{topic}相关内容"

                quiz_result = rag_engine.handle_quiz(
                    user_query=user_query,
                    document_id=target_document.id,
                    question_count=question_count,
                    question_types=question_types,
                    difficulty=difficulty
                )
            else:
                # 基于主题生成
                logger.info("没有可用文档，基于主题生成测验")
                rag_engine = RAGEngine()
                user_query = f"生成关于{topic or '通用知识'}的{question_count}道{difficulty}难度的测验题目"

                quiz_result = rag_engine.handle_quiz(
                    user_query=user_query,
                    question_count=question_count,
                    question_types=question_types,
                    difficulty=difficulty
                )

            # 处理ai_services返回结果
            return self._process_ai_services_result(quiz_result, target_document)

        except Exception as e:
            logger.error(f"标准测验生成失败: {e}")
            return JsonResponse({'error': f'生成失败: {str(e)}'}, status=500)

    def _process_ai_services_result(self, quiz_result, document=None):
        """处理ai_services返回的结果，转换为前端期望格式"""
        try:
            # 检查是否有错误
            if 'error' in quiz_result:
                error_msg = quiz_result['error']
                logger.error(f"ai_services返回错误: {error_msg}")
                return JsonResponse({'error': error_msg}, status=500)

            # 获取quiz_data - ai_services已经处理并保存到数据库
            quiz_data = quiz_result.get('quiz_data', [])
            logger.info(f"从ai_services获取的quiz_data: {quiz_data}")

            if not quiz_data:
                logger.error("ai_services未返回有效的quiz_data")
                return JsonResponse({'error': '未能生成有效的测验题目'}, status=500)

            # 转换为前端期望的格式
            formatted_questions = self._convert_to_frontend_format(quiz_data)
            logger.info(f"转换后的formatted_questions: {formatted_questions}")

            logger.info(f"测验生成成功: {len(formatted_questions)}道题目")

            # 构建响应
            response_data = {
                'AIQuestion': formatted_questions,
                'message': '测验生成成功'
            }

            # 添加文档信息（如果有）
            if document:
                response_data.update({
                    'document_id': document.id,
                    'document_title': document.title,
                    'based_on_document': True
                })
            else:
                response_data['based_on_document'] = False

            # 添加ai_services返回的额外信息
            if 'quiz_id' in quiz_result:
                response_data['quiz_id'] = quiz_result['quiz_id']

            return JsonResponse(response_data)

        except Exception as e:
            logger.error(f"处理ai_services结果失败: {e}")
            return JsonResponse({'error': f'处理结果失败: {str(e)}'}, status=500)

    def _convert_to_frontend_format(self, quiz_data):
        """将ai_services的quiz_data转换为前端期望的格式"""
        formatted_questions = []

        # 题目类型映射
        type_mapping = {
            'MC': '单选题',
            'MCM': '多选题',
            'TF': '判断题',
            'FB': '填空题',
            'SA': '简答题'
        }

        for i, q in enumerate(quiz_data):
            logger.info(f"处理题目 {i+1}: {q}")

            # 获取题目类型 - ai_services可能已经将type改为question_type
            question_type = q.get('type', q.get('question_type', 'MC')).upper()

            # 获取选项
            options = q.get('options', [])

            # 如果是选择题但没有选项，生成默认选项
            if question_type == 'MC' and not options:
                logger.warning(f"题目 {i+1} 是选择题但没有选项，生成默认选项")
                options = ['A. 选项A', 'B. 选项B', 'C. 选项C', 'D. 选项D']

            # 如果是判断题，确保有正确的选项
            elif question_type == 'TF':
                if not options:
                    options = ['正确', '错误']

            # 获取正确答案
            correct_answer = q.get('correct_answer', '')

            # 基于ai_services的实际输出格式进行转换
            formatted_q = {
                'id': i + 1,
                'question': q.get('content', ''),  # ai_services使用'content'字段
                'type': type_mapping.get(question_type, question_type),  # 转换为中文类型名
                'type_code': question_type,  # 保留原始类型代码
                'options': options,
                'answer': correct_answer,  # 前端期望'answer'字段
                'correct_answer': correct_answer,  # 保持兼容性
                'explanation': q.get('explanation', ''),
                'difficulty': q.get('difficulty', 'medium'),
                'knowledge_points': q.get('knowledge_points', [])
            }

            # 只添加有效题目
            if formatted_q['question']:
                formatted_questions.append(formatted_q)
                logger.info(f"题目 {i+1} 转换完成: type={formatted_q['type']}, options_count={len(formatted_q['options'])}")
            else:
                logger.warning(f"跳过无效题目: {q}")

        return formatted_questions

    def _extract_document_content(self, document):
        """提取文档内容"""
        try:
            from inquiryspring_backend.documents.document_processor import DocumentProcessor
            processor = DocumentProcessor()

            # 保存文件到临时位置进行处理
            import tempfile
            import os

            with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{document.file_type}') as temp_file:
                document.file.seek(0)
                temp_file.write(document.file.read())
                temp_file_path = temp_file.name

            # 使用DocumentProcessor提取内容
            result = processor.extract_text(temp_file_path, document.title)

            # 清理临时文件
            os.unlink(temp_file_path)

            if result['success']:
                document.content = result['content']
                document.metadata = result['metadata']
                document.save()
                logger.info(f"文档内容提取成功: {len(result['content'])} 字符")
                return True
            else:
                logger.error(f"文档内容提取失败: {result['error']}")
                return False

        except Exception as e:
            logger.error(f"文档内容提取异常: {e}")
            return False

    def _get_file_type(self, filename):
        """根据文件名确定文件类型"""
        extension = filename.lower().split('.')[-1] if '.' in filename else 'unknown'
        return extension




@api_view(['POST'])
def quiz_submit(request):
    """提交测验答案"""
    try:
        data = request.data
        quiz_id = data.get('quiz_id')
        answers = data.get('answers', [])
        
        if not quiz_id:
            return Response({'error': '缺少测验ID'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            quiz = Quiz.objects.get(id=quiz_id)
        except Quiz.DoesNotExist:
            return Response({'error': '测验不存在'}, status=status.HTTP_404_NOT_FOUND)
        
        # 创建测验尝试
        attempt = QuizAttempt.objects.create(quiz=quiz)
        
        # 处理答案
        total_score = 0
        total_points = 0
        
        for answer_data in answers:
            question_id = answer_data.get('question_id')
            user_answer = answer_data.get('answer', '')
            
            try:
                question = Question.objects.get(id=question_id, quiz=quiz)
                is_correct = user_answer.strip().lower() == question.correct_answer.strip().lower()
                points_earned = question.points if is_correct else 0
                
                Answer.objects.create(
                    attempt=attempt,
                    question=question,
                    user_answer=user_answer,
                    is_correct=is_correct,
                    points_earned=points_earned
                )
                
                total_score += points_earned
                total_points += question.points
                
            except Question.DoesNotExist:
                continue
        
        # 更新尝试结果
        attempt.score = total_score
        attempt.total_points = total_points
        attempt.is_completed = True
        attempt.save()
        
        return Response({
            'message': '测验提交成功',
            'score': total_score,
            'total_points': total_points,
            'percentage': (total_score / total_points * 100) if total_points > 0 else 0
        })
        
    except Exception as e:
        logger.error(f"测验提交失败: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def quiz_history(request):
    """获取测验历史"""
    try:
        attempts = QuizAttempt.objects.filter(is_completed=True)[:20]
        history = []
        
        for attempt in attempts:
            history.append({
                'id': attempt.id,
                'quiz_title': attempt.quiz.title,
                'score': attempt.score,
                'total_points': attempt.total_points,
                'percentage': (attempt.score / attempt.total_points * 100) if attempt.total_points > 0 else 0,
                'completed_at': attempt.completed_at.isoformat() if attempt.completed_at else None
            })
        
        return Response({'history': history})
        
    except Exception as e:
        logger.error(f"获取测验历史失败: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def quiz_analysis(request, attempt_id):
    """获取测验分析"""
    try:
        attempt = QuizAttempt.objects.get(id=attempt_id)
        answers = Answer.objects.filter(attempt=attempt)

        analysis = {
            'quiz_title': attempt.quiz.title,
            'total_score': attempt.score,
            'total_points': attempt.total_points,
            'percentage': (attempt.score / attempt.total_points * 100) if attempt.total_points > 0 else 0,
            'questions': []
        }

        for answer in answers:
            question_analysis = {
                'question': answer.question.question_text,
                'user_answer': answer.user_answer,
                'correct_answer': answer.question.correct_answer,
                'is_correct': answer.is_correct,
                'explanation': answer.question.explanation,
                'points_earned': answer.points_earned,
                'total_points': answer.question.points
            }
            analysis['questions'].append(question_analysis)

        return Response(analysis)

    except QuizAttempt.DoesNotExist:
        return Response({'error': '测验尝试不存在'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"获取测验分析失败: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)





@api_view(['GET'])
def available_documents(request):
    """获取可用于生成测验的文档列表"""
    try:
        documents = Document.objects.filter(is_processed=True).order_by('-uploaded_at')[:20]

        doc_list = []
        for doc in documents:
            doc_list.append({
                'id': doc.id,
                'title': doc.title,
                'file_type': doc.file_type,
                'file_size': doc.file_size,
                'uploaded_at': doc.uploaded_at.isoformat(),
                'processed_at': doc.processed_at.isoformat() if doc.processed_at else None
            })

        return Response({
            'documents': doc_list,
            'count': len(doc_list)
        })

    except Exception as e:
        logger.error(f"获取文档列表失败: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



