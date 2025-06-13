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
        self.max_tokens = model_config.max_tokens if model_config else 1000
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
                try:
                    response_text = response.text
                except Exception as text_error:
                    # 尝试从候选项中获取文本
                    if hasattr(response, 'candidates') and response.candidates:
                        candidate = response.candidates[0]
                        if hasattr(candidate, 'content') and candidate.content:
                            response_text = str(candidate.content)
                        else:
                            error_msg = f"无法从候选项中获取文本: {str(text_error)}"
                            logger.exception(error_msg)
                            # 更新任务日志
                            processing_time = time.time() - start_time
                            self._update_task_log(
                                task_log,
                                {},
                                "failed",
                                0,
                                processing_time,
                                error_msg
                            )
                            return {
                                "error": error_msg,
                                "text": "很抱歉，无法获取Gemini响应内容，请稍后再试。",
                                "model": self.model_id
                            }
                    else:
                        error_msg = f"响应中缺少文本内容: {str(text_error)}"
                        logger.exception(error_msg)
                        # 更新任务日志
                        processing_time = time.time() - start_time
                        self._update_task_log(
                            task_log,
                            {},
                            "failed",
                            0,
                            processing_time,
                            error_msg
                        )
                        return {
                            "error": error_msg,
                            "text": "很抱歉，无法获取Gemini响应内容，请稍后再试。",
                            "model": self.model_id
                        }
                
                # 使用 countTokens API 准确计算 token 使用量
                input_tokens = self.count_tokens(full_prompt)
                output_tokens = self.count_tokens(response_text)
                tokens_used = input_tokens + output_tokens
                
                # 记录详细的token使用情况
                logger.debug(f"Token使用情况 - 输入: {input_tokens}, 输出: {output_tokens}, 总计: {tokens_used}")
            
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