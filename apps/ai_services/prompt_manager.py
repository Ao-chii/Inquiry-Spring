"""
提示词管理模块 - 负责加载、管理和渲染提示词模板
"""
import re
import json
import logging
from typing import Dict, List, Any, Optional, Union
from string import Template

from .models import PromptTemplate

logger = logging.getLogger(__name__)

class PromptManager:
    @staticmethod
    def get_template(template_type: str, name: str = None) -> Optional[PromptTemplate]:
        """
        获取提示词模板
        
        Args:
            template_type: 模板类型
            name: 模板名称，如果不提供则获取该类型的默认模板
            
        Returns:
            PromptTemplate对象，如果未找到则返回None
        """
        try:
            if name:
                template = PromptTemplate.objects.get(
                    template_type=template_type, 
                    name=name, 
                    is_active=True
                )
            else:
                # 获取该类型的第一个活跃模板
                template = PromptTemplate.objects.filter(
                    template_type=template_type, 
                    is_active=True
                ).first()
                
            return template
        except PromptTemplate.DoesNotExist:
            logger.warning(f"找不到提示词模板: type={template_type}, name={name}")
            return None
        except Exception as e:
            logger.exception(f"获取提示词模板失败: {str(e)}")
            return None
    
    @staticmethod
    def render_template(template: Union[str, PromptTemplate], variables: Dict[str, Any]) -> str:
        """
        渲染提示词模板
        
        Args:
            template: 提示词模板对象或模板字符串
            variables: 变量字典
            
        Returns:
            渲染后的提示词
        """
        try:
            if isinstance(template, PromptTemplate):
                template_content = template.content
            else:
                template_content = template
            
            # 处理参考资料部分
            if '$reference_text_section' in template_content:
                if variables.get('reference_text'):
                    variables['reference_text_section'] = f"""参考资料:
{variables.get('reference_text')}"""
                    variables['reference_instruction'] = "如果参考资料中没有足够的信息来回答，请坦诚告知你无法基于给定资料回答，但可以提供一般性的建议。"
                    variables['citation_instruction'] = "引用参考资料中的相关内容来支持你的回答"
                else:
                    variables['reference_text_section'] = ""
                    variables['reference_instruction'] = "基于你的知识提供最准确的回答。"
                    variables['citation_instruction'] = "确保回答准确且有帮助"
                
            # 使用string.Template进行渲染
            template_obj = Template(template_content)
            rendered = template_obj.safe_substitute(variables)
            
            return rendered
        except Exception as e:
            logger.exception(f"渲染提示词模板失败: {str(e)}")
            # 返回原始模板或错误信息
            return f"模板渲染错误: {str(e)}" if isinstance(template, str) else f"模板渲染错误: {str(e)}"
    
    @staticmethod
    def render_by_type(template_type: str, variables: Dict[str, Any], name: str = None) -> str:
        """
        根据类型获取并渲染提示词
        
        Args:
            template_type: 模板类型
            variables: 变量字典
            name: 模板名称，如果不提供则使用该类型的默认模板
            
        Returns:
            渲染后的提示词，如果模板不存在则返回默认提示词
        """
        template = PromptManager.get_template(template_type, name)
        
        if not template:
            # 返回默认提示词
            default_templates = {
                'quiz_generation': PromptManager.get_default_quiz_template(),
                'quiz_without_doc': PromptManager.get_default_quiz_without_doc_template(),
                'chat_response': PromptManager.get_default_chat_template(),
                'chat_with_history_response': PromptManager.get_default_chat_with_history_template(),
                'explanation': PromptManager.get_default_explanation_template(),
                'summary': PromptManager.get_default_summary_template(),
            }
            
            default_template = default_templates.get(
                template_type, 
                "无效的模板类型: " + template_type
            )
            
            return PromptManager.render_template(default_template, variables)
        
        return PromptManager.render_template(template, variables)
    
    @staticmethod
    def get_default_quiz_template() -> str:
        # 获取默认的测验生成模板
        return """
        你是一个专业的教育测验出题专家。请根据以下学习材料，生成高质量的测验题目。

        学习材料:
        $content

        请生成 $question_count 道测验题，题型包括: $question_types。
        难度级别: $difficulty（easy, medium, hard, master）

        支持的题型说明:
        - MC: 单选题 - 提供4个选项(A,B,C,D)，只有1个正确答案
        - MCM: 多选题 - 提供4-6个选项，有2个或更多正确答案
        - TF: 判断题 - 判断陈述是"正确"还是"错误"
        - FB: 填空题 - 需要填写单词、短语或句子
        - SA: 简答题 - 需要学生用自己的话回答，提供关键点列表作为参考答案

        要求:
        1. 每个问题都必须直接基于提供的学习材料
        2. 问题必须明确且答案准确
        3. 为每个问题提供详细的解析，解释为何正确答案是正确的
        4. 答案解析应直接引用原文相关内容
        5. 按以下JSON格式返回:

        ```json
        [
        {
            "content": "问题内容",
            "type": "MC", // MC=单选题，MCM=多选题，TF=判断题，FB=填空题，SA=简答题
            "options": ["选项A", "选项B", "选项C", "选项D"], // 选择题需要
            "correct_answer": "正确答案", // 根据题型不同有不同格式：
                                        // 单选题: "A"、"B"等字母
                                        // 多选题: ["A", "C"]等字母数组
                                        // 判断题: "正确"或"错误"
                                        // 填空题: "具体答案文本"
                                        // 简答题: ["关键点1", "关键点2", ...]
            "explanation": "详细解析",
            "source_passage": "原文相关段落",
            "difficulty": "medium" // 难度：easy, medium, hard, master
        },
        // 更多题目...
        ]
        ```

        对于简答题，正确答案应包含评分要点（关键词或关键概念的列表）。

        仅返回JSON格式的答案，不要有其他文字。
        """
    
    @staticmethod
    def get_default_chat_template() -> str:
        # 获取默认的聊天回复模板
        return """
        你是一个专业的学习助手。请回答用户的问题。

        $reference_text_section

        用户问题: $query

        请提供一个清晰、准确的回答，直接回应用户的问题。$reference_instruction

        回答时:
        1. 使用简洁易懂的语言
        2. 如有必要，可以分点列出信息
        3. $citation_instruction
        4. 不要编造不确定的信息

        回答:
        """
    
    @staticmethod
    def get_default_chat_with_history_template() -> str:
        # 获取默认的带对话历史的聊天回复模板
        return """
        你是一个专业的学习助手。请根据对话历史回答用户的问题。

        $reference_text_section

        对话历史:
        $conversation_history

        用户当前问题: $query

        请提供一个清晰、准确的回答，直接回应用户的问题。回答时考虑之前的对话历史，保持上下文连贯性。
        如果需要引用之前对话中提到的信息，请明确指出。
        $reference_instruction

        回答要求:
        1. 使用简洁易懂的语言
        2. 如有必要，分点列出信息
        3. $citation_instruction
        4. 不要编造不确定的信息
        5. 保持与之前对话的连贯性

        回答:
        """
    
    @staticmethod
    def get_default_explanation_template() -> str:
        # 获取默认的解释生成模板
        return """
        你是一个专业的教育解释专家。学生在回答以下问题时做出了错误的选择。请提供详细的解释，帮助学生理解为什么他们的答案是错误的，以及为什么正确答案是对的。

        学习材料:
        $content

        问题: $question

        学生的错误答案: $wrong_answer
        正确答案: $correct_answer

        请提供详细解释，包括:
        1. 为什么学生的答案是错误的
        2. 为什么正确答案是对的
        3. 相关概念的解释
        4. 直接引用学习材料中的相关段落
        5. 如果可能，提供易于理解的类比或例子

        你的解释应该有教育意义，不仅仅指出错误，而是帮助学生真正理解概念。语气应该鼓励而非批判。
        """
    
    @staticmethod
    def get_default_summary_template() -> str:
        # 获取默认的总结生成模板
        return """
        请为以下内容生成一个全面、准确的摘要。摘要应该捕捉文档的主要论点、关键概念和重要结论。

        文档内容:
        $content

        长度要求:
        $length_requirement

        格式要求:
        $outline_requirement

        要求:
        1. 保留文档的核心信息和关键点
        2. 使用清晰、专业的语言
        3. 保持客观，不添加原文中没有的信息
        4. 结构化呈现，可以使用小标题或编号列表
        5. 如果文档包含技术术语，请保留并简要解释
        6. 突出文档中的重要数据或发现
        7. 标记特别重要的内容以便阅读者关注

        摘要:
        """
    
    @staticmethod
    def get_default_quiz_without_doc_template() -> str:
        # 获取默认的无文档测验生成模板
        return """
        你是一个专业的教育测验出题专家。请根据以下主题和要求，生成高质量的测验题目。

        主题: $topic
        
        请生成 $question_count 道测验题，题型包括: $question_types。
        难度级别: $difficulty（easy, medium, hard, master）

        支持的题型说明:
        - MC: 单选题 - 提供4个选项(A,B,C,D)，只有1个正确答案
        - MCM: 多选题 - 提供4-6个选项，有2个或更多正确答案
        - TF: 判断题 - 判断陈述是"正确"还是"错误"
        - FB: 填空题 - 需要填写单词、短语或句子
        - SA: 简答题 - 需要学生用自己的话回答，提供关键点列表作为参考答案

        额外约束和要求:
        $constraints

        要求:
        1. 问题必须与主题相关，且符合额外约束要求
        2. 问题必须明确且答案准确
        3. 为每个问题提供详细的解析，解释为何正确答案是正确的
        4. 答案解析应引用相关知识点
        5. 按以下JSON格式返回:

        ```json
        [
        {
            "content": "问题内容",
            "type": "MC", // MC=单选题，MCM=多选题，TF=判断题，FB=填空题，SA=简答题
            "options": ["选项A", "选项B", "选项C", "选项D"], // 选择题需要
            "correct_answer": "正确答案", // 根据题型不同有不同格式：
                                        // 单选题: "A"、"B"等字母
                                        // 多选题: ["A", "C"]等字母数组
                                        // 判断题: "正确"或"错误"
                                        // 填空题: "具体答案文本"
                                        // 简答题: ["关键点1", "关键点2", ...]
            "explanation": "详细解析",
            "difficulty": "medium" // 难度：easy, medium, hard, master
        },
        // 更多题目...
        ]
        ```

        对于简答题，正确答案应包含评分要点（关键词或关键概念的列表）。

        仅返回JSON格式的答案，不要有其他文字。
        """
    
    @staticmethod
    def create_default_templates():
        # 创建默认提示词模板
        try:
            from django.db import connection
            # 检查表是否存在
            table_names = connection.introspection.table_names()
            if 'ai_services_prompttemplate' not in table_names:
                logger.warning("提示词模板表不存在，跳过创建默认模板")
                return
                
            default_templates = [
                {
                    'name': '标准测验生成',
                    'template_type': 'quiz_generation',
                    'content': PromptManager.get_default_quiz_template(),
                    'variables': ['content', 'question_count', 'question_types', 'difficulty'],
                    'version': '1.0',
                    'is_active': True
                },
                {
                    'name': '无文档测验生成',
                    'template_type': 'quiz_without_doc',
                    'content': PromptManager.get_default_quiz_without_doc_template(),
                    'variables': ['topic', 'constraints', 'question_count', 'question_types', 'difficulty'],
                    'version': '1.0',
                    'is_active': True
                },
                {
                    'name': '标准聊天回复',
                    'template_type': 'chat_response',
                    'content': PromptManager.get_default_chat_template(),
                    'variables': ['reference_text', 'query'],
                    'version': '1.0',
                    'is_active': True
                },
                {
                    'name': '带历史聊天回复',
                    'template_type': 'chat_with_history_response',
                    'content': PromptManager.get_default_chat_with_history_template(),
                    'variables': ['reference_text', 'conversation_history', 'query'],
                    'version': '1.0',
                    'is_active': True
                },
                {
                    'name': '标准解释生成',
                    'template_type': 'explanation',
                    'content': PromptManager.get_default_explanation_template(),
                    'variables': ['content', 'question', 'wrong_answer', 'correct_answer'],
                    'version': '1.0',
                    'is_active': True
                },
                {
                    'name': '标准总结生成',
                    'template_type': 'summary',
                    'content': PromptManager.get_default_summary_template(),
                    'variables': ['content'],
                    'version': '1.0',
                    'is_active': True
                }
            ]
            
            for template_data in default_templates:
                try:
                    # 检查是否已存在
                    existing = PromptTemplate.objects.filter(
                        template_type=template_data['template_type'],
                        name=template_data['name']
                    ).first()
                    
                    if not existing:
                        PromptTemplate.objects.create(
                            name=template_data['name'],
                            template_type=template_data['template_type'],
                            content=template_data['content'],
                            variables=template_data['variables'],
                            version=template_data['version'],
                            is_active=template_data['is_active']
                        )
                        logger.info(f"创建默认提示词模板: {template_data['name']}")
                except Exception as e:
                    logger.warning(f"创建默认提示词模板失败: {str(e)}")
        except Exception as e:
            if 'no such table' in str(e).lower():
                logger.warning("提示词模板表不存在，跳过创建默认模板")
            else:
                logger.exception(f"创建默认提示词模板过程中出错: {str(e)}") 