import logging
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from .models import Project, ProjectDocument, ProjectStats

logger = logging.getLogger(__name__)


@api_view(['GET', 'POST'])
def project_list(request):
    """项目列表"""
    if request.method == 'GET':
        try:
            projects = Project.objects.filter(is_active=True)
            project_list = []
            
            for project in projects:
                project_data = {
                    'id': project.id,
                    'name': project.name,
                    'description': project.description,
                    'created_at': project.created_at.isoformat(),
                    'updated_at': project.updated_at.isoformat(),
                }
                
                # 添加统计信息
                try:
                    stats = project.stats
                    project_data.update({
                        'total_documents': stats.total_documents,
                        'total_chats': stats.total_chats,
                        'total_quizzes': stats.total_quizzes,
                        'completion_rate': stats.completion_rate,
                    })
                except ProjectStats.DoesNotExist:
                    project_data.update({
                        'total_documents': 0,
                        'total_chats': 0,
                        'total_quizzes': 0,
                        'completion_rate': 0.0,
                    })
                
                project_list.append(project_data)
            
            return Response({'projects': project_list})
            
        except Exception as e:
            logger.error(f"获取项目列表失败: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    elif request.method == 'POST':
        try:
            data = request.data
            name = data.get('name', '').strip()
            description = data.get('description', '').strip()
            
            if not name:
                return Response({'error': '项目名称不能为空'}, status=status.HTTP_400_BAD_REQUEST)
            
            # 创建项目
            project = Project.objects.create(
                name=name,
                description=description
            )
            
            # 创建统计记录
            ProjectStats.objects.create(project=project)
            
            logger.info(f"项目创建成功: {name}")
            
            return Response({
                'message': '项目创建成功',
                'project': {
                    'id': project.id,
                    'name': project.name,
                    'description': project.description,
                    'created_at': project.created_at.isoformat()
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"创建项目失败: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET', 'PUT', 'DELETE'])
def project_detail(request, project_id):
    """项目详情"""
    project = get_object_or_404(Project, id=project_id, is_active=True)
    
    if request.method == 'GET':
        try:
            # 获取项目文档
            documents = []
            for proj_doc in project.documents.all():
                documents.append({
                    'id': proj_doc.document.id,
                    'title': proj_doc.document.title,
                    'filename': proj_doc.document.filename,
                    'is_primary': proj_doc.is_primary,
                    'added_at': proj_doc.added_at.isoformat()
                })
            
            # 获取统计信息
            try:
                stats = project.stats
                stats_data = {
                    'total_documents': stats.total_documents,
                    'total_chats': stats.total_chats,
                    'total_quizzes': stats.total_quizzes,
                    'completion_rate': stats.completion_rate,
                    'last_activity': stats.last_activity.isoformat()
                }
            except ProjectStats.DoesNotExist:
                stats_data = {
                    'total_documents': 0,
                    'total_chats': 0,
                    'total_quizzes': 0,
                    'completion_rate': 0.0,
                    'last_activity': project.updated_at.isoformat()
                }
            
            return Response({
                'project': {
                    'id': project.id,
                    'name': project.name,
                    'description': project.description,
                    'created_at': project.created_at.isoformat(),
                    'updated_at': project.updated_at.isoformat(),
                    'documents': documents,
                    'stats': stats_data
                }
            })
            
        except Exception as e:
            logger.error(f"获取项目详情失败: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    elif request.method == 'PUT':
        try:
            data = request.data
            name = data.get('name', '').strip()
            description = data.get('description', '').strip()
            
            if name:
                project.name = name
            if description is not None:
                project.description = description
            
            project.save()
            
            return Response({
                'message': '项目更新成功',
                'project': {
                    'id': project.id,
                    'name': project.name,
                    'description': project.description,
                    'updated_at': project.updated_at.isoformat()
                }
            })
            
        except Exception as e:
            logger.error(f"更新项目失败: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    elif request.method == 'DELETE':
        try:
            project.is_active = False
            project.save()
            
            return Response({'message': '项目删除成功'})
            
        except Exception as e:
            logger.error(f"删除项目失败: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def project_add_document(request, project_id):
    """向项目添加文档"""
    try:
        project = get_object_or_404(Project, id=project_id, is_active=True)
        data = request.data
        document_id = data.get('document_id')
        is_primary = data.get('is_primary', False)
        
        if not document_id:
            return Response({'error': '缺少文档ID'}, status=status.HTTP_400_BAD_REQUEST)
        
        from ..documents.models import Document
        document = get_object_or_404(Document, id=document_id)
        
        # 检查是否已存在
        if ProjectDocument.objects.filter(project=project, document=document).exists():
            return Response({'error': '文档已在项目中'}, status=status.HTTP_400_BAD_REQUEST)
        
        # 添加文档
        ProjectDocument.objects.create(
            project=project,
            document=document,
            is_primary=is_primary
        )
        
        # 更新统计
        try:
            stats = project.stats
            stats.total_documents = project.documents.count()
            stats.save()
        except ProjectStats.DoesNotExist:
            ProjectStats.objects.create(
                project=project,
                total_documents=project.documents.count()
            )
        
        return Response({'message': '文档添加成功'})
        
    except Exception as e:
        logger.error(f"添加文档到项目失败: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
