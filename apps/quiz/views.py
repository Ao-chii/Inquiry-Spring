from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.generic import ListView, DetailView
import json

from .models import Quiz, Question, QuizAttempt
from apps.documents.models import Document


class QuizListView(ListView):
    """测验列表视图"""
    model = Quiz
    template_name = 'quiz/quiz_list.html'
    context_object_name = 'quizzes'
    paginate_by = 10


class QuizDetailView(DetailView):
    """测验详情视图"""
    model = Quiz
    template_name = 'quiz/quiz_detail.html'
    context_object_name = 'quiz'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['questions'] = self.object.questions.all()
        return context


@csrf_exempt
def quiz_generation_view(request):
    """测验生成视图"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            document_id = data.get('document_id')
            question_count = data.get('question_count', 5)
            difficulty = data.get('difficulty', 2)
            question_types = data.get('question_types', ['MC'])
            
            document = get_object_or_404(Document, id=document_id)
            
            # 创建测验
            quiz = Quiz.objects.create(
                document=document,
                title=f"{document.title} - 测验",
                difficulty_level=difficulty,
                config={
                    'question_count': question_count,
                    'question_types': question_types
                }
            )
            
            # TODO: 集成AI服务生成题目
            # 这里先创建示例题目
            sample_questions = [
                {
                    'content': '这是一道示例选择题？',
                    'type': 'MC',
                    'options': ['选项A', '选项B', '选项C', '选项D'],
                    'correct_answer': '选项A',
                    'explanation': '这是解释说明...'
                }
            ]
            
            for i, q_data in enumerate(sample_questions[:question_count]):
                Question.objects.create(
                    quiz=quiz,
                    content=q_data['content'],
                    question_type=q_data['type'],
                    options=q_data.get('options'),
                    correct_answer=q_data['correct_answer'],
                    explanation=q_data['explanation'],
                    order=i + 1
                )
            
            quiz.total_questions = len(sample_questions[:question_count])
            quiz.save()
            
            return JsonResponse({
                'success': True,
                'quiz_id': quiz.id,
                'message': '测验生成成功'
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': '仅支持POST请求'}, status=405)


@csrf_exempt
def quiz_submission_view(request):
    """测验提交视图"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            quiz_id = data.get('quiz_id')
            answers = data.get('answers', {})
            
            quiz = get_object_or_404(Quiz, id=quiz_id)
            
            # 创建答题记录
            attempt = QuizAttempt.objects.create(
                quiz=quiz,
                answers=answers
            )
            
            # 计算得分
            score = 0
            total_score = 0
            results = []
            
            for question in quiz.questions.all():
                total_score += 1
                user_answer = answers.get(str(question.id), '')
                is_correct = user_answer == question.correct_answer
                
                if is_correct:
                    score += 1
                
                results.append({
                    'question_id': question.id,
                    'question': question.content,
                    'user_answer': user_answer,
                    'correct_answer': question.correct_answer,
                    'is_correct': is_correct,
                    'explanation': question.explanation
                })
            
            # 更新答题记录
            attempt.score = score
            attempt.total_score = total_score
            attempt.is_completed = True
            attempt.save()
            
            return JsonResponse({
                'success': True,
                'attempt_id': attempt.id,
                'score': score,
                'total_score': total_score,
                'accuracy': attempt.accuracy,
                'results': results
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': '仅支持POST请求'}, status=405)


def quiz_form_view(request):
    """测验配置表单视图"""
    documents = Document.objects.all()
    
    context = {
        'documents': documents,
        'difficulty_choices': Quiz.DIFFICULTY_CHOICES,
        'question_types': Question.QUESTION_TYPES,
    }
    
    return render(request, 'quiz/quiz_form.html', context)