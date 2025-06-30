# Generated manually for project-level chat isolation

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0001_initial'),
        ('chat', '0004_chatsession_created_at_conversation_message_count_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='conversation',
            name='project',
            field=models.ForeignKey(
                blank=True, 
                null=True, 
                on_delete=django.db.models.deletion.CASCADE, 
                to='projects.project', 
                verbose_name='所属项目'
            ),
        ),
        migrations.AddIndex(
            model_name='conversation',
            index=models.Index(fields=['user', 'project', '-updated_at'], name='chat_convers_user_id_project_id_updated_at_idx'),
        ),
        migrations.AddIndex(
            model_name='conversation',
            index=models.Index(fields=['project', '-updated_at'], name='chat_convers_project_id_updated_at_idx'),
        ),
    ]
