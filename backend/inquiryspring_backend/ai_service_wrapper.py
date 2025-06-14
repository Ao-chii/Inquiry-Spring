"""
AI服务包装器 - 为Django后端提供统一的AI服务接口
"""
import logging
import os
from typing import Dict, Any, List

# 加载环境变量
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv不是必需的

logger = logging.getLogger(__name__)

# 检查是否可以导入Google Generative AI
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("Google Generative AI not available. Install with: pip install google-generativeai")


class AIService:
    """AI服务统一接口"""
    
    def __init__(self):
        self.api_key = os.getenv('GOOGLE_API_KEY')
        self.client = None
        self.model_name = "gemini-2.0-flash-exp"

        # 设置代理（如果需要）
        self._setup_proxy()

        if GEMINI_AVAILABLE and self.api_key:
            try:
                # 配置Gemini API
                genai.configure(api_key=self.api_key)
                self.client = genai.GenerativeModel(self.model_name)
                logger.info("Gemini AI client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}")
                self.client = None
        else:
            logger.warning("AI service running in offline mode")

    def _setup_proxy(self):
        """设置代理配置"""
        # 检查是否需要使用代理
        proxy_url = os.getenv('PROXY_URL', 'http://127.0.0.1:7890')
        use_proxy = os.getenv('USE_PROXY', 'true').lower() == 'true'

        if use_proxy:
            # 强制设置所有可能的代理环境变量
            proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']
            for var in proxy_vars:
                os.environ[var] = proxy_url

            # 配置urllib的代理（这对Google API很重要）
            try:
                import urllib.request
                proxy_handler = urllib.request.ProxyHandler({
                    'http': proxy_url,
                    'https': proxy_url
                })
                opener = urllib.request.build_opener(proxy_handler)
                urllib.request.install_opener(opener)
                logger.info(f"urllib proxy handler installed: {proxy_url}")
            except Exception as e:
                logger.warning(f"Failed to setup urllib proxy: {e}")

            logger.info(f"Proxy configured: {proxy_url}")
        else:
            # 清除代理设置
            proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']
            for var in proxy_vars:
                os.environ.pop(var, None)
            logger.info("Proxy disabled")
    
    def get_status(self) -> Dict[str, Any]:
        """获取AI服务状态"""
        return {
            'status': 'online' if self.client else 'offline',
            'api_key_configured': bool(self.api_key),
            'offline_mode': not bool(self.client),
            'model': self.model_name,
            'provider': 'gemini' if self.client else 'mock',
            'gemini_available': GEMINI_AVAILABLE
        }
    
    def chat(self, query: str, context: str = None) -> Dict[str, Any]:
        """聊天对话"""
        try:
            if self.client:
                # 构建提示词
                prompt = query
                if context:
                    prompt = f"基于以下上下文回答问题：\n\n{context}\n\n问题：{query}"

                # 调用Gemini API
                response = self.client.generate_content(prompt)

                return {
                    'text': response.text,
                    'model': self.model_name,
                    'provider': 'gemini',
                    'processing_time': 0.0,
                    'tokens_used': 0
                }
            else:
                # 离线模式返回模拟响应
                return {
                    'text': f"[模拟AI回复] 关于您的问题：{query}，这是一个模拟的AI回复。请配置GOOGLE_API_KEY环境变量以启用真实的AI功能。",
                    'model': 'mock',
                    'provider': 'mock',
                    'processing_time': 0.1,
                    'tokens_used': 50
                }

        except Exception as e:
            logger.error(f"Chat generation failed: {e}")
            return {
                'text': f"抱歉，AI服务暂时不可用。错误：{str(e)}",
                'model': self.model_name,
                'provider': 'error',
                'processing_time': 0.0,
                'tokens_used': 0,
                'error': str(e)
            }
    
    def summarize(self, content: str) -> Dict[str, Any]:
        """文档总结"""
        try:
            if self.client:
                prompt = f"""请对以下内容进行总结，要求：
1. 提取主要观点和关键信息
2. 保持逻辑清晰，结构合理
3. 控制在200-300字以内

内容：
{content}"""

                response = self.client.generate_content(prompt)

                return {
                    'text': response.text,
                    'model': self.model_name,
                    'provider': 'gemini'
                }
            else:
                return {
                    'text': f"[模拟总结] 这是对文档的模拟总结。文档长度：{len(content)}字符。请配置API密钥以获得真实的AI总结。",
                    'model': 'mock',
                    'provider': 'mock'
                }

        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            return {
                'text': f"总结生成失败：{str(e)}",
                'model': self.model_name,
                'provider': 'error',
                'error': str(e)
            }
    
    def generate_quiz(self, content: str = None, topic: str = None, 
                     question_count: int = 5, question_types: List[str] = None,
                     difficulty: str = 'medium') -> Dict[str, Any]:
        """生成测验"""
        try:
            if question_types is None:
                question_types = ['MC', 'TF']  # 单选题和判断题
            
            if self.client:
                if content:
                    prompt = f"""基于以下内容生成{question_count}道测验题目：

内容：
{content}

要求：
1. 题目类型：{', '.join(question_types)}
2. 难度：{difficulty}
3. 每道题包含：题目、选项（如适用）、正确答案、解释
4. 以JSON格式返回

格式示例：
{{
  "questions": [
    {{
      "type": "MC",
      "question": "题目内容",
      "options": ["A. 选项1", "B. 选项2", "C. 选项3", "D. 选项4"],
      "correct_answer": "A",
      "explanation": "解释内容"
    }}
  ]
}}"""
                else:
                    prompt = f"""生成关于"{topic or '通用知识'}"的{question_count}道测验题目：

要求：
1. 题目类型：{', '.join(question_types)}
2. 难度：{difficulty}
3. 每道题包含：题目、选项（如适用）、正确答案、解释
4. 以JSON格式返回"""
                
                response = self.client.generate_content(prompt)
                
                # 尝试解析JSON响应
                import json
                try:
                    result = json.loads(response.text)
                    return result
                except json.JSONDecodeError:
                    # 如果无法解析JSON，返回文本格式
                    return {
                        'text': response.text,
                        'questions': [],
                        'model': self.model_name,
                        'provider': 'gemini'
                    }
            else:
                # 生成模拟题目
                mock_questions = []
                for i in range(question_count):
                    if 'MC' in question_types:
                        mock_questions.append({
                            'type': 'MC',
                            'question': f'模拟单选题 {i+1}：这是一道关于{topic or "通用知识"}的测试题目？',
                            'options': ['A. 选项1', 'B. 选项2', 'C. 选项3', 'D. 选项4'],
                            'correct_answer': 'A',
                            'explanation': '这是模拟的解释内容。'
                        })
                    elif 'TF' in question_types:
                        mock_questions.append({
                            'type': 'TF',
                            'question': f'模拟判断题 {i+1}：关于{topic or "通用知识"}的陈述是正确的。',
                            'options': ['正确', '错误'],
                            'correct_answer': '正确',
                            'explanation': '这是模拟的解释内容。'
                        })
                
                return {
                    'questions': mock_questions,
                    'model': 'mock',
                    'provider': 'mock'
                }
                
        except Exception as e:
            logger.error(f"Quiz generation failed: {e}")
            return {
                'error': f"测验生成失败：{str(e)}",
                'questions': [],
                'model': self.model_name,
                'provider': 'error'
            }


# 全局AI服务实例
ai_service = AIService()
