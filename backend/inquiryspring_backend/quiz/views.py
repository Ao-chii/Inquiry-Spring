import logging
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .models import Quiz, Question, QuizAttempt, Answer
from ..ai_service_wrapper import ai_service
from ..documents.models import Document

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class TestGenerationView(View):
    """测验生成视图"""

    def get(self, request):
        """获取测验列表或历史"""
        try:
            # 返回最近的测验尝试
            attempts = QuizAttempt.objects.filter(is_completed=True)[:10]
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
        """生成测验"""
        try:
            data = json.loads(request.body)
            
            # 获取参数
            question_count = data.get('num', 5)
            difficulty = data.get('difficulty', 'medium')
            question_types = data.get('types', ['MC', 'TF'])
            topic = data.get('topic', '')
            
            logger.info(f"生成测验请求: 题目数量={question_count}, 难度={difficulty}, 类型={question_types}")

            # 获取最近上传的文档内容
            recent_document = Document.objects.filter(
                is_processed=True
            ).order_by('-uploaded_at').first()

            if recent_document and recent_document.content:
                # 基于文档内容生成测验
                logger.info(f"基于文档生成测验: {recent_document.title}")
                quiz_result = ai_service.generate_quiz(
                    content=recent_document.content,
                    topic=f"基于文档《{recent_document.title}》",
                    question_count=question_count,
                    question_types=question_types,
                    difficulty=difficulty
                )
            else:
                # 没有文档时使用主题生成
                logger.info("没有可用文档，基于主题生成测验")
                quiz_result = ai_service.generate_quiz(
                    topic=topic or "通用知识",
                    question_count=question_count,
                    question_types=question_types,
                    difficulty=difficulty
                )
            
            if "error" in quiz_result:
                return JsonResponse({'error': quiz_result["error"]}, status=500)
            
            # 解析生成的题目
            questions = quiz_result.get("questions", [])
            
            # 格式化为前端期望的格式
            formatted_questions = []
            for i, q in enumerate(questions):
                formatted_q = {
                    'id': i + 1,
                    'question': q.get('question', ''),
                    'type': q.get('type', 'MC'),
                    'options': q.get('options', []),
                    'correct_answer': q.get('correct_answer', ''),
                    'explanation': q.get('explanation', '')
                }
                formatted_questions.append(formatted_q)
            
            logger.info(f"测验生成成功: {len(formatted_questions)}道题目")
            
            return JsonResponse({
                'AIQuestion': formatted_questions,
                'message': '测验生成成功'
            })
            
        except Exception as e:
            logger.error(f"测验生成失败: {e}")
            return JsonResponse({'error': f'生成失败: {str(e)}'}, status=500)


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
