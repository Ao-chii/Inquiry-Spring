"""
初始化AI服务管理命令
"""
import logging
import os
from django.core.management.base import BaseCommand
from inquiryspring_backend.ai_services.models import AIModel, PromptTemplate
from inquiryspring_backend.ai_services.rag_engine import initialize_ai_services

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '初始化AI服务，创建或更新默认模型和提示词模板'

    def handle(self, *args, **options):
        self.stdout.write('开始初始化AI服务...')
        
        self.create_or_update_default_models()
        
        # 初始化提示词模板
        from inquiryspring_backend.ai_services.prompt_manager import PromptManager
        PromptManager.create_default_templates()
        
        # 初始化RAG引擎及其他AI服务
        initialize_ai_services()
        
        self.stdout.write(self.style.SUCCESS('AI服务初始化完成!'))
    
    def create_or_update_default_models(self):
        """创建或更新默认的AI模型配置"""
        # 获取环境变量中的API密钥
        gemini_api_key = os.getenv('GOOGLE_API_KEY', '')
        if not gemini_api_key:
            self.stdout.write(self.style.WARNING('警告: GOOGLE_API_KEY 环境变量未设置，将无法初始化Gemini模型。'))

        # 定义希望设为默认的Gemini模型
        default_gemini_model_data = {
            'name': 'gemini',
            'provider': 'gemini',
            'model_id': 'gemini-2.5-flash-preview-05-20',
            'api_key': gemini_api_key, # 从环境变量获取API密钥
            'max_tokens': 8000, # Flash模型通常有较大的上下文窗口，这里设一个参考值
            'temperature': 0.7,
            'is_active': True,
            'is_default': True # 期望这个是默认
        }

        # 其他可能存在的模型（如Pro版本或本地模型）
        other_models_data = [
            {
                'name': 'Gemini Flash',
                'provider': 'gemini',
                'model_id': 'gemini-2.5-flash-preview-05-20',
                'api_key': gemini_api_key, # 同样从环境变量获取
                'max_tokens': 2000,
                'temperature': 0.7,
                'is_active': False, # 由于之前的配额问题，默认不激活
                'is_default': False
            },
            {
                'name': '本地模型',
                'provider': 'local',
                'model_id': 'local-model', # 路径或标识符
                'api_base': os.path.join(os.getenv('LOCAL_MODEL_PATH', ''), 'models/your-local-model'), # 使用环境变量设置本地模型路径
                'max_tokens': 1500,
                'temperature': 0.7,
                'is_active': True, # 通常本地模型可以保持激活
                'is_default': False
            }
        ]
        
        created_count = 0
        updated_count = 0

        # 首先，确保所有现有的Gemini模型都不是默认，除了我们即将设置的最新版本
        AIModel.objects.filter(provider='gemini', is_default=True).exclude(
            model_id=default_gemini_model_data['model_id']
        ).update(is_default=False)
        updated_count += AIModel.objects.filter(provider='gemini', is_default=False, name__contains='Gemini').count() # 粗略计数

        # 创建或更新默认的Gemini Flash模型
        gemini_flash_model, created = AIModel.objects.update_or_create(
            provider=default_gemini_model_data['provider'], 
            model_id=default_gemini_model_data['model_id'],
            defaults=default_gemini_model_data
        )
        if created:
            self.stdout.write(f"创建默认AI模型: {gemini_flash_model.name}")
            created_count += 1
        else:
            # 如果是更新，确保is_default为True和is_active为True
            if not gemini_flash_model.is_default or not gemini_flash_model.is_active or not gemini_flash_model.api_key:
                gemini_flash_model.is_default = True
                gemini_flash_model.is_active = True
                # 仅当数据库中没有api_key时，才从环境变量更新
                if not gemini_flash_model.api_key and gemini_api_key:
                    gemini_flash_model.api_key = gemini_api_key
                gemini_flash_model.save()
            self.stdout.write(f"更新/确认默认AI模型: {gemini_flash_model.name}")
            updated_count += 1

        # 处理其他模型（例如，确保Pro版本不是默认且根据需要设置为非激活）
        for model_data in other_models_data:
            obj, created = AIModel.objects.update_or_create(
                provider=model_data['provider'],
                model_id=model_data['model_id'],
                defaults=model_data
            )
            if created:
                self.stdout.write(f"创建AI模型: {obj.name}")
                created_count +=1
            else:
                self.stdout.write(f"更新/确认AI模型: {obj.name}")
                updated_count +=1
        
        self.stdout.write(f"共创建 {created_count} 个AI模型配置，更新/确认 {updated_count} 个AI模型配置。") 