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


@api_view(['POST'])
def project_upload_document(request, project_id):
    """为项目上传文档并自动进行RAG处理"""
    try:
        project = get_object_or_404(Project, id=project_id, is_active=True)

        if 'file' not in request.FILES:
            return Response({'error': '没有选择文件'}, status=status.HTTP_400_BAD_REQUEST)

        file = request.FILES['file']

        if file.name == '':
            return Response({'error': '没有选择文件'}, status=status.HTTP_400_BAD_REQUEST)

        # 导入文档处理相关模块
        from ..documents.views import allowed_file
        from ..documents.document_processor import document_processor
        from ..documents.models import Document
        from django.conf import settings
        from django.utils import timezone
        import os
        import re

        def secure_filename(filename):
            """安全的文件名处理"""
            filename = re.sub(r'[^\w\s\-\.]', '', filename).strip()
            filename = re.sub(r'[\-\s]+', '_', filename)
            return filename

        if not allowed_file(file.name):
            return Response({'error': '不支持的文件类型'}, status=status.HTTP_400_BAD_REQUEST)

        if not document_processor.available:
            return Response({'error': '文档处理功能不可用'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 保存文件
        filename = secure_filename(file.name)
        upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads')
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, filename)

        with open(file_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)

        # 验证文件
        validation = document_processor.validate_file(file_path, filename)
        if not validation['valid']:
            if os.path.exists(file_path):
                os.remove(file_path)
            return Response({'error': validation['error']}, status=status.HTTP_400_BAD_REQUEST)

        # 创建Document记录
        document = Document.objects.create(
            title=f"项目文档-{filename}",
            file_type=validation['file_type'],
            file_size=validation['file_size'],
            processing_status='processing'
        )

        # 移动文件到最终位置
        final_dir = os.path.join(settings.MEDIA_ROOT, 'documents', str(document.id))
        os.makedirs(final_dir, exist_ok=True)
        final_path = os.path.join(final_dir, filename)
        os.rename(file_path, final_path)

        # 更新document记录
        document.file.name = f'documents/{document.id}/{filename}'
        document.save()

        # 提取文档内容
        extraction_result = document_processor.extract_text(final_path, filename)

        if extraction_result['success']:
            # 更新文档记录
            document.content = extraction_result['content']
            document.metadata = extraction_result['metadata']
            document.is_processed = True
            document.processing_status = 'completed'
            document.processed_at = timezone.now()
            document.save()

            # 立即进行RAG处理
            from ..ai_services import process_document_for_rag
            rag_processing_result = process_document_for_rag(document.id, force_reprocess=True)

            if rag_processing_result:
                logger.info(f"项目文档RAG处理成功: {filename}")
            else:
                logger.warning(f"项目文档RAG处理失败: {filename}")

            # 添加文档到项目
            ProjectDocument.objects.create(
                project=project,
                document=document,
                is_primary=request.data.get('is_primary', False)
            )

            # 更新项目统计
            try:
                stats = project.stats
                stats.total_documents = project.documents.count()
                stats.save()
            except ProjectStats.DoesNotExist:
                ProjectStats.objects.create(
                    project=project,
                    total_documents=project.documents.count()
                )

            logger.info(f"项目文档上传成功: {filename}")

            return Response({
                'message': '文档上传成功并已添加到项目',
                'document_id': document.id,
                'filename': filename,
                'content_length': len(extraction_result['content']),
                'file_type': validation['file_type'],
                'rag_processed': rag_processing_result
            })
        else:
            # 处理失败
            document.processing_status = 'failed'
            document.error_message = extraction_result['error']
            document.save()

            return Response({
                'error': f'文档处理失败: {extraction_result["error"]}',
                'document_id': document.id
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    except Exception as e:
        logger.error(f"项目文档上传失败: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def generate_project_summary(request, project_id):
    """生成项目摘要 - 基于项目中的所有文档"""
    try:
        project = get_object_or_404(Project, id=project_id, is_active=True)
        project_docs = ProjectDocument.objects.filter(project=project)

        if not project_docs.exists():
            return Response({'error': '项目中没有文档'}, status=status.HTTP_400_BAD_REQUEST)

        # 收集所有文档的摘要
        document_summaries = []
        failed_docs = []

        for proj_doc in project_docs:
            try:
                # 确保文档已进行RAG处理
                from ..ai_services import process_document_for_rag
                rag_processed = process_document_for_rag(proj_doc.document.id, force_reprocess=False)

                if not rag_processed:
                    logger.warning(f"文档 {proj_doc.document.id} RAG处理失败")
                    failed_docs.append(proj_doc.document.title)
                    continue

                # 生成文档摘要
                from ..ai_services.rag_engine import RAGEngine
                rag_engine = RAGEngine(document_id=proj_doc.document.id)
                doc_summary_result = rag_engine.handle_summary(
                    document_id=proj_doc.document.id,
                    user=getattr(request, 'user', None),
                    session_id=request.session.session_key
                )

                if 'error' not in doc_summary_result:
                    document_summaries.append({
                        'document_id': proj_doc.document.id,
                        'document_title': proj_doc.document.title,
                        'summary': doc_summary_result.get('text', ''),
                        'is_primary': proj_doc.is_primary
                    })
                else:
                    failed_docs.append(proj_doc.document.title)

            except Exception as e:
                logger.error(f"处理文档 {proj_doc.document.title} 摘要失败: {e}")
                failed_docs.append(proj_doc.document.title)

        if not document_summaries:
            return Response({'error': '无法生成任何文档摘要'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 生成项目整体摘要
        combined_content = f"项目名称: {project.name}\n"
        if project.description:
            combined_content += f"项目描述: {project.description}\n"
        combined_content += f"文档数量: {len(document_summaries)}\n\n"
        combined_content += "各文档摘要:\n"

        for i, doc_sum in enumerate(document_summaries, 1):
            primary_mark = " (主要文档)" if doc_sum['is_primary'] else ""
            combined_content += f"{i}. {doc_sum['document_title']}{primary_mark}:\n{doc_sum['summary']}\n\n"

        # 使用RAGEngine生成项目整体摘要
        from ..ai_services.rag_engine import RAGEngine
        rag_engine = RAGEngine()

        # 构建项目摘要提示词
        project_summary_prompt = f"""请基于以下信息生成一个综合的项目摘要：

{combined_content}

请生成一个简洁而全面的项目摘要，包括：
1. 项目的主要内容和目标
2. 涉及的关键主题和知识点
3. 文档之间的关联性
4. 学习建议或重点

摘要应该帮助用户快速了解整个项目的核心内容。"""

        system_prompt = "你是一个专业的项目分析专家。请基于提供的文档摘要，生成一个综合的项目摘要。"

        response = rag_engine.llm_client.generate_text(
            prompt=project_summary_prompt,
            system_prompt=system_prompt,
            task_type='project_summary',
            user=getattr(request, 'user', None),
            session_id=request.session.session_key
        )

        project_summary = response.get('text', '无法生成项目摘要')

        logger.info(f"项目摘要生成成功: {project.name}")

        result = {
            'message': '项目摘要生成成功',
            'project_id': project_id,
            'project_name': project.name,
            'project_summary': project_summary,
            'document_count': len(document_summaries),
            'document_summaries': document_summaries,
            'processing_time': response.get('processing_time', 0)
        }

        if failed_docs:
            result['warnings'] = f"以下文档处理失败: {', '.join(failed_docs)}"

        return Response(result)

    except Exception as e:
        logger.error(f"生成项目摘要失败: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def generate_project_quiz(request, project_id):
    """为项目生成测验 - 基于项目中的主要文档"""
    try:
        project = get_object_or_404(Project, id=project_id, is_active=True)
        project_docs = ProjectDocument.objects.filter(project=project)

        if not project_docs.exists():
            return Response({'error': '项目中没有文档'}, status=status.HTTP_400_BAD_REQUEST)

        # 获取请求参数
        data = request.data
        user_query = data.get('query', f'{project.name}相关测验')
        question_count = data.get('question_count', 5)
        question_types = data.get('question_types', ['MC', 'TF'])
        difficulty = data.get('difficulty', 'medium')

        # 优先使用主要文档，如果没有则使用第一个文档
        primary_doc = project_docs.filter(is_primary=True).first()
        if not primary_doc:
            primary_doc = project_docs.first()

        # 确保选中的文档已进行RAG处理
        from ..ai_services import process_document_for_rag
        rag_processed = process_document_for_rag(primary_doc.document.id, force_reprocess=False)

        if not rag_processed:
            logger.warning(f"文档 {primary_doc.document.id} RAG处理失败，尝试强制重新处理")
            rag_processed = process_document_for_rag(primary_doc.document.id, force_reprocess=True)

        if not rag_processed:
            return Response({'error': '文档RAG处理失败'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 生成测验
        from ..ai_services.rag_engine import RAGEngine
        rag_engine = RAGEngine(document_id=primary_doc.document.id)

        quiz_result = rag_engine.handle_quiz(
            user_query=user_query,
            document_id=primary_doc.document.id,
            question_count=question_count,
            question_types=question_types,
            difficulty=difficulty,
            user=getattr(request, 'user', None),
            session_id=request.session.session_key
        )

        if 'error' in quiz_result:
            return Response({'error': quiz_result['error']}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 更新项目统计
        try:
            stats = project.stats
            stats.total_quizzes += 1
            stats.save()
        except ProjectStats.DoesNotExist:
            ProjectStats.objects.create(
                project=project,
                total_quizzes=1
            )

        logger.info(f"项目测验生成成功: {project.name}")

        return Response({
            'message': '测验生成成功',
            'project_id': project_id,
            'project_name': project.name,
            'quiz_id': quiz_result.get('quiz_id'),
            'quiz_data': quiz_result.get('quiz_data', []),
            'based_on_document': primary_doc.document.title,
            'question_count': len(quiz_result.get('quiz_data', [])),
            'difficulty': difficulty
        })

    except Exception as e:
        logger.error(f"生成项目测验失败: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
