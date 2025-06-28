import os
import django
import json
import time
import pandas as pd
from typing import List, Dict

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'inquiryspring_backend.settings')
django.setup()

from inquiryspring_backend.ai_services.rag_engine import RAGEngine
from inquiryspring_backend.ai_services.evaluation_service import EvaluationService

# --- 配置 ---
EVAL_DATA_PATH = 'evaluation_data.json'  # 确保此文件存在于backend目录下
RESULTS_FILE_PATH = 'evaluation_results.json'
MODES_TO_EVALUATE = ['simple', 'graph', 'full']

def load_evaluation_data(file_path: str) -> List[Dict]:
    """加载评估数据集"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def run_evaluation():
    """主评估函数"""
    eval_questions = load_evaluation_data(EVAL_DATA_PATH)
    evaluation_service = EvaluationService()
    all_results = []

    for question_data in eval_questions:
        question_id = question_data['id']
        question = question_data['question']
        doc_id = question_data['document_id']

        print(f"\n{'='*20}\n评估问题: {question_id} - {question}\n{'='*20}")

        for mode in MODES_TO_EVALUATE:
            print(f"\n--- Running in [{mode.upper()}] mode ---")
            
            start_time = time.time()
            
            # 1. 初始化对应模式的RAG引擎
            rag_engine = RAGEngine(document_id=doc_id, mode=mode)
            
            # 2. 检索上下文
            retrieved_chunks = rag_engine.retrieve_relevant_chunks(question)
            retrieval_time = time.time() - start_time
            print(f"检索完成，耗时: {retrieval_time:.2f}s, 检索到 {len(retrieved_chunks)} 个块。")

            # 3. 生成答案
            answer_data = rag_engine.generate_answer_from_context(question, retrieved_chunks)
            answer = answer_data.get('answer', '')
            generation_time = time.time() - start_time - retrieval_time
            print(f"答案生成完成，耗时: {generation_time:.2f}s。")

            # 4. 使用LLM评委进行评估
            print("正在调用LLM评委进行打分...")
            retrieval_relevance = evaluation_service.evaluate_retrieval_relevance(question, retrieved_chunks)
            answer_faithfulness = evaluation_service.evaluate_answer_faithfulness(answer, retrieved_chunks)
            answer_relevance = evaluation_service.evaluate_answer_relevance(question, answer)
            
            # 5. 记录结果
            result_entry = {
                'question_id': question_id,
                'question': question,
                'mode': mode,
                'retrieved_context': [c.content for c in retrieved_chunks],
                'answer': answer,
                'retrieval_relevance_rating': retrieval_relevance['rating'],
                'retrieval_relevance_reasoning': retrieval_relevance['reasoning'],
                'answer_faithfulness_rating': answer_faithfulness['rating'],
                'answer_faithfulness_reasoning': answer_faithfulness['reasoning'],
                'answer_relevance_rating': answer_relevance['rating'],
                'answer_relevance_reasoning': answer_relevance['reasoning'],
            }
            all_results.append(result_entry)

    # 保存所有结果到JSON文件
    with open(RESULTS_FILE_PATH, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    print(f"\n评估全部完成！结果已保存到 {RESULTS_FILE_PATH}")

if __name__ == '__main__':
    run_evaluation() 