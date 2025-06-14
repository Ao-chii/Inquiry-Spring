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
            query_params = {'template_type': template_type, 'is_active': True}
            if name:
                query_params['name'] = name
            
            # 优先获取指定名称的，否则获取该类型的第一个
            return PromptTemplate.objects.filter(**query_params).first()
        except PromptTemplate.DoesNotExist:
            logger.warning(f"找不到提示词模板: type={template_type}, name={name}")
            return None
        except Exception as e:
            logger.exception(f"获取提示词模板失败: {str(e)}")
            return None
    
    @staticmethod
    def render_template(template_content: str, variables: Dict[str, Any]) -> str:
        """
        渲染提示词模板
        
        Args:
            template: 提示词模板对象或模板字符串
            variables: 变量字典
            
        Returns:
            渲染后的提示词
        """
        try:
            # 动态处理 RAG 和对话历史的占位符
            if '$reference_text_section' in template_content:
                if variables.get('reference_text'):
                    variables['reference_text_section'] = f"参考资料:\n{variables['reference_text']}"
                    variables['reference_instruction'] = "请严格根据上面提供的参考资料来回答问题。"
                else:
                    variables['reference_text_section'] = ""
                    variables['reference_instruction'] = "基于你的知识提供最准确的回答。"
            
            if '$conversation_history_section' in template_content:
                if variables.get('conversation_history'):
                    variables['conversation_history_section'] = f"对话历史:\n{variables['conversation_history']}"
                else:
                    variables['conversation_history_section'] = ""
                
            template_obj = Template(template_content)
            return template_obj.safe_substitute(variables)
        except Exception as e:
            logger.exception(f"渲染提示词模板失败: {str(e)}")
            return f"模板渲染错误: {str(e)}"
    
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
            logger.error(f"无法找到类型为 '{template_type}' 的活跃模板，渲染失败。")
            # 在严格模式下，我们不应使用硬编码的后备模板
            return f"错误：找不到类型为 '{template_type}' 的模板。"
        
        return PromptManager.render_template(template.content, variables)
    
    @staticmethod
    def create_default_templates():
        """
        在数据库中创建或更新三种核心类型的默认提示词模板。
        这确保了系统有可靠的、版本化的基础提示词。
        """
        try:
            # 检查表是否存在，避免在迁移前执行
            from django.db import connection
            if 'ai_services_prompttemplate' not in connection.introspection.table_names():
                logger.warning("提示词模板表不存在，跳过创建默认模板。")
                return
        except Exception as e:
             logger.warning(f"检查提示词模板表时出错: {e}，跳过创建。")
             return

        templates_to_create = {
            'chat': {
                'name': '统一智能对话',
                'content': """你是一个专业的学习助手。
                            $reference_text_section

                            $conversation_history_section

                            用户问题: $query

                            回答要求:
                            1. $reference_instruction
                            2. 对于每个关键信息点，必须在句末通过方括号标注其来源编号，例如：[1]、[2]。
                            3. 如果一个句子综合了多个来源，请标注所有来源，例如：[1,2]。
                            4. 不要编造不在参考资料中的信息。如果参考资料不足以回答问题，请明确说明。

                            请开始你的回答:""",
                'variables': ['query', 'reference_text', 'conversation_history'],
                'version': '3.0'
            },
            'quiz': {
                'name': '统一测验生成',
                'content': """你是一个专业的教育测验出题专家。请根据以下要求，生成高质量的测验题目。
                            $reference_text_section

                            主题: $topic
                            用户需求: $user_requirements

                            请生成 $question_count 道关于"$topic"主题的测验题，题型包括: $question_types。
                            难度级别: $difficulty。
                            $reference_instruction

                            请严格按以下JSON格式返回，不要有其他文字:
                            ```json
                            [
                            {
                                "content": "问题内容",
                                "type": "MC/MCM/TF/FB/SA", // 使用上述题型代码
                                "options": ["选项A", "选项B", "选项C", "选项D"], // 选择题需要
                                "correct_answer": "正确答案", // 根据题型不同有不同格式：
                                                            // 单选题: "A"、"B"等字母
                                                            // 多选题: ["A", "C"]等字母数组
                                                            // 判断题: "正确"或"错误"
                                                            // 填空题: "具体答案文本"
                                                            // 简答题: ["关键点1", "关键点2", ...]
                                "explanation": "详细解析",
                                "difficulty": "medium",   // 难度：easy、medium、hard
                                "knowledge_points": ["知识点1", "知识点2"] // 与问题相关的知识点
                            }
                            ]
                            ```""",
                'variables': ['reference_text', 'topic', 'user_requirements', 'question_count', 'question_types', 'difficulty'],
                'version': '3.0'
            },
            'summary': {
                'name': '标准文档总结',
                'content': """请为以下内容生成一个全面、准确的摘要。
                            摘要应该捕捉文档的主要论点、关键概念和重要结论。

                            文档内容:
                            $content

                            要求:
                            1. 生成一个结构化的摘要，突出文档的主要部分和关键点。
                            2. 对于每个关键信息点，必须在句末通过方括号标注其来源编号，例如：[1]、[2]。
                            3. 如果一个句子综合了多个来源，请标注所有来源，例如：[1,2]。
                            4. 保持客观，不添加原文中没有的信息。

                            摘要:""",
                'variables': ['content'],
                'version': '3.0'
            }
        }
        
        for t_type, t_data in templates_to_create.items():
            try:
                obj, created = PromptTemplate.objects.update_or_create(
                    template_type=t_type,
                    name=t_data['name'],
                    defaults={
                        'content': t_data['content'],
                        'variables': t_data['variables'],
                        'version': t_data['version'],
                        'is_active': True
                    }
                )
                if created:
                    logger.info(f"创建默认提示词模板: {obj.name}")
                else:
                    logger.info(f"更新/确认默认提示词模板: {obj.name}")
            except Exception as e:
                logger.error(f"创建或更新模板 '{t_data['name']}' 失败: {e}")