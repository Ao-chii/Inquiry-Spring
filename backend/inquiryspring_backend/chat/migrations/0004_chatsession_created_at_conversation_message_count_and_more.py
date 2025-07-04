# Generated by Django 5.2.1 on 2025-06-28 09:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0003_chatsession_is_ready'),
    ]

    operations = [
        migrations.AddField(
            model_name='chatsession',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True, verbose_name='创建时间'),
        ),
        migrations.AddField(
            model_name='conversation',
            name='message_count',
            field=models.IntegerField(default=0, verbose_name='消息数量'),
        ),
        migrations.AddField(
            model_name='conversation',
            name='username',
            field=models.CharField(blank=True, max_length=100, verbose_name='用户名'),
        ),
        migrations.AddField(
            model_name='message',
            name='document_id',
            field=models.IntegerField(blank=True, null=True, verbose_name='关联文档ID'),
        ),
        migrations.AddField(
            model_name='message',
            name='document_title',
            field=models.CharField(blank=True, max_length=200, verbose_name='文档标题'),
        ),
    ]
