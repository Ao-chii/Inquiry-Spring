"""
初始化AI服务管理命令
"""
import logging
import os
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings
from inquiryspring_backend.ai_services.models import AIModel, PromptTemplate
from inquiryspring_backend.ai_services.rag_engine import VECTOR_STORE_DIR

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '初始化AI服务，包括创建默认模型、提示词模板'

    def handle(self, *args, **options):
        self.stdout.write('开始初始化AI服务...')
        
        # 1. 创建或更新默认的AI模型配置
        self.create_or_update_default_models()
        
        # 2. 初始化提示词模板
        self.stdout.write("正在初始化提示词模板...")
        from inquiryspring_backend.ai_services.prompt_manager import PromptManager
        PromptManager.create_default_templates()
        self.stdout.write(self.style.SUCCESS("提示词模板初始化完成。"))
        
        # 3. 初始化RAG引擎及其他AI服务
        self.initialize_ai_services()
        
        self.stdout.write(self.style.SUCCESS('AI服务初始化全部完成!'))

    def create_or_update_default_models(self):
        """创建或更新默认的AI模型配置"""
        self.stdout.write("正在创建/更新默认AI模型...")
        # 获取环境变量中的API密钥
        gemini_api_key = os.getenv('GOOGLE_API_KEY', '')
        local_model_path = os.getenv('LOCAL_MODEL_PATH')

        if not gemini_api_key:
            self.stdout.write(self.style.WARNING('警告: GOOGLE_API_KEY 环境变量未设置，将无法初始化在线Gemini模型。'))
        
        # 声明式定义所有期望存在的模型配置
        model_configs = [
            {
                'name': 'Gemini Flash',
                'provider': 'gemini',
                'model_id': 'gemini-2.5-flash-preview-05-20',
                'api_key': gemini_api_key,
                'max_tokens': 10000,
                'temperature': 0.7,
                'is_active': bool(gemini_api_key), # 仅当有API Key时激活
                'is_default': True # 期望这个是默认
            },
            {
                'name': '本地模型',
                'provider': 'local',
                'model_id': 'local-model',
                'api_base': local_model_path if local_model_path else '', # api_base现在直接指向模型路径
                'max_tokens': 2000,
                'temperature': 0.7,
                'is_active': bool(local_model_path and os.path.exists(local_model_path)), # 仅当路径有效时激活
                'is_default': False
            }
        ]
        
        created_count = 0
        updated_count = 0

        # 首先，将所有模型的is_default标志重置为False
        # 这是一个安全的操作，确保只有一个模型最终被设为默认
        AIModel.objects.all().update(is_default=False)

        # 遍历声明式配置列表，创建或更新模型
        for config in model_configs:
            # unique_identifier用于查找现有记录
            unique_identifier = {'provider': config['provider'], 'model_id': config['model_id']}
            
            # 从配置中移除is_default，因为我们将单独处理它
            is_default_flag = config.pop('is_default', False)
            
            obj, created = AIModel.objects.update_or_create(
                **unique_identifier,
                defaults=config
            )

            if created:
                self.stdout.write(f"创建AI模型: {obj.name}")
                created_count += 1
            else:
                self.stdout.write(f"更新/确认AI模型: {obj.name}")
                updated_count += 1
                
            # 如果这个模型被标记为默认，就更新它的is_default字段
            if is_default_flag:
                obj.is_default = True
                obj.save()
        
        self.stdout.write(f"共创建 {created_count} 个AI模型配置，更新/确认 {updated_count} 个AI模型配置。") 
        self.stdout.write(self.style.SUCCESS("AI模型配置初始化完成。")) 

    def initialize_ai_services(self):
        """初始化所有AI服务相关组件"""
        try:
            # 初始化提示词模板
            from inquiryspring_backend.ai_services.prompt_manager import PromptManager
            logger.info("正在初始化提示词模板...")
            PromptManager.create_default_templates()
            
            # 确保向量存储目录存在
            os.makedirs(VECTOR_STORE_DIR, exist_ok=True)
            
            # 初始化默认的LLM客户端（验证连接）
            from inquiryspring_backend.ai_services.llm_client import LLMClientFactory
            logger.info("正在初始化LLM客户端...")
            client = LLMClientFactory.create_client()
            
            # 初始化Neo4j知识图谱
            from inquiryspring_backend.ai_services.neo4j_manager import initialize_neo4j
            logger.info("正在初始化Neo4j知识图谱...")
            neo4j_success = initialize_neo4j()
            if neo4j_success:
                logger.info("Neo4j知识图谱初始化成功")
            else:
                logger.warning("Neo4j知识图谱初始化失败，图谱检索功能将不可用")
            
            # 检查本地模型路径是否有效
            local_model_path = os.environ.get('LOCAL_MODEL_PATH')
            if local_model_path and os.path.exists(local_model_path):
                logger.info(f"检测到有效的本地模型路径: {local_model_path}")
            
            # 检查是否需要处理未处理的文档
            from inquiryspring_backend.documents.models import Document
            unprocessed_docs = Document.objects.filter(is_processed=False).count()
            if unprocessed_docs > 0:
                logger.info(f"发现 {unprocessed_docs} 个未处理的文档。可以使用process_documents管理命令进行处理。")
            
            logger.info("AI服务初始化完成。")
        except Exception as e:
            logger.exception(f"初始化AI服务时出错: {e}") 