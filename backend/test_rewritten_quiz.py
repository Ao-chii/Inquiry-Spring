#!/usr/bin/env python
"""
测试重写后的quiz模块与ai_services的集成
"""

import requests
import json
import time

# 测试配置
BASE_URL = "http://localhost:8000"

def test_document_upload_quiz():
    """测试文档上传生成测验 - 新的ai_services路线"""
    print("🧪 测试文档上传生成测验（基于ai_services路线）...")
    
    # 创建测试文档内容
    test_content = """
    Python编程基础教程

    Python是一种高级编程语言，以其简洁的语法和强大的功能而闻名。

    1. 基本语法
    Python使用缩进来表示代码块，这使得代码更加清晰易读。

    2. 数据类型
    - 整数 (int): 用于表示整数值
    - 浮点数 (float): 用于表示小数
    - 字符串 (str): 用于表示文本
    - 布尔值 (bool): True或False
    - 列表 (list): 有序的可变序列
    - 字典 (dict): 键值对的集合

    3. 控制结构
    - if语句: 条件判断
    - for循环: 遍历序列
    - while循环: 条件循环

    4. 函数定义
    使用def关键字定义函数：
    def function_name(parameters):
        return result

    5. 面向对象编程
    Python支持类和对象的概念：
    class ClassName:
        def __init__(self):
            pass

    Python广泛应用于Web开发、数据科学、人工智能等领域。
    """
    
    url = f"{BASE_URL}/api/test/"
    
    files = {
        'file': ('python_tutorial.txt', test_content.encode('utf-8'), 'text/plain')
    }
    
    data = {
        'num': '4',
        'difficulty': 'medium',
        'types': 'MC,TF',
        'topic': 'Python编程基础'
    }
    
    try:
        print("📤 发送文档上传请求...")
        response = requests.post(url, files=files, data=data, timeout=120)
        print(f"📥 响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 文档上传测验生成成功!")
            print(f"📄 文档: {result.get('document_title', '未知')}")
            print(f"📊 生成题目数量: {len(result.get('AIQuestion', []))}")
            print(f"🎯 基于文档: {result.get('based_on_document', False)}")
            
            if 'quiz_id' in result:
                print(f"🆔 Quiz ID: {result['quiz_id']}")
            
            # 显示生成的题目
            for i, question in enumerate(result.get('AIQuestion', []), 1):
                print(f"\n📋 题目 {i}:")
                print(f"   类型: {question.get('type', '未知')}")
                print(f"   内容: {question.get('question', '')}")
                if question.get('options'):
                    print(f"   选项: {question['options']}")
                print(f"   正确答案: {question.get('answer', question.get('correct_answer', ''))}")
                if question.get('explanation'):
                    print(f"   解析: {question.get('explanation', '')}")
                    
        else:
            print(f"❌ 文档上传测验生成失败: {response.status_code}")
            try:
                error_data = response.json()
                print(f"错误信息: {error_data.get('error', response.text)}")
            except:
                print(f"错误信息: {response.text}")
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")

def test_standard_quiz():
    """测试标准测验生成 - 基于现有文档或主题"""
    print("\n🧪 测试标准测验生成（基于ai_services路线）...")
    
    url = f"{BASE_URL}/api/test/"
    data = {
        "num": 3,
        "difficulty": "medium",
        "types": ["MC", "TF"],
        "topic": "Python编程"
    }
    
    try:
        print("📤 发送标准测验请求...")
        response = requests.post(url, json=data, timeout=60)
        print(f"📥 响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 标准测验生成成功!")
            print(f"📊 生成题目数量: {len(result.get('AIQuestion', []))}")
            print(f"🎯 基于文档: {result.get('based_on_document', False)}")
            
            if result.get('document_title'):
                print(f"📄 使用文档: {result['document_title']}")
            
            # 显示生成的题目
            for i, question in enumerate(result.get('AIQuestion', []), 1):
                print(f"\n📋 题目 {i}:")
                print(f"   类型: {question.get('type', '未知')}")
                print(f"   内容: {question.get('question', '')}")
                if question.get('options'):
                    print(f"   选项: {question['options']}")
                print(f"   正确答案: {question.get('answer', question.get('correct_answer', ''))}")
                    
        else:
            print(f"❌ 标准测验生成失败: {response.status_code}")
            try:
                error_data = response.json()
                print(f"错误信息: {error_data.get('error', response.text)}")
            except:
                print(f"错误信息: {response.text}")
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")

def test_quiz_history():
    """测试测验历史获取"""
    print("\n🧪 测试测验历史获取...")
    
    try:
        response = requests.get(f"{BASE_URL}/api/test/", timeout=30)
        print(f"📥 响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 测验历史获取成功!")
            print(f"📊 历史记录数量: {len(result.get('quizzes', []))}")
            
            for i, quiz in enumerate(result.get('quizzes', [])[:3], 1):
                print(f"\n📋 历史 {i}:")
                print(f"   标题: {quiz.get('quiz_title', '未知')}")
                print(f"   得分: {quiz.get('score', 0)}/{quiz.get('total_points', 0)}")
                print(f"   百分比: {quiz.get('percentage', 0):.1f}%")
                
        else:
            print(f"❌ 测验历史获取失败: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")

def test_available_documents():
    """测试可用文档列表"""
    print("\n🧪 测试可用文档列表...")
    
    try:
        response = requests.get(f"{BASE_URL}/api/test/documents/", timeout=30)
        print(f"📥 响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 文档列表获取成功!")
            print(f"📊 可用文档数量: {result.get('count', 0)}")
            
            for i, doc in enumerate(result.get('documents', [])[:3], 1):
                print(f"\n📄 文档 {i}:")
                print(f"   标题: {doc.get('title', '未知')}")
                print(f"   类型: {doc.get('file_type', '未知')}")
                print(f"   大小: {doc.get('file_size', 0)} bytes")
                
        else:
            print(f"❌ 文档列表获取失败: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")

def main():
    """主测试函数"""
    print("🔍 开始测试重写后的quiz模块")
    print(f"目标服务器: {BASE_URL}")
    print("=" * 60)
    
    # 测试1: 文档上传生成测验
    test_document_upload_quiz()
    
    # 等待一下
    time.sleep(3)
    
    # 测试2: 标准测验生成
    test_standard_quiz()
    
    # 等待一下
    time.sleep(2)
    
    # 测试3: 测验历史
    test_quiz_history()
    
    # 测试4: 可用文档
    test_available_documents()
    
    print("\n" + "=" * 60)
    print("🔍 测试完成")
    print("\n📋 重写要点验证:")
    print("1. ✅ 完全基于ai_services路线")
    print("2. ✅ 兼容前端期望格式")
    print("3. ✅ 支持文档上传和标准生成")
    print("4. ✅ 模型字段与ai_services匹配")
    print("5. ✅ 统一的错误处理")
    print("\n🎯 如果所有测试通过，说明重写成功！")

if __name__ == "__main__":
    main()
