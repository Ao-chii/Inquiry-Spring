"""
结构化输出处理模块 - 处理LLM输出的格式化、验证和自动修复
"""
import json
import logging
from typing import Any, Dict, List, Optional, Type, TypeVar, Union
from pydantic import BaseModel, ValidationError
import time

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)

# 预定义的Pydantic模型
class QuestionOption(BaseModel):
    text: str
    id: str

class Question(BaseModel):
    content: str
    question_type: str
    options: Optional[List[QuestionOption]] = None
    correct_answer: Union[str, List[str]]
    explanation: str
    difficulty: str
    knowledge_points: List[str]

class Quiz(BaseModel):
    questions: List[Question]

class ChatResponse(BaseModel):
    answer: str

class SummaryResponse(BaseModel):
    summary: str

# 主处理类
class StructuredOutputProcessor:
    """处理LLM结构化输出的验证与修复"""
    
    def __init__(self, max_retries=2, retry_delay=1):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
    
    def validate_and_fix(
        self, 
        text: str, 
        model_class: Type[T], 
        llm_client: Any, 
        task_type: str = "structured_output",
        **retry_kwargs
    ) -> T:
        """
        验证并修复LLM输出，确保符合指定的Pydantic模型结构
        
        Args:
            text: LLM生成的文本
            model_class: 用于验证的Pydantic模型类
            llm_client: LLM客户端，用于在验证失败时重新生成
            task_type: 任务类型，用于日志记录
            **retry_kwargs: 重新生成时传递给LLM客户端的参数
            
        Returns:
            符合模型的结构化数据
        """
        parsed_data = self._extract_and_parse_json(text)
        
        for attempt in range(self.max_retries + 1):
            try:
                # 尝试验证数据
                if isinstance(parsed_data, list) and not issubclass(model_class, list):
                    # 处理常见的错误：模型期望对象，但得到列表（如问题列表而非问题集合）
                    if issubclass(model_class, Quiz) and all(isinstance(item, dict) for item in parsed_data):
                        parsed_data = {"questions": parsed_data}
                
                # 验证数据
                validated_data = model_class.model_validate(parsed_data)
                return validated_data
                
            except ValidationError as e:
                logger.warning(f"验证失败 (尝试 {attempt+1}/{self.max_retries+1}): {str(e)}")
                
                if attempt < self.max_retries:
                    # 构建带有错误反馈的修复提示
                    correction_prompt = self._build_correction_prompt(text, parsed_data, model_class, e)
                    
                    # 添加延迟，避免模型API的速率限制
                    time.sleep(self.retry_delay)
                    
                    # 重新调用LLM获取修复后的输出
                    system_prompt = f"你需要修复之前的输出，使其符合以下JSON Schema: {self.get_json_schema(model_class)}"
                    response = llm_client.generate_text(
                        prompt=correction_prompt,
                        system_prompt=system_prompt,
                        task_type=task_type,
                        **retry_kwargs
                    )
                    
                    # 使用新的输出再次尝试解析
                    text = response.get("text", "")
                    parsed_data = self._extract_and_parse_json(text)
                else:
                    logger.error(f"达到最大重试次数，无法修复输出。最后一个错误: {str(e)}")
                    raise ValueError(f"无法将LLM输出转换为有效的结构化数据: {str(e)}")
    
    def _extract_and_parse_json(self, text: str) -> Any:
        """从LLM响应中提取和解析JSON"""
        import re
        
        # 尝试从Markdown代码块中提取JSON
        json_block_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
        match = re.search(json_block_pattern, text)
        json_str = match.group(1) if match else text
        
        # 清理可能导致JSON无效的内容
        json_str = self._clean_json_string(json_str)
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON解析失败: {e}，尝试更积极的清理")
            
            # 第二次尝试：更积极地移除干扰内容
            lines = [line for line in json_str.split('\n') 
                    if not line.strip().startswith('//') and '//' not in line]
            clean_json = '\n'.join(lines)
            
            try:
                return json.loads(clean_json)
            except json.JSONDecodeError:
                # 如果仍然失败，返回一个最小可行的对象
                logger.error("JSON解析彻底失败")
                return {} if not json_str.strip().startswith('[') else []
    
    def _clean_json_string(self, json_str: str) -> str:
        """清理JSON字符串，移除注释和尾随逗号"""
        import re
        
        # 移除单行注释
        json_str = re.sub(r'//.*?$', '', json_str, flags=re.MULTILINE)
        
        # 移除多行注释
        json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)
        
        # 修复尾随逗号
        json_str = re.sub(r',(\s*[\]}])', r'\1', json_str)
        
        return json_str
    
    def _build_correction_prompt(self, original_text: str, parsed_data: Any, 
                               model_class: Type[BaseModel], error: ValidationError) -> str:
        """构建用于修复输出的提示"""
        schema = self.get_json_schema(model_class)
        
        return f"""我需要你修复以下JSON输出，使其符合指定的模式。

原始输出:
```json
{json.dumps(parsed_data, ensure_ascii=False, indent=2)}
```

验证错误:
{str(error)}

请根据以下JSON Schema修复输出，确保格式正确:
```json
{schema}
```

请只返回符合schema的有效JSON，不要包含任何其他解释或评论。"""
    
    @staticmethod
    def get_json_schema(model_class: Type[BaseModel]) -> str:
        """获取模型的JSON Schema"""
        schema = model_class.model_json_schema()
        return json.dumps(schema, ensure_ascii=False, indent=2)
    
    @staticmethod
    def generate_prompt_with_schema(base_prompt: str, model_class: Type[BaseModel], examples: List[Dict] = None) -> str:
        """生成包含JSON Schema和示例的完整提示"""
        schema = StructuredOutputProcessor.get_json_schema(model_class)
        
        schema_prompt = f"{base_prompt}\n\n请严格按照以下JSON Schema格式返回结果:\n```json\n{schema}\n```"
        
        if examples and len(examples) > 0:
            examples_json = json.dumps(examples, ensure_ascii=False, indent=2)
            schema_prompt += f"\n\n以下是符合要求的示例输出:\n```json\n{examples_json}\n```"
            
        schema_prompt += "\n\n请确保你的输出是有效的JSON，可以被直接解析，不包含任何额外的文本或解释。输出应当使用```json和```包装。"
        
        return schema_prompt
        
# 使用示例:
"""
# 构建Quiz模式的提示
processor = StructuredOutputProcessor()
quiz_prompt = processor.generate_prompt_with_schema(
    "生成一个包含3道选择题的测验",
    Quiz,
    examples=[{
        "questions": [
            {
                "content": "地球是第几颗行星?",
                "question_type": "MC",
                "options": [
                    {"id": "A", "text": "第一颗"},
                    {"id": "B", "text": "第三颗"},
                    {"id": "C", "text": "第五颗"}
                ],
                "correct_answer": "B",
                "explanation": "地球是距离太阳第三近的行星",
                "difficulty": "easy",
                "knowledge_points": ["天文学", "太阳系"]
            }
        ]
    }]
)

# 在生成结果后验证和修复
response = llm_client.generate_text(quiz_prompt)
quiz = processor.validate_and_fix(response['text'], Quiz, llm_client)
""" 