import logging
import json
from typing import List
from .llm_client import LLMClientFactory
from inquiryspring_backend.documents.models import DocumentChunk

logger = logging.getLogger(__name__)

class EvaluationService:
    """
    使用LLM作为评委来评估RAG系统性能的服务。
    """
    def __init__(self, llm_client=None):
        self.llm_client = llm_client or LLMClientFactory.create_client()

    def _get_llm_as_judge_response(self, prompt: str) -> dict:
        """调用LLM评委并解析其JSON响应。"""
        try:
            response = self.llm_client.generate_text(prompt, task_type='evaluation')
            text_response = response.get('text', '{}')
            
            # 从Markdown代码块中提取JSON
            if '```json' in text_response:
                text_response = text_response.split('```json\n')[1].split('```')[0]
            
            parsed = json.loads(text_response)
            return {
                'rating': parsed.get('rating', 0),
                'reasoning': parsed.get('reasoning', 'No reasoning provided.')
            }
        except (json.JSONDecodeError, AttributeError) as e:
            logger.error(f"解析LLM评委响应失败: {e}. 响应: {text_response}")
            return {'rating': 0, 'reasoning': f"Failed to parse LLM response: {e}"}

    def evaluate_retrieval_relevance(self, question: str, context_chunks: List[DocumentChunk]) -> dict:
        """评估检索到的上下文与问题的相关性。"""
        if not context_chunks:
            return {'rating': 0, 'reasoning': 'No context provided.'}
        
        context_str = "\n---\n".join([f"Chunk {i+1}:\n{chunk.content}" for i, chunk in enumerate(context_chunks)])
        
        prompt = f"""你是一个公正的RAG系统评估专家。你的任务是评估检索到的上下文是否与用户问题高度相关。

        请基于以下问题和上下文，对上下文的整体相关性进行评分，分数为1到5分。
        - 5分: 上下文非常相关，包含了回答问题所需的所有关键信息。
        - 3分: 上下文部分相关，但可能缺少一些关键信息或包含一些噪音。
        - 1分: 上下文完全不相关。

        问题:
        "{question}"

        检索到的上下文:
        {context_str}

        请以JSON格式返回你的评分和理由，格式如下：
        ```json
        {{
          "rating": <你的评分>,
          "reasoning": "<你的评分理由>"
        }}
        ```
        """
        return self._get_llm_as_judge_response(prompt)

    def evaluate_answer_faithfulness(self, answer: str, context_chunks: List[DocumentChunk]) -> dict:
        """评估答案在多大程度上被上下文所支持（忠实度）。"""
        if not context_chunks:
            return {'rating': 1, 'reasoning': 'No context was provided to base the answer on.'}
        
        context_str = "\n---\n".join([chunk.content for chunk in context_chunks])
        
        prompt = f"""你是一个严格的事实核查员。你的任务是评估一个答案是否完全基于给定的上下文信息，是否存在编造或幻觉。

        请基于以下上下文和答案，对答案的忠实度进行评分，分数为1到5分。
        - 5分: 答案中的每一句话都完全由上下文支持。
        - 3分: 答案大部分由上下文支持，但包含少量无法验证的细节。
        - 1分: 答案包含与上下文无关或相矛盾的信息（存在幻觉）。

        上下文:
        {context_str}

        生成的答案:
        "{answer}"

        请以JSON格式返回你的评分和理由：
        ```json
        {{
          "rating": <你的评分>,
          "reasoning": "<你的评分理由>"
        }}
        ```
        """
        return self._get_llm_as_judge_response(prompt)

    def evaluate_answer_relevance(self, question: str, answer: str) -> dict:
        """评估答案本身与问题的相关性。"""
        prompt = f"""你是一个问答质量评估员。你的任务是评估一个答案是否直接、完整地回答了用户的问题。

        请基于以下问题和答案，对答案与问题的相关性进行评分，分数为1到5分。
        - 5分: 答案非常相关，精准且完整地解决了用户的问题。
        - 3分: 答案相关，但可能不够直接或遗漏了一些方面。
        - 1分: 答案完全答非所问。

        原始问题:
        "{question}"

        生成的答案:
        "{answer}"

        请以JSON格式返回你的评分和理由：
        ```json
        {{
          "rating": <你的评分>,
          "reasoning": "<你的评分理由>"
        }}
        ```
        """
        return self._get_llm_as_judge_response(prompt) 