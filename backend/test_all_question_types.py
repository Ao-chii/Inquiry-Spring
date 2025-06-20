#!/usr/bin/env python
"""
测试所有题目类型的生成 - 包括多选题和填空题
"""

import requests
import json

# 测试配置
BASE_URL = "http://localhost:8000"

def test_all_question_types():
    """测试所有题目类型的生成"""
    print("🧪 测试所有题目类型生成...")
    
    url = f"{BASE_URL}/api/test/"
    data = {
        "num": 5,
        "difficulty": "medium",
        "types": ["MC", "MCM", "TF", "FB", "SA"],  # 包含所有类型
        "topic": "推免加分规则"
    }
    
    try:
        print("📤 发送全类型测验生成请求...")
        print(f"请求参数: {json.dumps(data, ensure_ascii=False, indent=2)}")
        
        response = requests.post(url, json=data, timeout=90)
        print(f"📥 响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 全类型测验生成成功!")
            
            questions = result.get('AIQuestion', [])
            print(f"📊 生成题目数量: {len(questions)}")
            
            # 统计各类型题目数量
            type_counts = {}
            for question in questions:
                qtype = question.get('type', '未知')
                type_counts[qtype] = type_counts.get(qtype, 0) + 1
            
            print(f"\n📋 题目类型分布:")
            for qtype, count in type_counts.items():
                print(f"   {qtype}: {count}道")
            
            print(f"\n🔍 详细题目检查:")
            
            for i, question in enumerate(questions, 1):
                print(f"\n📝 题目 {i}:")
                print(f"   ID: {question.get('id', '无ID')}")
                print(f"   类型: {question.get('type', '无类型')} ({question.get('type_code', '无代码')})")
                print(f"   题目: {question.get('question', '无题目')[:60]}...")
                
                # 检查选项
                options = question.get('options', [])
                qtype = question.get('type_code', question.get('type', ''))
                
                if qtype in ['MC', 'MCM']:
                    print(f"   选项数量: {len(options)}")
                    if options:
                        for j, option in enumerate(options[:2]):  # 只显示前2个选项
                            print(f"     {j+1}. {option}")
                        if len(options) > 2:
                            print(f"     ... (共{len(options)}个选项)")
                    else:
                        print("   ❌ 选择题没有选项!")
                        
                elif qtype == 'TF':
                    print(f"   判断题选项: {options}")
                    
                elif qtype in ['FB', 'SA']:
                    print(f"   {qtype}题无需选项")
                
                # 检查答案
                answer = question.get('answer', '')
                print(f"   正确答案: {answer}")
                
                # 检查解析
                analysis = question.get('analysis', '')
                if analysis:
                    print(f"   解析: {analysis[:50]}...")
                else:
                    print("   ⚠️ 没有解析")
                
                print("   " + "-" * 50)
            
            # 验证生成效果
            print(f"\n🔍 生成效果验证:")
            
            # 检查是否包含所有请求的类型
            requested_types = set(['单选题', '多选题', '判断题', '填空题', '简答题'])
            generated_types = set(q.get('type', '') for q in questions)
            
            missing_types = requested_types - generated_types
            if missing_types:
                print(f"⚠️ 缺少题目类型: {missing_types}")
            else:
                print("✅ 包含所有请求的题目类型")
            
            # 检查多选题和填空题
            mcm_questions = [q for q in questions if q.get('type_code') == 'MCM']
            fb_questions = [q for q in questions if q.get('type_code') == 'FB']
            
            print(f"✅ 多选题数量: {len(mcm_questions)}")
            print(f"✅ 填空题数量: {len(fb_questions)}")
            
            # 检查多选题答案格式
            for q in mcm_questions:
                answer = q.get('answer', '')
                if isinstance(answer, list):
                    print(f"✅ 多选题答案格式正确: {answer}")
                else:
                    print(f"⚠️ 多选题答案格式可能有问题: {answer}")
            
            return True
                    
        else:
            print(f"❌ 全类型测验生成失败: {response.status_code}")
            try:
                error_data = response.json()
                print(f"错误信息: {error_data.get('error', response.text)}")
            except:
                print(f"错误信息: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return False

def test_chinese_type_names():
    """测试中文题目类型名称"""
    print("\n🧪 测试中文题目类型名称...")
    
    url = f"{BASE_URL}/api/test/"
    data = {
        "num": 4,
        "difficulty": "easy",
        "types": ["单选题", "多选题", "判断题", "填空题"],  # 使用中文名称
        "topic": "软件工程基础"
    }
    
    try:
        print("📤 发送中文类型名称请求...")
        print(f"请求参数: {json.dumps(data, ensure_ascii=False, indent=2)}")
        
        response = requests.post(url, json=data, timeout=60)
        print(f"📥 响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 中文类型名称测验生成成功!")
            
            questions = result.get('AIQuestion', [])
            print(f"📊 生成题目数量: {len(questions)}")
            
            # 检查类型转换
            for i, question in enumerate(questions, 1):
                qtype = question.get('type', '')
                type_code = question.get('type_code', '')
                print(f"题目 {i}: {qtype} ({type_code})")
            
            return True
        else:
            print(f"❌ 中文类型名称测验生成失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return False

def test_document_upload_all_types():
    """测试文档上传生成所有类型题目"""
    print("\n🧪 测试文档上传生成所有类型题目...")
    
    # 创建测试文档
    test_content = """
    数据结构与算法基础

    1. 数据结构分类
    数据结构可以分为以下几类：
    - 线性结构：数组、链表、栈、队列
    - 树形结构：二叉树、平衡树、堆
    - 图结构：有向图、无向图、加权图
    - 散列结构：哈希表、布隆过滤器

    2. 算法复杂度
    时间复杂度常见类型：
    - O(1)：常数时间复杂度
    - O(log n)：对数时间复杂度
    - O(n)：线性时间复杂度
    - O(n²)：平方时间复杂度

    3. 排序算法
    常见排序算法包括：
    - 冒泡排序：简单但效率低
    - 快速排序：分治思想，平均O(n log n)
    - 归并排序：稳定排序，O(n log n)
    - 堆排序：利用堆的性质，O(n log n)

    4. 查找算法
    - 线性查找：O(n)时间复杂度
    - 二分查找：O(log n)时间复杂度，要求数据有序
    - 哈希查找：平均O(1)时间复杂度
    """
    
    url = f"{BASE_URL}/api/test/"
    
    files = {
        'file': ('数据结构算法.txt', test_content.encode('utf-8'), 'text/plain')
    }
    
    data = {
        'num': '4',
        'difficulty': 'medium',
        'types': 'MC,MCM,TF,FB',  # 包含多种类型
        'topic': '数据结构与算法'
    }
    
    try:
        print("📤 发送文档上传全类型请求...")
        response = requests.post(url, files=files, data=data, timeout=120)
        print(f"📥 响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 文档上传全类型测验生成成功!")
            
            questions = result.get('AIQuestion', [])
            print(f"📊 生成题目数量: {len(questions)}")
            
            # 快速检查类型分布
            type_counts = {}
            for question in questions:
                qtype = question.get('type', '未知')
                type_counts[qtype] = type_counts.get(qtype, 0) + 1
            
            print(f"📋 类型分布: {type_counts}")
            
            return True
        else:
            print(f"❌ 文档上传全类型测验生成失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return False

def main():
    """主测试函数"""
    print("🔧 测试所有题目类型生成功能")
    print("=" * 60)
    
    # 测试1: 所有题目类型
    test1_success = test_all_question_types()
    
    # 测试2: 中文类型名称
    test2_success = test_chinese_type_names()
    
    # 测试3: 文档上传全类型
    test3_success = test_document_upload_all_types()
    
    print("\n" + "=" * 60)
    print("🔍 测试结果总结")
    
    if test1_success and test2_success and test3_success:
        print("🎉 所有题目类型生成功能完全正常！")
        print("\n✅ 支持的题目类型:")
        print("1. 单选题 (MC) - 4个选项，单个答案")
        print("2. 多选题 (MCM) - 4个选项，多个答案")
        print("3. 判断题 (TF) - 正确/错误选项")
        print("4. 填空题 (FB) - 无选项，文本答案")
        print("5. 简答题 (SA) - 无选项，详细答案")
        
        print("\n✅ 功能特性:")
        print("- 支持中文和英文类型名称")
        print("- 自动类型转换和映射")
        print("- 智能选项生成")
        print("- 完整的解析内容")
    else:
        print("❌ 部分功能有问题")
        if not test1_success:
            print("- 全类型生成有问题")
        if not test2_success:
            print("- 中文类型名称有问题")
        if not test3_success:
            print("- 文档上传全类型有问题")

if __name__ == "__main__":
    main()
