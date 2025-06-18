"""
LLM客户端模块 - 用于与不同的LLM服务提供商进行通信
"""
import os
import json
import time
import logging
from typing import Dict, Any, Optional, List
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from .models import AIModel, AITaskLog
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from django.utils import timezone

logger = logging.getLogger(__name__)

class LLMClientFactory:
    
    @staticmethod
    def create_client(model_id=None, provider=None):
        """
        创建LLM客户端
        
        
        Args:
            model_id: 模型ID，如果提供则直接使用该ID查找模型
            provider: 提供商名称，如果model_id未提供，则使用provider查找默认模型
            
        Returns:
            LLMClient子类的实例
        """
        try:
            # 获取模型配置
            if model_id:
                model_config = AIModel.objects.get(id=model_id, is_active=True)
            elif provider:
                model_config = AIModel.objects.get(provider=provider, is_active=True, is_default=True)
            else:
                # 获取默认模型
                try:
                    model_config = AIModel.objects.get(is_active=True, is_default=True)
                except AIModel.DoesNotExist:
                    logger.warning("找不到默认AI模型配置，使用内置Gemini客户端")
                    return GeminiClient(None)
                except Exception as e:
                    if 'no such table' in str(e).lower():
                        logger.warning("AI模型表不存在，使用内置Gemini客户端")
                        return GeminiClient(None)
                    raise
                
            # 根据提供商创建对应的客户端
            if model_config.provider == 'gemini':
                return GeminiClient(model_config)
            elif model_config.provider == 'local':
                return LocalModelClient(model_config)
            else:
                logger.warning(f"不支持的LLM提供商: {model_config.provider}，使用内置Gemini客户端")
                return GeminiClient(None)
                
        except AIModel.DoesNotExist:
            logger.warning(f"找不到可用的模型配置. model_id={model_id}, provider={provider}，使用内置Gemini客户端")
            # 创建一个默认的Gemini客户端作为后备方案
            return GeminiClient(None)
        except Exception as e:
            if 'no such table' in str(e).lower():
                logger.warning("AI模型表不存在，使用内置Gemini客户端")
                return GeminiClient(None)
            logger.exception(f"创建LLM客户端失败: {str(e)}")
            # 出错时也返回默认客户端，而不是抛出异常
            return GeminiClient(None)


class BaseLLMClient:
    """LLM客户端基类"""
    
    def __init__(self, model_config: Optional[AIModel]):
        self.model_config = model_config
        self.model_id = model_config.model_id if model_config else "gemini-2.5-flash-preview-05-20"
        self.max_tokens = model_config.max_tokens if model_config else 10000  # 增加默认token限制用于文档总结
        self.temperature = model_config.temperature if model_config else 0.7
        
        # 设置API密钥和基础URL
        if model_config and model_config.api_key:
            self.api_key = model_config.api_key
        else:
            # 从环境变量获取
            self.api_key = os.environ.get("OPENAI_API_KEY", "")
            
        if model_config and model_config.api_base:
            self.api_base = model_config.api_base
        else:
            self.api_base = None
    
    def _create_task_log(self, task_type: str, input_data: Dict, **kwargs) -> AITaskLog:
        """创建任务日志"""
        log_data = {
            'task_type': task_type,
            'model': self.model_config,
            'input_data': input_data,
            'status': 'processing',
            'user': kwargs.get('user'),
            'session_id': kwargs.get('session_id'),
            'document': kwargs.get('document')
        }
        # 过滤掉None的值，避免向create方法传递空参数
        log_data = {k: v for k, v in log_data.items() if v is not None}
        return AITaskLog.objects.create(**log_data)
    
    def _update_task_log(self, task_log: AITaskLog, output_data: Dict, 
                        status: str, tokens_used: int, 
                        processing_time: float, error_msg: str = "") -> None:
        """更新任务日志"""
        task_log.output_data = output_data
        task_log.status = status
        task_log.tokens_used = tokens_used
        task_log.processing_time = processing_time
        task_log.error_message = error_msg
        task_log.completed_at = timezone.now()
        task_log.save()
    
    def generate_text(self, prompt: str, system_prompt: str = None, 
                    max_tokens: int = None, temperature: float = None,
                    task_type: str = "chat", **kwargs) -> Dict[str, Any]:
        """
        生成文本（由子类实现）
        
        Args:
            prompt: 主提示词
            system_prompt: 系统提示词
            max_tokens: 最大生成令牌数
            temperature: 温度参数
            task_type: 任务类型
            **kwargs: 用于日志记录的额外上下文 (user, session_id, document)
            
        Returns:
            包含生成结果的字典
        """
        raise NotImplementedError("子类必须实现此方法")


class GeminiClient(BaseLLMClient):
    """Google Gemini API客户端"""
    
    def __init__(self, model_config: Optional[AIModel]):
        super().__init__(model_config)
        
        api_key = self.api_key
        if model_config and model_config.api_key:
            api_key = model_config.api_key
        elif os.environ.get("GOOGLE_API_KEY"):
            api_key = os.environ.get("GOOGLE_API_KEY")
        else:
            api_key = None
            
        if not api_key:
            logger.warning("未提供有效的Gemini API密钥 (既不在模型配置中，也不在GOOGLE_API_KEY环境变量中)，将使用模拟响应")
            self.genai = None
            self.offline_mode = True
            return
            
        self.offline_mode = os.environ.get("GEMINI_OFFLINE_MODE", "").lower() in ("true", "1", "yes")
        if self.offline_mode:
            logger.warning("Gemini客户端运行在离线模式，将返回模拟响应")
            self.genai = None
            return
            
        try:
            genai.configure(api_key=api_key)
            self.genai = genai
        except Exception as e:
            logger.error(f"配置Gemini API失败: {str(e)}，将使用模拟响应")
            self.genai = None
            self.offline_mode = True
        
        if self.model_config and self.model_config.model_id:
            self.model_id = self.model_config.model_id
        elif not hasattr(self, 'model_id') or not self.model_id or self.model_id == "gpt-3.5-turbo":
            self.model_id = "gemini-2.5-flash-preview-05-20"
            logger.info(f"GeminiClient: No specific model_id provided, defaulting to {self.model_id}")
        else:
            logger.info(f"GeminiClient: Using pre-existing model_id: {self.model_id}")
    
    def _estimate_tokens(self, text: str) -> int:
        """估算文本包含的token数量 (简单估算)
        
        Args:
            text: 要估算的文本
            
        Returns:
            估计的token数量
        """
        # 简单估算：每个汉字约等于1个token，每4个英文字符约等于1个token
        # 这是一个简化估算，实际token数会根据模型分词器的具体实现有所不同
        chinese_count = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        english_chars = sum(1 for c in text if c.isascii() and (c.isalnum() or c.isspace()))
        english_tokens = english_chars / 4
        
        return int(chinese_count + english_tokens)
    
    def count_tokens(self, text: str) -> int:
        """使用 Gemini API 准确计算文本的 token 数量
        
        Args:
            text: 要计算的文本
            
        Returns:
            token 数量
        """
        if not self.genai:
            # 如果没有API访问，回退到估算方法
            return self._estimate_tokens(text)
            
        try:
            # 使用模型的 countTokens 方法准确计算
            model = self.genai.GenerativeModel(self.model_id)
            result = model.count_tokens(text)
            return result.total_tokens
        except Exception as e:
            logger.warning(f"使用 countTokens API 计算 token 失败: {e}，回退到估算方法")
            # 出错时回退到估算方法
            return self._estimate_tokens(text)
    
    def generate_text(self, prompt: str, system_prompt: str = None, 
                    max_tokens: int = None, temperature: float = None,
                    task_type: str = "chat", **kwargs) -> Dict[str, Any]:
        """使用Gemini API生成文本"""
        if not max_tokens:
            max_tokens = self.max_tokens
            
        if not temperature:
            temperature = self.temperature
            
        if not system_prompt:
            system_prompt = "你是一名资深教学问答专家。请根据用户的问题提供准确、有用的回答。"
            
        # 创建任务日志
        input_data = {
            "prompt": prompt,
            "system_prompt": system_prompt,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        task_log = self._create_task_log(task_type, input_data, **kwargs)
        
        start_time = time.time()
        
        try:
            if not self.genai:
                # 模拟响应，用于无API密钥的情况
                response_text = f"[Gemini模拟响应] 对于问题: {prompt}"
                tokens_used = 50
            else:
                # 配置生成参数
                generation_config = {
                    "temperature": temperature,
                    "max_output_tokens": max_tokens,
                    "top_p": 0.95,
                    "top_k": 40,
                }
                
                # 安全设置配置
                safety_settings = {
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                }
                
                # 合并system_prompt和prompt
                full_prompt = prompt
                if system_prompt:
                    full_prompt = f"{system_prompt}\n\n{prompt}"
                
                # 调用Gemini API
                model = self.genai.GenerativeModel(self.model_id)
                response = model.generate_content(
                    full_prompt,
                    generation_config=generation_config,
                    safety_settings=safety_settings
                )
                
                # 处理响应，确保text属性存在
                response_text = ""
                try:
                    # 首先检查response candidates中是否有finish_reason为MAX_TOKENS的情况
                    if response.candidates and hasattr(response.candidates[0], 'finish_reason'):
                        candidate = response.candidates[0]
                        finish_reason = candidate.finish_reason.name if hasattr(candidate.finish_reason, 'name') else str(candidate.finish_reason)
                        
                        if finish_reason == "MAX_TOKENS":
                            logger.warning("检测到Gemini响应因达到最大tokens限制而被截断")
                            # 即使在MAX_TOKENS的情况下，也尝试提取已经生成的内容
                            if candidate.content and candidate.content.parts:
                                extracted_text = "".join(str(part.text) for part in candidate.content.parts 
                                                       if hasattr(part, 'text') and part.text is not None)
                                if extracted_text:
                                    logger.info("成功提取被截断的内容")
                                    response_text = extracted_text
                                    # 直接继续处理，不抛出异常
                            else:
                                # 对于MAX_TOKENS但没有内容的特殊情况
                                logger.warning("检测到MAX_TOKENS但无法提取内容，返回默认消息")
                                # 设置一个默认消息，而不是错误
                                response_text = "内容因超出长度限制而被截断。"
                                # 全局定义extracted_text变量，以便后续设置正确的finish_reason
                                extracted_text = response_text
                    
                    # 如果没有被MAX_TOKENS截断，或者没能从MAX_TOKENS中提取内容，则尝试正常方式获取text
                    if not response_text:
                        response_text = response.text
                except Exception as text_error:
                    logger.warning(f"直接访问 response.text 失败: {text_error}。尝试手动解析候选项。")
                    if response.candidates:
                        # 从第一个候选项连接所有文本部分
                        candidate = response.candidates[0]
                        if candidate.content and candidate.content.parts:
                            response_text = "".join(str(part.text) for part in candidate.content.parts 
                                                 if hasattr(part, 'text') and part.text is not None)
                        
                if not response_text:
                    # 如果 response_text 仍然为空，说明响应可能被阻止了或者发生了其他问题
                    finish_reason = "Unknown"
                    safety_ratings_str = "N/A"
                    
                    if response.candidates:
                        candidate = response.candidates[0]
                        finish_reason = candidate.finish_reason.name if hasattr(candidate.finish_reason, 'name') else str(candidate.finish_reason)
                        safety_ratings_str = str(candidate.safety_ratings)
                        
                        # 特殊处理MAX_TOKENS情况，如果之前未处理
                        if finish_reason == "MAX_TOKENS":
                            # 即使没有内容，也返回一个优雅的消息而不是错误
                            logger.warning(f"在第二次尝试中检测到MAX_TOKENS但无法提取内容，返回默认消息")
                            response_text = "内容因超出长度限制而被截断。"
                            extracted_text = response_text  # 设置extracted_text以标记这是MAX_TOKENS情况
                            
                    # 如果有一个有效的响应文本，无论是从哪里获得的，就使用它
                    if response_text:
                        logger.info(f"成功获取响应内容，长度: {len(response_text)}")
                    else:
                        # 其他情况，真正无法提取内容
                        error_msg = f"未能从Gemini响应中提取有效文本。完成原因: {finish_reason}. 安全评级: {safety_ratings_str}"
                        logger.error(error_msg)
                        
                        processing_time = time.time() - start_time
                        self._update_task_log(
                            task_log,
                            output_data={"error": error_msg, "raw_response": str(response)},
                            status="failed",
                            tokens_used=0,
                            processing_time=processing_time,
                            error_msg=error_msg
                        )
                        return {
                            "error": error_msg,
                            "text": f"抱歉，无法获取Gemini响应内容。原因: {finish_reason}",
                            "model": self.model_id
                        }
                
                # 使用 countTokens API 准确计算 token 使用量
                input_tokens = self.count_tokens(full_prompt)
                output_tokens = self.count_tokens(response_text)
                tokens_used = input_tokens + output_tokens
                
                # 记录详细的token使用情况
                logger.debug(f"Token使用情况 - 输入: {input_tokens}, 输出: {output_tokens}, 总计: {tokens_used}")
            
            # 构建结果
            # 确定正确的finish_reason
            finish_reason = "stop"
            # 如果之前检测到了MAX_TOKENS情况，更新finish_reason
            if "extracted_text" in locals() and extracted_text:
                finish_reason = "MAX_TOKENS"
                logger.info(f"返回已截断的响应，finish_reason设置为: {finish_reason}")
            
            result = {
                "text": response_text,
                "tokens_used": tokens_used,
                "model": self.model_id,
                "finish_reason": finish_reason
            }
            
            # 更新任务日志
            processing_time = time.time() - start_time
            self._update_task_log(
                task_log, 
                {"result": result}, 
                "completed", 
                tokens_used, 
                processing_time
            )
            
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = str(e)
            logger.exception(f"Gemini API调用失败: {error_msg}")
            
            # 更新任务日志
            self._update_task_log(
                task_log,
                {},
                "failed",
                0,
                processing_time,
                error_msg
            )
            
            # 返回错误信息
            return {
                "error": error_msg,
                "text": "很抱歉，Gemini服务暂时不可用，请稍后再试。",
                "model": self.model_id
            }


class LocalModelClient(BaseLLMClient):
    """本地模型客户端"""
    
    def __init__(self, model_config: Optional[AIModel]):
        super().__init__(model_config)
        
        # 设置默认模型ID
        if not self.model_id:
            self.model_id = "local-model"
            
        # 初始化本地模型
        self.model = None
        self.tokenizer = None
        try:

            # 检查是否有CUDA
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"本地模型将使用设备: {self.device}")
            
            # 获取模型路径
            model_path = self.model_id
            if self.model_config and self.model_config.api_base:
                # 如果api_base字段包含了模型路径
                model_path = self.model_config.api_base
                
            # 初始化模型和分词器
            logger.info(f"正在从 {model_path} 加载本地模型...")
            
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
                self.model = AutoModelForCausalLM.from_pretrained(
                    model_path,
                    device_map=self.device,
                    torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                    trust_remote_code=True
                )
                logger.info(f"本地模型 {model_path} 加载成功")
            except Exception as load_error:
                logger.error(f"加载本地模型失败: {str(load_error)}")
                self.model = None
                self.tokenizer = None
        except ImportError as e:
            logger.warning(f"无法导入必要的库以支持本地模型: {str(e)}")
            logger.warning("请确保已安装 torch 和 transformers 库")
            self.model = None
            self.tokenizer = None
        except Exception as e:
            logger.exception(f"初始化本地模型失败: {str(e)}")
            self.model = None
            self.tokenizer = None
    
    def generate_text(self, prompt: str, system_prompt: str = None, 
                    max_tokens: int = None, temperature: float = None,
                    task_type: str = "chat", **kwargs) -> Dict[str, Any]:
        """使用本地模型生成文本"""
        if not max_tokens:
            max_tokens = self.max_tokens
            
        if not temperature:
            temperature = self.temperature
            
        # 创建任务日志
        input_data = {
            "prompt": prompt,
            "system_prompt": system_prompt,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        task_log = self._create_task_log(task_type, input_data, **kwargs)
        
        start_time = time.time()
        
        try:
            # 如果本地模型未初始化成功，返回模拟响应
            if not self.model or not self.tokenizer:
                response_text = f"[本地模型模拟响应] 对于问题: {prompt}"
                tokens_used = 50
            else:
                # 构建完整提示词
                full_prompt = prompt
                if system_prompt:
                    full_prompt = f"{system_prompt}\n\n{prompt}"
                
                # 设置生成参数
                gen_kwargs = {
                    "max_new_tokens": max_tokens,
                    "temperature": temperature,
                    "top_p": 0.95,
                    "top_k": 50,
                    "do_sample": temperature > 0.1  # 当温度大于0.1时使用采样
                }
                

                with torch.no_grad():
                    inputs = self.tokenizer(full_prompt, return_tensors="pt").to(self.device)
                    input_ids_length = inputs.input_ids.shape[1]
                    
                    # 生成文本
                    outputs = self.model.generate(
                        **inputs,
                        **gen_kwargs
                    )
                    
                    # 只保留新生成的部分
                    new_tokens = outputs[0][input_ids_length:]
                    response_text = self.tokenizer.decode(new_tokens, skip_special_tokens=True)
                    
                    # 计算token使用量
                    tokens_used = input_ids_length + len(new_tokens)
            
            # 构建结果
            result = {
                "text": response_text,
                "tokens_used": tokens_used,
                "model": self.model_id,
                "finish_reason": "stop"
            }
            
            # 更新任务日志
            processing_time = time.time() - start_time
            self._update_task_log(
                task_log, 
                {"result": result}, 
                "completed", 
                tokens_used, 
                processing_time
            )
            
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = str(e)
            logger.exception(f"本地模型调用失败: {error_msg}")
            
            # 更新任务日志
            self._update_task_log(
                task_log,
                {},
                "failed",
                0,
                processing_time,
                error_msg
            )
            
            # 返回错误信息
            return {
                "error": error_msg,
                "text": "很抱歉，本地模型服务暂时不可用，请稍后再试。",
                "model": self.model_id
            } 