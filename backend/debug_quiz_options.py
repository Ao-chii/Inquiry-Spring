#!/usr/bin/env python
"""
调试quiz选项缺失问题
"""

import os
import sys
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'inquiryspring_backend.settings')
django.setup()

from inquiryspring_backend.ai_services.rag_engine import RAGEngine
from inquiryspring_backend.documents.models import Document
from inquiryspring_backend.quiz.models import Quiz, Question
import logging

# 设置详细日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_quiz_generation_debug():
    """调试测验生成过程"""
    print("🔍 调试测验生成过程...")
    
    # 1. 获取最新的已处理文档
    try:
        document = Document.objects.filter(is_processed=True).order_by('-id').first()
        if not document:
            print("❌ 没有找到已处理的文档")
            return False
        
        print(f"✅ 使用文档: {document.title} (ID: {document.id})")
        
    except Exception as e:
        print(f"❌ 获取文档失败: {e}")
        return False
    
    # 2. 创建RAG引擎并生成测验
    try:
        rag_engine = RAGEngine(document_id=document.id)
        print("✅ RAG引擎创建成功")
        
        # 生成测验
        user_query = "生成2道关于推免加分规则的测验题目"
        quiz_result = rag_engine.handle_quiz(
            user_query=user_query,
            document_id=document.id,
            question_count=2,
            question_types=['MC', 'TF'],
            difficulty='medium'
        )
        
        print(f"✅ 测验生成完成")
        print(f"📊 quiz_result keys: {list(quiz_result.keys())}")
        
        # 检查返回的数据
        if 'error' in quiz_result:
            print(f"❌ 生成错误: {quiz_result['error']}")
            return False
        
        quiz_data = quiz_result.get('quiz_data', [])
        print(f"📋 quiz_data 数量: {len(quiz_data)}")
        
        # 详细检查每道题
        for i, q in enumerate(quiz_data):
            print(f"\n📝 题目 {i+1} 详细信息:")
            print(f"   content: {q.get('content', '无内容')}")
            print(f"   type: {q.get('type', '无类型')}")
            print(f"   options: {q.get('options', '无选项')}")
            print(f"   correct_answer: {q.get('correct_answer', '无答案')}")
            print(f"   explanation: {q.get('explanation', '无解析')}")
            print(f"   所有字段: {list(q.keys())}")
        
        # 3. 检查数据库中保存的数据
        if 'quiz_id' in quiz_result:
            quiz_id = quiz_result['quiz_id']
            print(f"\n🗄️ 检查数据库中的Quiz (ID: {quiz_id})...")
            
            try:
                quiz_obj = Quiz.objects.get(id=quiz_id)
                questions = Question.objects.filter(quiz=quiz_obj)
                
                print(f"📊 数据库中的题目数量: {questions.count()}")
                
                for i, question in enumerate(questions):
                    print(f"\n📝 数据库题目 {i+1}:")
                    print(f"   content: {question.content}")
                    print(f"   question_type: {question.question_type}")
                    print(f"   options: {question.options}")
                    print(f"   correct_answer: {question.correct_answer}")
                    print(f"   explanation: {question.explanation}")
                    
            except Exception as e:
                print(f"❌ 检查数据库失败: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测验生成失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_prompt_template():
    """测试提示词模板"""
    print("\n🔍 检查提示词模板...")
    
    try:
        from inquiryspring_backend.ai_services.prompt_manager import PromptManager
        
        # 渲染测试提示词
        test_vars = {
            'topic': '推免加分规则',
            'user_requirements': '生成2道测验题目',
            'question_count': 2,
            'question_types': ['MC', 'TF'],
            'difficulty': 'medium',
            'reference_text': '这是测试参考文本...'
        }
        
        rendered_prompt = PromptManager.render_by_type('quiz', test_vars)
        print("✅ 提示词渲染成功")
        print(f"📝 渲染后的提示词长度: {len(rendered_prompt)} 字符")
        print(f"📝 提示词预览:\n{rendered_prompt[:500]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ 提示词测试失败: {e}")
        return False

def test_llm_direct():
    """直接测试LLM响应"""
    print("\n🔍 直接测试LLM响应...")
    
    try:
        from inquiryspring_backend.ai_services.llm_client import LLMClientFactory
        
        llm_client = LLMClientFactory.create_client()
        print("✅ LLM客户端创建成功")
        
        # 简单的测试提示词
        test_prompt = """请生成1道关于软件工程的单选题，严格按以下JSON格式返回：
```json
[
{
    "content": "什么是软件工程？",
    "type": "MC",
    "options": ["A. 软件开发方法", "B. 编程语言", "C. 操作系统", "D. 数据库"],
    "correct_answer": "A",
    "explanation": "软件工程是关于软件开发的系统化方法",
    "difficulty": "medium",
    "knowledge_points": ["软件工程基础"]
}
]
```"""
        
        response = llm_client.generate_text(
            prompt=test_prompt,
            system_prompt="你是一个测验出题专家。请严格按照JSON格式生成题目。",
            task_type='quiz'
        )
        
        print("✅ LLM响应获取成功")
        print(f"📝 响应内容: {response.get('text', '无内容')}")
        
        # 尝试解析响应
        from inquiryspring_backend.ai_services.rag_engine import RAGEngine
        rag_engine = RAGEngine()
        parsed_data = rag_engine._parse_json_from_response(response.get('text', '[]'))
        
        print(f"📊 解析后的数据: {parsed_data}")
        
        return True
        
    except Exception as e:
        print(f"❌ LLM测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("🔧 调试quiz选项缺失问题")
    print("=" * 60)
    
    # 测试1: 提示词模板
    test1_success = test_prompt_template()
    
    print("\n" + "-" * 40)
    
    # 测试2: 直接LLM测试
    test2_success = test_llm_direct()
    
    print("\n" + "-" * 40)
    
    # 测试3: 完整测验生成流程
    test3_success = test_quiz_generation_debug()
    
    print("\n" + "=" * 60)
    print("🔍 调试结果总结")
    
    if test1_success and test2_success and test3_success:
        print("🎉 所有测试通过，问题可能在前端显示")
    else:
        print("❌ 发现问题:")
        if not test1_success:
            print("- 提示词模板有问题")
        if not test2_success:
            print("- LLM响应有问题")
        if not test3_success:
            print("- 测验生成流程有问题")
    
    print("\n💡 下一步调试建议:")
    print("1. 检查前端JavaScript代码中的选项显示逻辑")
    print("2. 检查API响应的完整JSON结构")
    print("3. 验证数据库中的options字段是否正确保存")

if __name__ == "__main__":
    main()
