#!/usr/bin/env python
"""
测试选项修复效果
"""

import requests
import json

# 测试配置
BASE_URL = "http://localhost:8000"

def test_quiz_options():
    """测试题目选项是否正确显示"""
    print("🧪 测试题目选项修复效果...")
    
    url = f"{BASE_URL}/api/test/"
    data = {
        "num": 2,
        "difficulty": "medium",
        "types": ["MC", "TF"],
        "topic": "推免加分规则"
    }
    
    try:
        print("📤 发送测验生成请求...")
        response = requests.post(url, json=data, timeout=60)
        print(f"📥 响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 测验生成成功!")
            
            questions = result.get('AIQuestion', [])
            print(f"📊 生成题目数量: {len(questions)}")
            
            # 详细检查每道题目
            for i, question in enumerate(questions, 1):
                print(f"\n📋 题目 {i} 详细检查:")
                print(f"   ID: {question.get('id', '无ID')}")
                print(f"   题目: {question.get('question', '无题目')[:50]}...")
                print(f"   类型: {question.get('type', '无类型')}")
                print(f"   类型代码: {question.get('type_code', '无代码')}")
                
                # 重点检查选项
                options = question.get('options', [])
                print(f"   选项数量: {len(options)}")
                if options:
                    print("   选项内容:")
                    for j, option in enumerate(options):
                        print(f"     {j+1}. {option}")
                    print("   ✅ 选项正常显示")
                else:
                    print("   ❌ 选项缺失!")
                
                # 检查答案
                answer = question.get('answer', '')
                print(f"   正确答案: {answer}")
                
                # 检查解析
                explanation = question.get('explanation', '')
                if explanation:
                    print(f"   解析: {explanation[:50]}...")
                else:
                    print("   ⚠️ 没有解析")
                
                print("   " + "-" * 40)
            
            # 验证修复效果
            print("\n🔍 修复效果验证:")
            
            # 检查1: 所有题目是否有选项
            questions_with_options = [q for q in questions if q.get('options')]
            print(f"✅ 选项完整性: {len(questions_with_options)}/{len(questions)} 道题有选项")
            
            # 检查2: 单选题选项数量
            mc_questions = [q for q in questions if q.get('type_code') == 'MC']
            mc_with_4_options = [q for q in mc_questions if len(q.get('options', [])) >= 4]
            print(f"✅ 单选题选项: {len(mc_with_4_options)}/{len(mc_questions)} 道单选题有足够选项")
            
            # 检查3: 判断题选项
            tf_questions = [q for q in questions if q.get('type_code') == 'TF']
            tf_with_options = [q for q in tf_questions if '正确' in str(q.get('options', [])) and '错误' in str(q.get('options', []))]
            print(f"✅ 判断题选项: {len(tf_with_options)}/{len(tf_questions)} 道判断题有正确/错误选项")
            
            # 检查4: 题目类型显示
            type_display_correct = all(q.get('type') in ['单选题', '多选题', '判断题', '填空题', '简答题'] for q in questions)
            print(f"✅ 题目类型显示: {'正确' if type_display_correct else '错误'}")
            
            # 总体评估
            all_good = (
                len(questions_with_options) == len(questions) and
                len(mc_with_4_options) == len(mc_questions) and
                len(tf_with_options) == len(tf_questions) and
                type_display_correct
            )
            
            if all_good:
                print("\n🎉 所有检查通过！选项问题已完全修复")
                return True
            else:
                print("\n⚠️ 部分检查未通过，仍有问题需要解决")
                return False
                    
        else:
            print(f"❌ 测验生成失败: {response.status_code}")
            try:
                error_data = response.json()
                print(f"错误信息: {error_data.get('error', response.text)}")
            except:
                print(f"错误信息: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return False

def test_document_upload():
    """测试文档上传生成的题目选项"""
    print("\n🧪 测试文档上传生成题目选项...")
    
    # 创建测试文档
    test_content = """
    计算机网络基础知识

    1. OSI七层模型
    OSI（开放系统互连）模型包括七个层次：
    - 物理层：负责比特流的传输
    - 数据链路层：负责帧的传输
    - 网络层：负责数据包的路由
    - 传输层：负责端到端的数据传输
    - 会话层：负责会话的建立和管理
    - 表示层：负责数据的格式化和加密
    - 应用层：为应用程序提供网络服务

    2. TCP/IP协议
    TCP/IP是互联网的核心协议族：
    - TCP：传输控制协议，提供可靠的数据传输
    - IP：网际协议，负责数据包的路由
    - UDP：用户数据报协议，提供不可靠但快速的传输
    """
    
    url = f"{BASE_URL}/api/test/"
    
    files = {
        'file': ('计算机网络基础.txt', test_content.encode('utf-8'), 'text/plain')
    }
    
    data = {
        'num': '2',
        'difficulty': 'easy',
        'types': 'MC,TF',
        'topic': '计算机网络'
    }
    
    try:
        print("📤 发送文档上传请求...")
        response = requests.post(url, files=files, data=data, timeout=120)
        print(f"📥 响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 文档上传测验生成成功!")
            
            questions = result.get('AIQuestion', [])
            print(f"📊 生成题目数量: {len(questions)}")
            
            # 快速检查选项
            all_have_options = True
            for i, question in enumerate(questions, 1):
                options = question.get('options', [])
                question_type = question.get('type', '未知')
                
                print(f"📋 题目 {i}: {question_type}, 选项数量: {len(options)}")
                
                if not options:
                    print(f"   ❌ 题目 {i} 没有选项!")
                    all_have_options = False
                else:
                    print(f"   ✅ 题目 {i} 有选项: {options}")
            
            return all_have_options
        else:
            print(f"❌ 文档上传测验生成失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return False

def main():
    """主测试函数"""
    print("🔧 测试选项修复效果")
    print(f"目标服务器: {BASE_URL}")
    print("=" * 60)
    
    # 测试1: 标准测验选项
    test1_success = test_quiz_options()
    
    # 测试2: 文档上传测验选项
    test2_success = test_document_upload()
    
    print("\n" + "=" * 60)
    print("🔍 测试结果总结")
    
    if test1_success and test2_success:
        print("🎉 选项问题完全修复！")
        print("\n✅ 修复内容:")
        print("1. 正确处理ai_services返回的question_type字段")
        print("2. 单选题自动生成4个选项（如果缺失）")
        print("3. 判断题自动生成正确/错误选项")
        print("4. 题目类型正确显示为中文名称")
        print("5. 完整的选项验证和日志记录")
    else:
        print("❌ 仍有问题需要解决")
        if not test1_success:
            print("- 标准测验选项有问题")
        if not test2_success:
            print("- 文档上传测验选项有问题")

if __name__ == "__main__":
    main()
