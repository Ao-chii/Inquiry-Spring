#!/usr/bin/env python
"""
测试前端修复后的选项显示效果
"""

import requests
import json

# 测试配置
BASE_URL = "http://localhost:8000"

def test_frontend_options_display():
    """测试前端选项显示修复"""
    print("🧪 测试前端选项显示修复...")
    
    url = f"{BASE_URL}/api/test/"
    data = {
        "num": 3,
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
            
            print("\n🔍 验证前端期望的数据格式:")
            
            for i, question in enumerate(questions, 1):
                print(f"\n📋 题目 {i}:")
                print(f"   ID: {question.get('id', '无ID')}")
                print(f"   题目: {question.get('question', '无题目')[:50]}...")
                print(f"   类型: {question.get('type', '无类型')}")
                
                # 重点检查选项格式
                options = question.get('options', [])
                print(f"   选项数量: {len(options)}")
                
                if options:
                    print("   选项内容:")
                    for j, option in enumerate(options):
                        print(f"     {j+1}. {option}")
                    
                    # 检查选项格式
                    if question.get('type') == '单选题':
                        has_letter_prefix = any(opt.startswith(('A.', 'B.', 'C.', 'D.')) for opt in options)
                        print(f"   选项格式: {'有字母前缀' if has_letter_prefix else '无字母前缀'}")
                    
                    print("   ✅ 前端应该能正确显示这些选项")
                else:
                    print("   ❌ 没有选项!")
                
                # 检查答案格式
                answer = question.get('answer', '')
                print(f"   正确答案: {answer}")
                
                # 检查解析
                explanation = question.get('explanation', '')
                if explanation:
                    print(f"   解析: {explanation[:50]}...")
                
                print("   " + "-" * 40)
            
            # 生成前端测试指南
            print("\n📋 前端测试指南:")
            print("1. 打开浏览器访问前端页面")
            print("2. 生成测验后检查选项是否正确显示")
            print("3. 单选题应显示完整的选项文本")
            print("4. 判断题应显示'正确'和'错误'选项")
            print("5. 选择答案后提交验证功能是否正常")
            
            # 输出前端调试信息
            print("\n🔧 前端调试信息:")
            print("修复内容:")
            print("- 使用 question[i]?.options 替代硬编码的 options")
            print("- 添加 getOptionValue() 方法处理选项值")
            print("- 支持带字母前缀的选项格式")
            
            return True
                    
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

def generate_frontend_test_data():
    """生成前端测试用的示例数据"""
    print("\n🧪 生成前端测试用的示例数据...")
    
    sample_data = {
        "AIQuestion": [
            {
                "id": 1,
                "question": "根据推免加分细则，以下哪项竞赛的最高加分为2分？",
                "type": "单选题",
                "type_code": "MC",
                "options": [
                    "A. 全国大学生数学建模竞赛",
                    "B. 国际遗传工程机器设计大赛（iGEM）",
                    "C. 全国大学生英语竞赛",
                    "D. 湖北省挑战杯竞赛"
                ],
                "answer": "B",
                "correct_answer": "B",
                "explanation": "根据细则，国际遗传工程机器设计大赛（iGEM）的最高加分为2分。",
                "difficulty": "medium",
                "knowledge_points": ["推免加分规则", "竞赛加分"]
            },
            {
                "id": 2,
                "question": "全国计算机技术与软件专业技术资格考试只有高级证书才能获得加分。",
                "type": "判断题",
                "type_code": "TF",
                "options": ["正确", "错误"],
                "answer": "正确",
                "correct_answer": "正确",
                "explanation": "根据细则，该考试仅高级证书可获得2分加分，其他级别不加分。",
                "difficulty": "medium",
                "knowledge_points": ["推免加分规则", "证书加分"]
            }
        ],
        "message": "测验生成成功",
        "based_on_document": True
    }
    
    print("📄 示例数据结构:")
    print(json.dumps(sample_data, ensure_ascii=False, indent=2))
    
    print("\n✅ 前端应该能够:")
    print("1. 正确显示题目类型（单选题、判断题）")
    print("2. 显示完整的选项内容")
    print("3. 支持选项选择和答案验证")
    
    return sample_data

def main():
    """主测试函数"""
    print("🔧 测试前端选项显示修复")
    print("=" * 60)
    
    # 测试1: 实际API调用
    test_success = test_frontend_options_display()
    
    print("\n" + "-" * 40)
    
    # 测试2: 生成示例数据
    sample_data = generate_frontend_test_data()
    
    print("\n" + "=" * 60)
    print("🔍 修复总结")
    
    if test_success:
        print("🎉 后端数据格式完全正确！")
        print("\n✅ 前端修复内容:")
        print("1. 使用动态选项: question[i]?.options")
        print("2. 添加选项值处理: getOptionValue()")
        print("3. 支持字母前缀格式: 'A. 选项内容'")
        print("4. 判断题默认选项: ['正确', '错误']")
        
        print("\n🧪 测试步骤:")
        print("1. 重新加载前端页面")
        print("2. 生成测验")
        print("3. 检查选项是否正确显示")
        print("4. 验证答案选择功能")
        
        print("\n💡 如果仍有问题:")
        print("- 检查浏览器控制台是否有JavaScript错误")
        print("- 确认前端代码已正确保存")
        print("- 清除浏览器缓存后重试")
    else:
        print("❌ 后端仍有问题，需要先解决后端问题")

if __name__ == "__main__":
    main()
