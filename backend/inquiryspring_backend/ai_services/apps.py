from django.apps import AppConfig
import logging
from django.db import connection
from django.db.models.signals import post_migrate

logger = logging.getLogger(__name__)

class AiServicesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'inquiryspring_backend.ai_services'
    verbose_name = 'AI服务'

    def ready(self):
        # 导入需要在应用启动时使用的模块
        # 但不立即初始化数据库对象
        # 避免在应用加载时访问数据库
        # 我们将通过信号在第一次请求时初始化，或使用管理命令
        
        # 添加初始化方法供后续调用
        def initialize_services():
            try:
                # 延迟导入，避免循环依赖
                from .management.commands.init_ai_services import Command as InitCommand
                
                # 检查相关表是否存在
                table_names = connection.introspection.table_names()
                if 'ai_services_aimodel' in table_names and 'ai_services_prompttemplate' in table_names:
                    logger.info("开始初始化AI服务...")
                    # 使用CommandClass中的初始化方法
                    init_cmd = InitCommand()
                    init_cmd.initialize_ai_services()
                    logger.info("AI服务初始化完成")
                else:
                    logger.warning("数据库表尚未创建，跳过AI服务初始化")
            except Exception as e:
                logger.exception("AI服务初始化失败")
                # 初始化失败不应该阻止应用启动
                # raise e
        
        # 将初始化方法保存为类属性，便于其他地方调用
        self.initialize_services = initialize_services
        
        # 从Django 3.2开始，推荐使用post_migrate信号而非在ready()中直接访问数据库
        
        # 注册post_migrate信号处理器
        def post_migrate_callback(sender, **kwargs):
            # 只在当前应用的迁移完成后执行
            if sender.name == self.name:
                initialize_services()
        
        post_migrate.connect(post_migrate_callback, sender=self)