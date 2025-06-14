#!/usr/bin/env python
"""
403错误调试测试脚本
用于测试项目文档上传的403 Forbidden错误
"""

import requests
import json
import sys
import os

# 测试配置
BASE_URL = "http://localhost:8000"
TEST_ENDPOINTS = [
    "/health",
    "/api/projects/test/",
    "/api/projects/1/documents/",
    "/api/projects/1749890204035/documents/",
]

def test_endpoint(method, endpoint, data=None, files=None):
    """测试单个端点"""
    url = BASE_URL + endpoint
    
    print(f"\n{'='*60}")
    print(f"测试: {method} {endpoint}")
    print(f"完整URL: {url}")
    
    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            if files:
                response = requests.post(url, data=data, files=files, timeout=10)
            else:
                response = requests.post(url, json=data, timeout=10)
        elif method == "OPTIONS":
            response = requests.options(url, timeout=10)
        else:
            print(f"不支持的方法: {method}")
            return
        
        print(f"状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        
        if response.status_code == 403:
            print("❌ 403 FORBIDDEN ERROR!")
            print(f"响应内容: {response.text}")
        elif response.status_code == 200:
            print("✅ 请求成功!")
            try:
                json_data = response.json()
                print(f"JSON响应: {json.dumps(json_data, indent=2, ensure_ascii=False)}")
            except:
                print(f"文本响应: {response.text}")
        else:
            print(f"⚠️ 其他状态码: {response.status_code}")
            print(f"响应内容: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ 连接错误: Django服务器可能没有运行")
    except requests.exceptions.Timeout:
        print("❌ 请求超时")
    except Exception as e:
        print(f"❌ 请求异常: {e}")

def test_file_upload(endpoint):
    """测试文件上传"""
    print(f"\n{'='*60}")
    print(f"测试文件上传: POST {endpoint}")
    
    # 创建测试文件
    test_content = "这是一个测试文档内容。\n用于测试项目文档上传功能。"
    
    try:
        files = {
            'file': ('test_document.txt', test_content, 'text/plain')
        }
        
        url = BASE_URL + endpoint
        response = requests.post(url, files=files, timeout=10)
        
        print(f"状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        
        if response.status_code == 403:
            print("❌ 文件上传403错误!")
            print(f"响应内容: {response.text}")
        elif response.status_code == 200:
            print("✅ 文件上传成功!")
            try:
                json_data = response.json()
                print(f"JSON响应: {json.dumps(json_data, indent=2, ensure_ascii=False)}")
            except:
                print(f"文本响应: {response.text}")
        else:
            print(f"⚠️ 文件上传状态码: {response.status_code}")
            print(f"响应内容: {response.text}")
            
    except Exception as e:
        print(f"❌ 文件上传异常: {e}")

def main():
    """主测试函数"""
    print("🔍 开始403错误调试测试")
    print(f"目标服务器: {BASE_URL}")
    
    # 1. 测试健康检查
    test_endpoint("GET", "/health")
    
    # 2. 测试项目相关端点
    for endpoint in TEST_ENDPOINTS[1:]:
        # GET测试
        test_endpoint("GET", endpoint)
        
        # OPTIONS测试（CORS预检）
        test_endpoint("OPTIONS", endpoint)
        
        # POST测试（空数据）
        test_endpoint("POST", endpoint, data={})
    
    # 3. 测试文件上传
    test_file_upload("/api/projects/1/documents/")
    test_file_upload("/api/projects/1749890204035/documents/")
    
    print(f"\n{'='*60}")
    print("🔍 调试测试完成")
    print("\n📋 检查要点:")
    print("1. 如果所有请求都403 → Django全局配置问题")
    print("2. 如果只有projects相关403 → URL路由问题")
    print("3. 如果health正常但projects异常 → 应用级别问题")
    print("4. 检查Django控制台是否有调试日志输出")

if __name__ == "__main__":
    main()
