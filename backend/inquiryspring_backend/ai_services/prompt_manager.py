"""
提示词管理模块 - 负责加载、管理和渲染提示词模板
增强版本支持JSON Schema和Few-shot示例
"""
import re
import json
import logging
from typing import Dict, List, Any, Optional, Union, Type
from string import Template

from .models import PromptTemplate
from pydantic import BaseModel
from .structured_output import StructuredOutputProcessor

logger = logging.getLogger(__name__)

class PromptManager:
    # 预定义的示例存储
    _examples_cache = {}
    
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
                    # 获取知识来源标识，如果存在
                    knowledge_source = variables.get('knowledge_source', '参考资料')
                    # 根据知识来源类型设置不同的标题
                    variables['reference_text_section'] = f"{knowledge_source}:\n{variables['reference_text']}"

                    variables['reference_instruction'] = "请严格根据上面提供的参考资料来回答问题。"
                else:
                    variables['reference_text_section'] = ""
                    variables['reference_instruction'] = "基于你的知识提供最准确的回答。不要显示任何来源标识或索引标记。"
            
            if '$conversation_history_section' in template_content:
                if variables.get('conversation_history'):
                    variables['conversation_history_section'] = f"对话历史:\n{variables['conversation_history']}"
                else:
                    variables['conversation_history_section'] = ""
                    
            # 处理JSON Schema部分（如果存在）
            if '$json_schema_section' in template_content and variables.get('output_schema'):
                schema_obj = variables.get('output_schema')
                if isinstance(schema_obj, Type) and issubclass(schema_obj, BaseModel):
                    # 如果是Pydantic模型类，使用StructuredOutputProcessor获取schema
                    processor = StructuredOutputProcessor()
                    schema_str = processor.get_json_schema(schema_obj)
                    variables['json_schema_section'] = f"请严格按照以下JSON Schema格式返回:\n```json\n{schema_str}\n```"
                elif isinstance(schema_obj, dict):
                    # 如果已经是JSON schema字典，直接使用
                    schema_str = json.dumps(schema_obj, ensure_ascii=False, indent=2)
                    variables['json_schema_section'] = f"请严格按照以下JSON Schema格式返回:\n```json\n{schema_str}\n```"
                else:
                    variables['json_schema_section'] = ""
                    
            # 处理示例部分（如果存在）
            if '$examples_section' in template_content and variables.get('examples'):
                examples = variables.get('examples')
                if examples:
                    examples_str = json.dumps(examples, ensure_ascii=False, indent=2)
                    variables['examples_section'] = f"以下是符合要求的示例输出:\n```json\n{examples_str}\n```"
                else:
                    variables['examples_section'] = ""
                
            template_obj = Template(template_content)
            return template_obj.safe_substitute(variables)
        except Exception as e:
            logger.exception(f"渲染提示词模板失败: {str(e)}")
            return f"模板渲染错误: {str(e)}"
    
    @staticmethod
    def render_by_type(
        template_type: str, 
        variables: Dict[str, Any], 
        name: str = None,
        output_schema: Type[BaseModel] = None,
        examples: List[Dict] = None
    ) -> str:
        """
        根据类型获取并渲染提示词，支持JSON Schema和示例
        
        Args:
            template_type: 模板类型
            variables: 变量字典
            name: 模板名称，如果不提供则使用该类型的默认模板
            output_schema: Pydantic模型类，用于生成JSON Schema
            examples: Few-shot示例列表
            
        Returns:
            渲染后的提示词，如果模板不存在则返回默认提示词
        """
        template = PromptManager.get_template(template_type, name)
        
        if not template:
            logger.error(f"无法找到类型为 '{template_type}' 的活跃模板，渲染失败。")
            # 在严格模式下，我们不应使用硬编码的后备模板
            return f"错误：找不到类型为 '{template_type}' 的模板。"
        
        # 添加Schema和示例到变量字典
        if output_schema:
            variables['output_schema'] = output_schema
        if examples:
            variables['examples'] = examples
            
        return PromptManager.render_template(template.content, variables)
    
    @staticmethod
    def render_with_schema(
        template_type: str,
        variables: Dict[str, Any],
        output_schema: Type[BaseModel],
        examples: List[Dict] = None,
        name: str = None
    ) -> str:
        """
        便捷方法：用JSON Schema和示例渲染提示词
        
        这是render_by_type的简化版本，专门用于结构化输出
        """
        # 模板中已有schema和examples占位符，使用标准渲染
        return PromptManager.render_by_type(template_type, variables, name, output_schema, examples)
    
    @staticmethod
    def _get_or_create_examples(example_type: str) -> List[Dict]:
        """获取或创建指定类型的示例"""
        if example_type in PromptManager._examples_cache:
            return PromptManager._examples_cache[example_type]
            
        examples = []
        
        # 根据类型创建预定义示例
        if example_type == 'quiz':
            examples = [{
                "questions": [
                    {
                        "content": "地球是太阳系中第几颗行星？",
                        "question_type": "MC",
                        "options": [
                            {"id": "A", "text": "第一颗"},
                            {"id": "B", "text": "第三颗"},
                            {"id": "C", "text": "第五颗"},
                            {"id": "D", "text": "第七颗"}
                        ],
                        "correct_answer": "B",
                        "explanation": "地球是太阳系中第三颗行星，位于金星和火星之间。",
                        "difficulty": "easy",
                        "knowledge_points": ["天文学", "太阳系"]
                    },
                    {
                        "content": "以下哪些不是地球的自然卫星？",
                        "question_type": "MCM",
                        "options": [
                            {"id": "A", "text": "月球"},
                            {"id": "B", "text": "火星"},
                            {"id": "C", "text": "太阳"},
                            {"id": "D", "text": "国际空间站"}
                        ],
                        "correct_answer": ["B", "C", "D"],
                        "explanation": "月球是地球唯一的自然卫星。",
                        "difficulty": "easy",
                        "knowledge_points": ["天文学", "地球系统"]
                    },
                    {
                        "content": "光合作用是植物将光能转化为化学能的过程。对/错？",
                        "question_type": "TF",
                        "options": [],
                        "correct_answer": "对",
                        "explanation": "光合作用确实是植物利用光能合成有机物，储存化学能的过程。",
                        "difficulty": "medium",
                        "knowledge_points": ["生物学", "植物生理"]
                    },
                    {
                        "content": "水的化学式是____。",
                        "question_type": "FB",
                        "options": [],
                        "correct_answer": "H2O",
                        "explanation": "水分子由两个氢原子和一个氧原子组成。",
                        "difficulty": "medium",
                        "knowledge_points": ["化学", "分子式"]
                    },
                    {
                        "content": "简述牛顿第三定律。",
                        "question_type": "SA",
                        "options": [],
                        "correct_answer": "牛顿第三定律指出，对于每一个作用力，都存在一个大小相等、方向相反的反作用力。",
                        "explanation": "牛顿第三定律是经典力学的三大基本定律之一，描述了物体之间相互作用的规律。",
                        "difficulty": "hard",
                        "knowledge_points": ["物理学", "经典力学", "牛顿定律"]
                    },
                    {
                        "content": "以下哪个国家不属于G7集团？",
                        "question_type": "MC",
                        "options": [
                            {"id": "A", "text": "法国"},
                            {"id": "B", "text": "德国"},
                            {"id": "C", "text": "俄罗斯"},
                            {"id": "D", "text": "日本"}
                        ],
                        "correct_answer": "C",
                        "explanation": "G7集团是由七个主要发达国家组成的政府间政治论坛。俄罗斯曾是G8成员，但在2014年因克里米亚事件被暂停成员资格。",
                        "difficulty": "hard",
                        "knowledge_points": ["国际关系", "地理", "G7"]
                    },
                    {
                        "content": "哪些编程语言通常被认为是面向对象的？",
                        "question_type": "MCM",
                        "options": [
                            {"id": "A", "text": "C"},
                            {"id": "B", "text": "Python"},
                            {"id": "C", "text": "Java"},
                            {"id": "D", "text": "汇编语言"}
                        ],
                        "correct_answer": ["B", "C"],
                        "explanation": "Python和Java是典型的面向对象编程语言，而C是面向过程的，汇编语言是低级语言。",
                        "difficulty": "medium",
                        "knowledge_points": ["计算机科学", "编程语言", "面向对象"]
                    }
                ]
            }]
        elif example_type == 'chat':
            examples = [{
                "answer": "二氧化碳是一种无色无味的气体，是地球温室效应的主要贡献者之一。在常温常压下，二氧化碳以气态存在，分子式为CO₂。工业上，它被广泛用于饮料碳酸化、灭火器和制冷（干冰）等领域。",
                "sources": []
            }]
        elif example_type == 'summary':
            examples = [{
                "summary": """# 人工智能：概念、应用与未来

本文档深入探讨了**人工智能（AI）**的核心概念、在各行业的广泛应用，并对未来发展趋势进行了展望。AI作为模拟人类智能的计算机科学分支，正以前所未有的速度改变着世界。

## 核心技术与分支

AI领域主要由几个核心技术分支驱动，其中最重要的是**机器学习（ML）**和**深度学习（DL）**。机器学习允许系统从数据中自动学习和改进，而深度学习则通过模拟人脑的神经网络结构，在处理复杂模式（如图像和语音）方面取得了巨大成功。

## 跨行业应用

AI技术已渗透到众多行业，展现出巨大的商业价值。在**医疗领域**，AI被用于辅助诊断和药物研发；在**金融领域**，它被用于风险评估和算法交易。此外，在自动驾驶、个性化推荐和智能客服等方面，AI也扮演着关键角色。

**核心要点**
- AI的核心是让机器模仿人类的智能行为。
- 机器学习和深度学习是当前AI发展的两大主要驱动力。
- AI在医疗、金融、交通等多个领域都有颠覆性的应用。
- 未来的AI发展将更加注重可解释性、公平性和安全性。"""
            }]
            
        # 缓存示例以供后续使用
        PromptManager._examples_cache[example_type] = examples
        return examples
    
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

                            **严格要求**:
                            1. **绝对禁止**在回答中使用任何形式的索引标记，包括但不限于：[1]、[2]、[3]、(1)、(2)、①、②等。
                            2. **绝对禁止**添加任何引用标记、来源标识或参考文献标记。
                            3. **必须**直接回答问题，不使用"根据资料"、"文档显示"等表述。
                            4. $reference_instruction
                            5. 不要编造不在参考资料中的信息。如果参考资料不足以回答问题，请明确说明。
                            6. 使用清晰的markdown格式回答，适当使用**粗体**强调重点，使用列表组织信息。
                            7. 确保回答结构清晰，便于阅读。

                            $json_schema_section

                            $examples_section

                            请开始你的回答:""",
                'variables': ['query', 'reference_text', 'conversation_history', 'output_schema', 'examples', 'knowledge_source'],
                'version': '5.5'
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
                            
                            注意事项:
                            1. 每道题目应包含明确的知识点标注，便于学习者了解所考察的知识领域。
                            2. 难度设置应符合要求，请确保题目既有挑战性又不偏离主题范围。
                            
                            $json_schema_section
                            
                            $examples_section

                            请严格按指定格式返回，不要有其他文字。请确保返回格式符合JSON Schema要求，可以被直接解析。""",
                'variables': ['reference_text', 'topic', 'user_requirements', 'question_count', 'question_types', 'difficulty', 'output_schema', 'examples'],
                'version': '5.2'
            },
            'summary': {
                'name': '标准文档总结',
                'content': """你是一位专业的文档分析师和内容编辑。请为以下内容生成一个结构清晰、美观的Markdown格式摘要。

                            文档内容:
                            $content

                            **严格要求**:
                            1.  **绝对禁止**在摘要中使用任何形式的索引标记，包括但不限于：[1]、[2]、[3]、(1)、(2)、①、②等。
                            2.  **绝对禁止**添加任何引用标记、来源标识或参考文献标记。
                            3.  **必须**直接陈述事实，不使用"根据文档"、"文档显示"等表述。
                            4.  **使用Markdown语法**进行格式化，以增强可读性。
                            5.  根据文档大小和内容结构进行排版，比如考虑包含以下部分：
                                *   一个一级标题 (`#`)，作为整个文档的总结性标题。
                                *   一段引言，简要介绍文档的核心主题。
                                *   至少两个二级标题 (`##`) 的核心章节，深入阐述关键内容。
                                *   一个名为"**核心要点**"的章节，使用无序列表 (`-`) 总结出3-5个最重要的结论或要点。
                            6.  在适当的地方使用粗体 (`**text**`) 来强调关键词。
                            7.  保持客观，不添加原文中没有的信息。
                            8.  **直接返回Markdown格式的摘要文本**，不要包装在JSON中。

                            请开始生成你的Markdown格式摘要:""",
                'variables': ['content'],
                'version': '5.3'
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