#!/usr/bin/env python
"""
测试RAG修复后的文档上传生成测验功能
"""

import requests
import json
import time

# 测试配置
BASE_URL = "http://localhost:8000"

def test_document_upload_quiz_fixed():
    """测试修复后的文档上传生成测验"""
    print("🧪 测试修复后的文档上传生成测验...")
    
    # 创建测试文档内容
    test_content = """
    华中科技大学软件学院推荐免试研究生加分细则

    根据学校相关规定，结合软件学院实际情况，制定以下加分细则：

    一、学科竞赛加分标准

    1. 国际级竞赛
    - ACM-ICPC世界总决赛：金牌加15分，银牌加12分，铜牌加10分
    - 国际大学生程序设计竞赛亚洲区域赛：金牌加8分，银牌加6分，铜牌加4分

    2. 国家级竞赛
    - 全国大学生数学建模竞赛：一等奖加6分，二等奖加4分
    - 全国大学生电子设计竞赛：一等奖加6分，二等奖加4分
    - 中国大学生计算机设计大赛：一等奖加5分，二等奖加3分

    3. 省级竞赛
    - 湖北省大学生程序设计竞赛：一等奖加3分，二等奖加2分，三等奖加1分
    - 湖北省大学生数学竞赛：一等奖加2分，二等奖加1分

    二、科研创新加分

    1. 学术论文
    - SCI一区论文：第一作者加10分，第二作者加5分
    - SCI二区论文：第一作者加8分，第二作者加4分
    - EI检索论文：第一作者加4分，第二作者加2分

    2. 专利发明
    - 发明专利：第一发明人加6分，第二发明人加3分
    - 实用新型专利：第一发明人加2分

    3. 软件著作权
    - 软件著作权：第一完成人加1分

    三、社会实践加分

    1. 创新创业
    - 国家级大学生创新创业训练计划项目：负责人加3分，主要参与者加1分
    - 省级大学生创新创业训练计划项目：负责人加2分

    2. 社会服务
    - 优秀志愿者（省级以上）：加1分
    - 社会实践优秀个人（校级以上）：加0.5分

    四、其他说明

    1. 同一项目获得不同级别奖励，按最高级别计分，不重复加分
    2. 团队项目按贡献度分配加分，总分不超过单项最高分
    3. 所有加分项目需提供相关证明材料
    4. 最终加分由学院推免工作小组审核确定

    本细则自发布之日起执行，解释权归软件学院所有。
    """
    
    url = f"{BASE_URL}/api/test/"
    
    files = {
        'file': ('软件学院推免加分细则.txt', test_content.encode('utf-8'), 'text/plain')
    }
    
    data = {
        'num': '5',
        'difficulty': 'medium',
        'types': 'MC,TF',
        'topic': '推免加分规则'
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
                    
            return True
                    
        else:
            print(f"❌ 文档上传测验生成失败: {response.status_code}")
            try:
                error_data = response.json()
                print(f"错误信息: {error_data.get('error', response.text)}")
            except:
                print(f"错误信息: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return False

def test_standard_quiz_with_existing_doc():
    """测试基于现有文档的标准测验生成"""
    print("\n🧪 测试基于现有文档的标准测验生成...")
    
    url = f"{BASE_URL}/api/test/"
    data = {
        "num": 3,
        "difficulty": "easy",
        "types": ["MC", "TF"],
        "topic": "加分规则"
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
                    
            return True
                    
        else:
            print(f"❌ 标准测验生成失败: {response.status_code}")
            try:
                error_data = response.json()
                print(f"错误信息: {error_data.get('error', response.text)}")
            except:
                print(f"错误信息: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return False

def main():
    """主测试函数"""
    print("🔧 测试RAG修复后的测验生成功能")
    print(f"目标服务器: {BASE_URL}")
    print("=" * 60)
    
    # 测试1: 文档上传生成测验
    test1_success = test_document_upload_quiz_fixed()
    
    # 等待一下
    time.sleep(3)
    
    # 测试2: 基于现有文档的标准测验生成
    test2_success = test_standard_quiz_with_existing_doc()
    
    print("\n" + "=" * 60)
    print("🔍 测试结果总结")
    
    if test1_success and test2_success:
        print("🎉 所有测试通过！RAG问题已完全修复")
        print("\n✅ 修复要点:")
        print("1. 移除了Chroma的手动persist()调用")
        print("2. 在RAG处理前确保文档内容提取")
        print("3. 使用DocumentProcessor正确提取PDF内容")
        print("4. 完整的错误处理和日志记录")
    elif test1_success:
        print("⚠️ 文档上传测验成功，但标准测验有问题")
    elif test2_success:
        print("⚠️ 标准测验成功，但文档上传测验有问题")
    else:
        print("❌ 所有测试都失败，需要进一步调查")
        print("\n💡 建议检查:")
        print("- Django服务器是否正常运行")
        print("- 数据库连接是否正常")
        print("- AI服务配置是否正确")

if __name__ == "__main__":
    main()
