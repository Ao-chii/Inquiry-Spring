from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from inquiryspring_backend.chat.models import Conversation
from inquiryspring_backend.projects.models import Project


class Command(BaseCommand):
    help = '将现有对话迁移到项目中'

    def handle(self, *args, **options):
        self.stdout.write('开始迁移对话到项目...')
        
        # 获取所有没有项目关联的对话
        conversations_without_project = Conversation.objects.filter(project__isnull=True)
        total_conversations = conversations_without_project.count()
        
        if total_conversations == 0:
            self.stdout.write(self.style.SUCCESS('没有需要迁移的对话'))
            return
        
        self.stdout.write(f'找到 {total_conversations} 个需要迁移的对话')
        
        migrated_count = 0
        created_projects = 0
        
        for conv in conversations_without_project:
            try:
                # 如果对话有关联用户
                if conv.user:
                    # 获取或创建用户的默认项目
                    default_project, created = Project.objects.get_or_create(
                        user=conv.user,
                        name=f"{conv.user.username}的默认项目",
                        defaults={
                            'description': '系统自动创建的默认项目，用于存放历史对话记录'
                        }
                    )
                    
                    if created:
                        created_projects += 1
                        self.stdout.write(f"为用户 {conv.user.username} 创建默认项目")
                    
                    # 关联对话到默认项目
                    conv.project = default_project
                    conv.save()
                    migrated_count += 1
                    
                elif conv.username:
                    # 如果只有用户名，尝试创建或获取用户
                    user, user_created = User.objects.get_or_create(
                        username=conv.username,
                        defaults={
                            'email': f"{conv.username}@example.com"
                        }
                    )
                    
                    if user_created:
                        self.stdout.write(f"为用户名 {conv.username} 创建用户账户")
                    
                    # 获取或创建默认项目
                    default_project, created = Project.objects.get_or_create(
                        user=user,
                        name=f"{user.username}的默认项目",
                        defaults={
                            'description': '系统自动创建的默认项目，用于存放历史对话记录'
                        }
                    )
                    
                    if created:
                        created_projects += 1
                        self.stdout.write(f"为用户 {user.username} 创建默认项目")
                    
                    # 更新对话关联
                    conv.user = user
                    conv.project = default_project
                    conv.save()
                    migrated_count += 1
                    
                else:
                    # 没有用户信息的对话，创建匿名项目
                    anonymous_user, _ = User.objects.get_or_create(
                        username='anonymous',
                        defaults={
                            'email': 'anonymous@example.com'
                        }
                    )
                    
                    anonymous_project, created = Project.objects.get_or_create(
                        user=anonymous_user,
                        name="匿名用户项目",
                        defaults={
                            'description': '匿名用户的对话记录'
                        }
                    )
                    
                    if created:
                        created_projects += 1
                        self.stdout.write("创建匿名用户项目")
                    
                    conv.user = anonymous_user
                    conv.project = anonymous_project
                    conv.save()
                    migrated_count += 1
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'迁移对话 {conv.id} 失败: {e}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'迁移完成！\n'
                f'- 迁移对话数: {migrated_count}/{total_conversations}\n'
                f'- 创建项目数: {created_projects}'
            )
        )
