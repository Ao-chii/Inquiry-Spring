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
            logger.info(f"=== 测验生成请求开始 ===")
            logger.info(f"请求方法: {request.method}")
            logger.info(f"请求路径: {request.path}")
            logger.info(f"请求头: {dict(request.headers)}")
            logger.info(f"请求体: {request.body}")
            logger.info(f"文件: {list(request.FILES.keys())}")

            # 检查是否有文件上传
            if request.FILES.get('file'):
                logger.info("处理文档上传测验生成")
                return self._handle_document_upload_quiz(request)
            else:
                logger.info("处理标准测验生成")
                return self._handle_standard_quiz(request)

        except Exception as e:
            logger.error(f"测验生成失败: {e}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return JsonResponse({'error': f'生成失败: {str(e)}'}, status=500)

    def _handle_document_upload_quiz(self, request):
        """处理文档上传并生成测验 - 严格按照ai_services路线"""
        try:
            uploaded_file = request.FILES['file']

            # 解析参数 - 兼容前端格式
            question_count = int(request.POST.get('num', 5))
            difficulty = request.POST.get('difficulty', 'medium')
            question_types_str = request.POST.get('types', 'MC,TF')
            question_types_raw = question_types_str.split(',') if isinstance(question_types_str, str) else question_types_str
            topic = request.POST.get('topic', '')

            # 转换前端题目类型为ai_services期望的格式
            question_types = self._convert_frontend_types_to_ai_types(question_types_raw)

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
            logger.info(f"开始处理标准测验生成")
            logger.info(f"请求体内容: {request.body}")

            data = json.loads(request.body)
            logger.info(f"解析后的数据: {data}")

            # 解析参数 - 兼容前端testReq格式
            question_count = data.get('question_count', data.get('num', 5))
            difficulty = data.get('difficulty', 'medium')
            question_types_raw = data.get('question_types', data.get('types', ['MC', 'TF']))
            topic = data.get('topic', '')
            document_id = data.get('document_id')  # 可选：指定文档ID

            logger.info(f"解析的参数: question_count={question_count}, difficulty={difficulty}, question_types_raw={question_types_raw}, topic={topic}, document_id={document_id}")

            # 转换前端题目类型为ai_services期望的格式
            question_types = self._convert_frontend_types_to_ai_types(question_types_raw)

            logger.info(f"标准测验生成: 题目数量={question_count}, 难度={difficulty}, 原始类型={question_types_raw}, 转换后类型={question_types}")

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
            # 检查是否有错误 - 只有当error不为None时才认为是错误
            if 'error' in quiz_result and quiz_result['error'] is not None:
                error_msg = quiz_result['error']
                logger.error(f"ai_services返回错误: {error_msg}")
                return JsonResponse({'error': error_msg}, status=500)

            # 记录ai_services返回的完整结果用于调试
            logger.info(f"ai_services返回结果: {quiz_result}")

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

        # 前端题目类型映射（兼容前端期望的中文名称）
        frontend_type_mapping = {
            '单选题': 'MC',
            '多选题': 'MCM',
            '判断题': 'TF',
            '填空题': 'FB',
            '简答题': 'SA'
        }

        for i, q in enumerate(quiz_data):
            logger.info(f"处理题目 {i+1}: {q}")

            # 获取题目类型 - ai_services可能已经将type改为question_type
            question_type = q.get('type', q.get('question_type', 'MC')).upper()

            # 获取选项
            options = q.get('options', [])

            # 标准化选项格式 - 确保选项是统一的格式
            standardized_options = []
            if options:
                for opt in options:
                    if isinstance(opt, dict):
                        # ai_services返回的格式: {"text": "内容", "id": "A"}
                        standardized_options.append(opt)
                    elif isinstance(opt, str):
                        # 字符串格式，需要转换
                        # 假设格式为 "A. 内容" 或直接是内容
                        if '. ' in opt and len(opt) > 2:
                            parts = opt.split('. ', 1)
                            if len(parts) == 2:
                                standardized_options.append({"text": parts[1], "id": parts[0]})
                            else:
                                # 如果分割失败，使用索引作为ID
                                standardized_options.append({"text": opt, "id": chr(65 + len(standardized_options))})
                        else:
                            standardized_options.append({"text": opt, "id": chr(65 + len(standardized_options))})
                options = standardized_options

            # 根据题目类型处理选项
            if question_type == 'MC' and not options:
                logger.warning(f"题目 {i+1} 是单选题但没有选项，生成默认选项")
                options = [
                    {"text": "选项A", "id": "A"},
                    {"text": "选项B", "id": "B"},
                    {"text": "选项C", "id": "C"},
                    {"text": "选项D", "id": "D"}
                ]

            elif question_type == 'MCM' and not options:
                logger.warning(f"题目 {i+1} 是多选题但没有选项，生成默认选项")
                options = [
                    {"text": "选项A", "id": "A"},
                    {"text": "选项B", "id": "B"},
                    {"text": "选项C", "id": "C"},
                    {"text": "选项D", "id": "D"}
                ]

            elif question_type == 'TF':
                if not options:
                    options = [
                        {"text": "正确", "id": "A"},
                        {"text": "错误", "id": "B"}
                    ]

            elif question_type == 'FB':
                # 填空题不需要选项
                options = []

            elif question_type == 'SA':
                # 简答题不需要选项
                options = []

            # 获取正确答案
            correct_answer = q.get('correct_answer', '')

            # 基于ai_services的实际输出格式进行转换
            explanation = q.get('explanation', '')
            formatted_q = {
                'id': i + 1,
                'question': q.get('content', ''),  # ai_services使用'content'字段
                'type': type_mapping.get(question_type, question_type),  # 转换为中文类型名
                'type_code': question_type,  # 保留原始类型代码
                'options': options,
                'answer': correct_answer,  # 前端期望'answer'字段
                'correct_answer': correct_answer,  # 保持兼容性
                'explanation': explanation,  # 保持兼容性
                'analysis': explanation,  # 前端期望'analysis'字段
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

    def _convert_frontend_types_to_ai_types(self, frontend_types):
        """将前端题目类型转换为ai_services期望的格式"""
        # 前端到ai_services的类型映射
        type_mapping = {
            '单选题': 'MC',
            '多选题': 'MCM',
            '判断题': 'TF',
            '填空题': 'FB',
            '简答题': 'SA',
            # 兼容直接传递代码的情况
            'MC': 'MC',
            'MCM': 'MCM',
            'TF': 'TF',
            'FB': 'FB',
            'SA': 'SA'
        }

        converted_types = []
        for ftype in frontend_types:
            ftype = ftype.strip()  # 去除空格
            ai_type = type_mapping.get(ftype, ftype)  # 如果找不到映射，使用原值
            converted_types.append(ai_type)

        logger.info(f"题目类型转换: {frontend_types} -> {converted_types}")
        return converted_types

    def _get_file_type(self, filename):
        """根据文件名确定文件类型"""
        extension = filename.lower().split('.')[-1] if '.' in filename else 'unknown'
        return extension




@api_view(['POST'])
def quiz_submit(request):
    """提交测验答案 - 支持前端直接答案评判"""
    try:
        data = request.data
        answers = data.get('answers', [])
        questions = data.get('questions', [])

        logger.info(f"收到答案提交: {len(answers)}个答案, {len(questions)}道题目")

        # 如果没有提供questions，尝试从quiz_id获取
        if not questions and data.get('quiz_id'):
            try:
                quiz = Quiz.objects.get(id=data.get('quiz_id'))
                questions = list(quiz.questions.all().values(
                    'id', 'content', 'question_type', 'correct_answer', 'options'
                ))
            except Quiz.DoesNotExist:
                return Response({'error': '测验不存在'}, status=status.HTTP_404_NOT_FOUND)

        if not questions:
            return Response({'error': '缺少题目信息'}, status=status.HTTP_400_BAD_REQUEST)

        # 评判答案
        results = []
        total_score = 0
        total_questions = len(questions)

        for i, question in enumerate(questions):
            user_answer = answers[i] if i < len(answers) else None
            correct_answer = question.get('correct_answer', '')
            question_type = question.get('question_type', question.get('type', 'MC'))

            is_correct = _evaluate_answer(user_answer, correct_answer, question_type)

            result = {
                'question_index': i,
                'question_id': question.get('id'),
                'user_answer': user_answer,
                'correct_answer': correct_answer,
                'is_correct': is_correct,
                'question_type': question_type
            }
            results.append(result)

            if is_correct:
                total_score += 1

        percentage = (total_score / total_questions * 100) if total_questions > 0 else 0

        logger.info(f"答案评判完成: {total_score}/{total_questions} = {percentage:.1f}%")

        return Response({
            'message': '答案评判完成',
            'results': results,
            'score': total_score,
            'total_questions': total_questions,
            'percentage': percentage
        })

    except Exception as e:
        logger.error(f"答案提交失败: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def _evaluate_answer(user_answer, correct_answer, question_type):
    """评判单个答案是否正确"""
    if user_answer is None or user_answer == '':
        return False

    # 标准化答案格式
    def normalize_answer(answer):
        if isinstance(answer, list):
            return sorted([str(a).strip().upper() for a in answer])
        return str(answer).strip().upper()

    # 判断题特殊处理
    if question_type.upper() == 'TF':
        return _evaluate_true_false_answer(user_answer, correct_answer)

    user_normalized = normalize_answer(user_answer)
    correct_normalized = normalize_answer(correct_answer)

    if question_type.upper() == 'MCM':  # 多选题
        # 多选题需要完全匹配
        return user_normalized == correct_normalized
    elif question_type.upper() == 'MC':  # 单选题
        return user_normalized == correct_normalized
    elif question_type.upper() in ['FB', 'SA']:  # 填空题和简答题
        # 对于填空题和简答题，进行更宽松的匹配
        user_text = str(user_answer).strip().lower()
        correct_text = str(correct_answer).strip().lower()

        # 完全匹配
        if user_text == correct_text:
            return True

        # 包含匹配（用户答案包含正确答案或反之）
        if correct_text in user_text or user_text in correct_text:
            return True

        return False

    return user_normalized == correct_normalized


def _evaluate_true_false_answer(user_answer, correct_answer):
    """专门处理判断题的答案评判"""
    # 将各种可能的"正确"表示统一化
    true_values = {
        # 中文表示
        '正确', '对', '是', '真', '√', '✓',
        # 英文表示
        'TRUE', 'T', 'YES', 'Y', 'RIGHT', 'CORRECT',
        # 选项ID
        'A'  # 通常A选项是"正确"
    }

    # 将各种可能的"错误"表示统一化
    false_values = {
        # 中文表示
        '错误', '错', '否', '假', '×', '✗',
        # 英文表示
        'FALSE', 'F', 'NO', 'N', 'WRONG', 'INCORRECT',
        # 选项ID
        'B'  # 通常B选项是"错误"
    }

    # 标准化用户答案和正确答案
    user_normalized = str(user_answer).strip().upper()
    correct_normalized = str(correct_answer).strip().upper()

    # 判断用户答案的真假值
    user_is_true = user_normalized in true_values
    user_is_false = user_normalized in false_values

    # 判断正确答案的真假值
    correct_is_true = correct_normalized in true_values
    correct_is_false = correct_normalized in false_values

    # 如果无法识别用户答案，返回False
    if not (user_is_true or user_is_false):
        return False

    # 如果无法识别正确答案，使用直接比较
    if not (correct_is_true or correct_is_false):
        return user_normalized == correct_normalized

    # 比较真假值
    return (user_is_true and correct_is_true) or (user_is_false and correct_is_false)


@api_view(['POST'])
def evaluate_answers(request):
    """评判答案 - 前端专用接口"""
    try:
        data = request.data
        answers = data.get('answers', [])
        questions = data.get('questions', [])

        logger.info(f"评判答案请求: {len(answers)}个答案, {len(questions)}道题目")

        if not questions:
            return Response({'error': '缺少题目信息'}, status=status.HTTP_400_BAD_REQUEST)

        # 评判每个答案
        results = []
        correct_count = 0

        for i, question in enumerate(questions):
            user_answer = answers[i] if i < len(answers) else None
            correct_answer = question.get('answer', question.get('correct_answer', ''))
            question_type = question.get('type_code', question.get('question_type', 'MC'))

            is_correct = _evaluate_answer(user_answer, correct_answer, question_type)

            if is_correct:
                correct_count += 1

            results.append({
                'index': i,
                'is_correct': is_correct,
                'user_answer': user_answer,
                'correct_answer': correct_answer
            })

        total_questions = len(questions)
        percentage = (correct_count / total_questions * 100) if total_questions > 0 else 0

        return Response({
            'results': results,
            'correct_count': correct_count,
            'total_questions': total_questions,
            'percentage': percentage,
            'message': f'评判完成：{correct_count}/{total_questions} 正确'
        })

    except Exception as e:
        logger.error(f"答案评判失败: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
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



