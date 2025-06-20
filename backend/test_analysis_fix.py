#!/usr/bin/env python
"""
测试解析字段修复效果
"""

import requests
import json

# 测试配置
BASE_URL = "http://localhost:8000"

def test_analysis_field():
    """测试解析字段是否正确返回"""
    print("🧪 测试解析字段修复...")
    
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
            
            print("\n🔍 检查解析字段:")
            
            for i, question in enumerate(questions, 1):
                print(f"\n📋 题目 {i}:")
                print(f"   题目: {question.get('question', '无题目')[:50]}...")
                print(f"   类型: {question.get('type', '无类型')}")
                
                # 重点检查解析字段
                explanation = question.get('explanation', '')
                analysis = question.get('analysis', '')
                
                print(f"   explanation字段: {'有内容' if explanation else '无内容'}")
                print(f"   analysis字段: {'有内容' if analysis else '无内容'}")
                
                if explanation:
                    print(f"   explanation内容: {explanation[:100]}...")
                
                if analysis:
                    print(f"   analysis内容: {analysis[:100]}...")
                
                # 检查字段一致性
                if explanation and analysis:
                    if explanation == analysis:
                        print("   ✅ explanation和analysis字段内容一致")
                    else:
                        print("   ⚠️ explanation和analysis字段内容不一致")
                elif explanation and not analysis:
                    print("   ❌ 有explanation但没有analysis")
                elif not explanation and analysis:
                    print("   ❌ 有analysis但没有explanation")
                else:
                    print("   ❌ 两个字段都没有内容")
                
                print("   " + "-" * 40)
            
            # 验证修复效果
            print("\n🔍 修复效果验证:")
            
            # 检查1: 所有题目是否有解析
            questions_with_explanation = [q for q in questions if q.get('explanation')]
            questions_with_analysis = [q for q in questions if q.get('analysis')]
            
            print(f"✅ explanation字段: {len(questions_with_explanation)}/{len(questions)} 道题有内容")
            print(f"✅ analysis字段: {len(questions_with_analysis)}/{len(questions)} 道题有内容")
            
            # 检查2: 字段一致性
            consistent_fields = all(
                q.get('explanation') == q.get('analysis') 
                for q in questions 
                if q.get('explanation') or q.get('analysis')
            )
            print(f"✅ 字段一致性: {'一致' if consistent_fields else '不一致'}")
            
            # 总体评估
            all_good = (
                len(questions_with_analysis) == len(questions) and
                consistent_fields
            )
            
            if all_good:
                print("\n🎉 解析字段问题已完全修复！")
                print("前端现在应该能正确显示解析内容")
                return True
            else:
                print("\n⚠️ 仍有问题需要解决")
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

def test_document_upload_analysis():
    """测试文档上传生成的解析字段"""
    print("\n🧪 测试文档上传生成的解析字段...")
    
    # 创建测试文档
    test_content = """
    软件工程项目管理

    1. 项目生命周期
    软件项目通常包括以下阶段：
    - 需求分析：明确项目目标和功能需求
    - 设计阶段：制定系统架构和详细设计
    - 开发阶段：编码实现功能模块
    - 测试阶段：验证系统功能和性能
    - 部署阶段：系统上线和用户培训
    - 维护阶段：持续优化和问题修复

    2. 项目管理方法
    - 瀑布模型：线性顺序的开发方法
    - 敏捷开发：迭代增量的开发方法
    - Scrum：敏捷开发的具体实践框架
    """
    
    url = f"{BASE_URL}/api/test/"
    
    files = {
        'file': ('软件工程项目管理.txt', test_content.encode('utf-8'), 'text/plain')
    }
    
    data = {
        'num': '2',
        'difficulty': 'easy',
        'types': 'MC,TF',
        'topic': '项目管理'
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
            
            # 快速检查解析字段
            all_have_analysis = True
            for i, question in enumerate(questions, 1):
                analysis = question.get('analysis', '')
                explanation = question.get('explanation', '')
                
                print(f"📋 题目 {i}: analysis={'有' if analysis else '无'}, explanation={'有' if explanation else '无'}")
                
                if not analysis:
                    print(f"   ❌ 题目 {i} 没有analysis字段!")
                    all_have_analysis = False
                else:
                    print(f"   ✅ 题目 {i} 有analysis: {analysis[:50]}...")
            
            return all_have_analysis
        else:
            print(f"❌ 文档上传测验生成失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return False

def main():
    """主测试函数"""
    print("🔧 测试解析字段修复")
    print("=" * 60)
    
    # 测试1: 标准测验解析字段
    test1_success = test_analysis_field()
    
    # 测试2: 文档上传测验解析字段
    test2_success = test_document_upload_analysis()
    
    print("\n" + "=" * 60)
    print("🔍 测试结果总结")
    
    if test1_success and test2_success:
        print("🎉 解析字段问题完全修复！")
        print("\n✅ 修复内容:")
        print("1. 后端同时返回explanation和analysis字段")
        print("2. 两个字段内容完全一致")
        print("3. 兼容前端期望的analysis字段")
        print("4. 保持explanation字段的向后兼容性")
        
        print("\n🧪 前端验证:")
        print("1. 重新生成测验")
        print("2. 点击'查看解析'按钮")
        print("3. 应该能看到完整的解析内容")
        print("4. 解析内容应该详细说明答案原因")
    else:
        print("❌ 仍有问题需要解决")
        if not test1_success:
            print("- 标准测验解析字段有问题")
        if not test2_success:
            print("- 文档上传测验解析字段有问题")

if __name__ == "__main__":
    main()
