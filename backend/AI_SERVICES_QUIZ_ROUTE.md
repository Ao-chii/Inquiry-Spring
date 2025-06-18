# AI Services 小测生成路线图

## 📋 概述

本文档详细描述了AI Services模块中小测生成的完整调用路线，包括所有相关函数、类和数据流。

## 🛣️ 主要路线

### 1. 入口点 (quiz/views.py)

```python
# 用户请求入口
POST /api/test/
├── TestGenerationView.post()
    ├── _handle_file_upload_and_quiz()     # 文档上传生成
    └── _handle_quiz_generation()          # 基于现有文档生成
```

### 2. 文档处理路线

```python
# 文档上传流程
_handle_file_upload_and_quiz()
├── Document.objects.create()              # 创建文档记录
├── process_document_for_rag()             # ai_services/__init__.py
    └── RAGEngine.process_and_embed_document()
        ├── _extract_text_from_file()      # 提取文档内容
        ├── _split_document()              # 文档分块
        └── _embed_and_store_chunks()      # 向量化存储
```

### 3. 核心测验生成路线

```python
# 测验生成核心流程
RAGEngine.handle_quiz()                    # rag_engine.py:88
├── _extract_quiz_constraints()            # 提取用户需求参数
    └── LLMClient.generate_text()          # 解析用户查询
├── _generate_quiz_with_doc()              # 基于文档生成
    ├── retrieve_relevant_chunks()         # 检索相关文档片段
    └── _call_quiz_llm()
└── _generate_quiz_without_doc()           # 基于主题生成
    └── _call_quiz_llm()
```

### 4. LLM调用路线

```python
# LLM调用核心
_call_quiz_llm()                          # rag_engine.py:212
├── PromptManager.render_by_type('quiz')   # 渲染提示词模板
├── LLMClient.generate_text()              # 调用LLM
    ├── GeminiClient.generate_text()       # Gemini API
    └── LocalLLMClient.generate_text()     # 本地模型
└── _process_quiz_response()               # 处理响应
    ├── _parse_json_from_response()        # 解析JSON
    ├── Quiz.objects.create()              # 创建Quiz对象
    └── Question.objects.create()          # 创建Question对象
```

## 🔧 关键函数详解

### 1. 入口函数

#### `process_document_for_rag(document_id, force_reprocess=False)`
- **位置**: `ai_services/__init__.py:8`
- **功能**: 文档RAG处理的统一入口
- **返回**: `bool` - 处理是否成功

#### `RAGEngine.handle_quiz(user_query, document_id=None, ...)`
- **位置**: `ai_services/rag_engine.py:88`
- **功能**: 测验生成的统一处理入口
- **参数**:
  - `user_query`: 用户查询
  - `document_id`: 文档ID（可选）
  - `question_count`: 题目数量
  - `question_types`: 题目类型列表
  - `difficulty`: 难度级别
- **返回**: `Dict[str, Any]` - 包含quiz_data或error

### 2. 核心处理函数

#### `_extract_quiz_constraints(user_query)`
- **位置**: `ai_services/rag_engine.py:184`
- **功能**: 从用户查询中提取测验参数
- **使用LLM**: 是
- **返回**: `Dict` - 包含topic、question_types、difficulty等

#### `_generate_quiz_with_doc(**kwargs)`
- **位置**: `ai_services/rag_engine.py:202`
- **功能**: 基于文档内容生成测验
- **流程**:
  1. 检索相关文档片段
  2. 构建包含参考文本的提示词
  3. 调用LLM生成题目

#### `_generate_quiz_without_doc(**kwargs)`
- **位置**: `ai_services/rag_engine.py:208`
- **功能**: 基于主题生成测验（无文档）
- **流程**: 直接基于主题调用LLM

#### `_call_quiz_llm(**kwargs)`
- **位置**: `ai_services/rag_engine.py:212`
- **功能**: 调用LLM生成测验的核心函数
- **流程**:
  1. 渲染quiz提示词模板
  2. 调用LLM生成文本
  3. 处理响应并保存到数据库

### 3. 提示词管理

#### `PromptManager.render_by_type('quiz', kwargs)`
- **位置**: `ai_services/prompt_manager.py`
- **功能**: 渲染quiz类型的提示词模板
- **模板变量**:
  - `$reference_text_section`: 参考文档内容
  - `$topic`: 主题
  - `$user_requirements`: 用户需求
  - `$question_count`: 题目数量
  - `$question_types`: 题目类型
  - `$difficulty`: 难度级别

### 4. LLM客户端

#### `LLMClient.generate_text(prompt, system_prompt, task_type='quiz', ...)`
- **位置**: `ai_services/llm_client.py:122`
- **功能**: LLM文本生成的基类方法
- **子类实现**:
  - `GeminiClient.generate_text()` - Gemini API调用
  - `LocalLLMClient.generate_text()` - 本地模型调用

### 5. 响应处理

#### `_process_quiz_response(response, topic, difficulty)`
- **位置**: `ai_services/rag_engine.py:219`
- **功能**: 处理LLM响应并保存到数据库
- **流程**:
  1. 解析JSON格式的题目数据
  2. 创建Quiz对象
  3. 创建Question对象
  4. 返回quiz_data

## 📊 数据流

### 输入数据
```python
{
    "user_query": "生成5道Python编程题目",
    "document_id": 123,  # 可选
    "question_count": 5,
    "question_types": ["MC", "TF"],
    "difficulty": "medium"
}
```

### 中间数据 (提示词渲染后)
```python
{
    "topic": "Python编程",
    "reference_text": "文档内容片段...",
    "question_count": 5,
    "question_types": "MC, TF",
    "difficulty": "medium"
}
```

### LLM响应格式
```json
[
    {
        "content": "Python中哪个关键字用于定义函数？",
        "type": "MC",
        "options": ["def", "function", "func", "define"],
        "correct_answer": "A",
        "explanation": "在Python中，def关键字用于定义函数",
        "difficulty": "medium",
        "knowledge_points": ["Python语法", "函数定义"]
    }
]
```

### 最终输出
```python
{
    "quiz_data": [...],  # 题目列表
    "message": "生成成功",
    "processing_time": 2.5
}
```

## 🔍 关键配置

### RAGEngine默认配置
```python
{
    'chunk_size': 1000,
    'chunk_overlap': 200,
    'default_question_count': 5,
    'default_question_types': ['MC', 'TF'],
    'default_difficulty': 'medium'
}
```

### 支持的题目类型
- `MC`: 单选题 (Multiple Choice)
- `MCM`: 多选题 (Multiple Choice Multiple)
- `TF`: 判断题 (True/False)
- `FB`: 填空题 (Fill in the Blank)
- `SA`: 简答题 (Short Answer)

## 🚨 错误处理点

1. **文档处理失败**: `process_document_for_rag()` 返回 False
2. **RAG检索失败**: `retrieve_relevant_chunks()` 返回空列表
3. **LLM调用失败**: `generate_text()` 返回错误
4. **JSON解析失败**: `_parse_json_from_response()` 解析异常
5. **数据库保存失败**: Quiz/Question创建异常

## 📝 使用示例

```python
# 基于文档生成测验
rag_engine = RAGEngine(document_id=123)
result = rag_engine.handle_quiz(
    user_query="生成5道关于Python的测验题",
    question_count=5,
    question_types=["MC", "TF"],
    difficulty="medium"
)

# 基于主题生成测验
rag_engine = RAGEngine()
result = rag_engine.handle_quiz(
    user_query="生成数学题目",
    question_count=3,
    question_types=["MC"],
    difficulty="easy"
)
```

这个路线图展示了从用户请求到最终返回测验题目的完整数据流和函数调用链。
