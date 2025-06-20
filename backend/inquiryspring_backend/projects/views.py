import logging
import os
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .models import Project, ProjectDocument, ProjectStats

logger = logging.getLogger(__name__)


@api_view(['GET', 'POST'])
def project_list(request):
    """项目列表和创建 - 完全适应前端需求"""
    """项目列表"""
    if request.method == 'GET':
        try:
            username = request.GET.get('username', '').strip()
            if username:
                from django.contrib.auth.models import User
                try:
                    user = User.objects.get(username=username)
                except User.DoesNotExist:
                    return Response([], status=status.HTTP_200_OK)
                projects = Project.objects.filter(is_active=True, user=user).order_by('-created_at')
            else:
                projects = Project.objects.filter(is_active=True).order_by('-created_at')
            project_list = []

            for project in projects:
                # 获取项目文档信息 - 适应前端期望格式
                documents = []
                for proj_doc in project.documents.all():
                    doc = proj_doc.document
                    if hasattr(doc, 'is_processed') and doc.is_processed:
                        documents.append({
                            'name': doc.title,
                            'size': f"{doc.file_size // 1024}KB" if doc.file_size else "未知",
                            'uploadTime': doc.uploaded_at.strftime('%Y-%m-%d %H:%M') if doc.uploaded_at else "未知"
                        })

                # 构建前端期望的项目数据格式
                project_data = {
                    'id': project.id,
                    'name': project.name,
                    'description': project.description,
                    'createTime': project.created_at.strftime('%Y-%m-%d'),  # 前端期望的时间格式
                    'documents': documents  # 前端期望的文档列表
                }

                project_list.append(project_data)

            # 直接返回项目数组，匹配前端期望
            return Response(project_list)
            
        except Exception as e:
            logger.error(f"获取项目列表失败: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    elif request.method == 'POST':
        try:
            data = request.data
            name = data.get('name', '').strip()
            description = data.get('description', '').strip()
            username = data.get('username', '').strip()
            if not name:
                return Response({'error': '项目名称不能为空'}, status=status.HTTP_400_BAD_REQUEST)
            if not username:
                return Response({'error': '用户名不能为空'}, status=status.HTTP_400_BAD_REQUEST)
            # 根据用户名查找用户
            from django.contrib.auth.models import User
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                return Response({'error': '用户不存在'}, status=status.HTTP_404_NOT_FOUND)
            # 创建项目并关联用户
            project = Project.objects.create(
                name=name,
                description=description,
                user=user
            )
            ProjectStats.objects.create(project=project)
            # 返回前端所需的项目详细数据
            return Response({
                'message': '项目创建成功',
                'project': {
                    'id': project.id,
                    'name': project.name,
                    'description': project.description,
                    'createTime': project.created_at.strftime('%Y-%m-%d'),
                    'documents': []
                },
                'success': True
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
            # 校验 username 参数，只有项目 owner 才能访问
            username = request.GET.get('username', '').strip()
            if username:
                from django.contrib.auth.models import User
                try:
                    user = User.objects.get(username=username)
                except User.DoesNotExist:
                    return Response({'error': '用户不存在'}, status=status.HTTP_404_NOT_FOUND)
                if project.user != user:
                    return Response({'error': '无权访问该项目'}, status=status.HTTP_403_FORBIDDEN)
            # 先查 ProjectDocument 表获取文档索引，再查 Document 表
            from ..documents.models import Document
            project_docs = ProjectDocument.objects.filter(project=project)
            documents = []
            for proj_doc in project_docs:
                try:
                    doc = Document.objects.get(id=proj_doc.document_id)
                    documents.append({
                        'id': doc.id,
                        'title': doc.title,
                        'filename': doc.filename if hasattr(doc, 'filename') else '',
                        'size': f"{doc.file_size // 1024}KB" if getattr(doc, 'file_size', None) else "未知",
                        'uploadTime': doc.uploaded_at.strftime('%Y-%m-%d %H:%M') if getattr(doc, 'uploaded_at', None) else "未知",
                        'is_primary': proj_doc.is_primary,
                        'added_at': proj_doc.added_at.isoformat()
                    })
                except Document.DoesNotExist:
                    continue
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
def project_add_document(request, project_id):
    """向项目添加文档，支持直接上传文件或通过文档ID添加"""
    from ..documents.models import Document
    from ..documents.document_processor import document_processor
    from ..ai_services.rag_engine import RAGEngine
    from django.conf import settings
    import os
    import re
    project = get_object_or_404(Project, id=project_id, is_active=True)
    try:
        # 如果有文件上传，走上传逻辑
        if 'file' in request.FILES:
            file = request.FILES['file']
            if file.name == '':
                return Response({'error': '没有选择文件'}, status=status.HTTP_400_BAD_REQUEST)
            # 文件名安全处理
            filename = re.sub(r'[^\w\s\-\.]', '', file.name).strip()
            filename = re.sub(r'[\-\s]+', '_', filename)
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
                title=filename,
                file_type=validation['file_type'],
                file_size=validation['file_size'],
                processing_status='processing'
            )
            # 移动文件到最终位置
            final_dir = os.path.join(settings.MEDIA_ROOT, 'documents', str(document.id))
            os.makedirs(final_dir, exist_ok=True)
            final_path = os.path.join(final_dir, filename)
            os.rename(file_path, final_path)
            document.file.name = f'documents/{document.id}/{filename}'
            document.save()
            # 提取文档内容
            extraction_result = document_processor.extract_text(final_path, filename)
            if extraction_result['success']:
                document.content = extraction_result['content']
                metadata = extraction_result['metadata'] or {}
                metadata['original_filename'] = file.name
                document.metadata = metadata
                document.is_processed = True
                document.processing_status = 'completed'
                document.processed_at = timezone.now()
                document.save()
                # RAG处理
                try:
                    from ..ai_services import process_document_for_rag
                    rag_processing_result = process_document_for_rag(document.id, force_reprocess=True)
                except Exception as e:
                    rag_processing_result = False
                # 建立项目与文档的关联
                ProjectDocument.objects.create(
                    project=project,
                    document=document,
                    is_primary=False
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
                url = document.file.url if hasattr(document.file, 'url') else ''
                return Response({
                    'message': '文档上传并关联成功',
                    'document_id': document.id,
                    'filename': file.name,
                    'url': url
                })
            else:
                document.processing_status = 'failed'
                document.error_message = extraction_result['error']
                document.save()
                return Response({'error': f'文档处理失败: {extraction_result["error"]}'}, status=500)
        # 否则走原有文档ID添加逻辑
        data = request.data
        document_id = data.get('document_id')
        is_primary = data.get('is_primary', False)
        if not document_id:
            return Response({'error': '缺少文档ID'}, status=status.HTTP_400_BAD_REQUEST)
        document = get_object_or_404(Document, id=document_id)
        if ProjectDocument.objects.filter(project=project, document=document).exists():
            return Response({'error': '文档已在项目中'}, status=status.HTTP_400_BAD_REQUEST)
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


@csrf_exempt
@api_view(['POST'])
def project_upload_document(request, project_id):
    """为项目上传文档并存储到数据库，保存文件并建立项目-文档关联，接口与el-upload兼容，处理逻辑与SummarizeView.post一致"""
    from ..documents.models import Document
    from ..documents.document_processor import document_processor
    from ..ai_services.rag_engine import RAGEngine
    from django.conf import settings
    import os
    import re
    project = get_object_or_404(Project, id=project_id, is_active=True)
    try:
        if 'file' not in request.FILES:
            return Response({'error': '没有选择文件'}, status=status.HTTP_400_BAD_REQUEST)
        file = request.FILES['file']
        if file.name == '':
            return Response({'error': '没有选择文件'}, status=status.HTTP_400_BAD_REQUEST)
        # 文件名安全处理
        filename = re.sub(r'[^\w\s\-\.]', '', file.name).strip()
        filename = re.sub(r'[\-\s]+', '_', filename)
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
            title=filename,
            file_type=validation['file_type'],
            file_size=validation['file_size'],
            processing_status='processing'
        )
        # 移动文件到最终位置
        final_dir = os.path.join(settings.MEDIA_ROOT, 'documents', str(document.id))
        os.makedirs(final_dir, exist_ok=True)
        final_path = os.path.join(final_dir, filename)
        os.rename(file_path, final_path)
        document.file.name = f'documents/{document.id}/{filename}'
        document.save()
        # 提取文档内容
        extraction_result = document_processor.extract_text(final_path, filename)
        if extraction_result['success']:
            document.content = extraction_result['content']
            metadata = extraction_result['metadata'] or {}
            metadata['original_filename'] = file.name
            document.metadata = metadata
            document.is_processed = True
            document.processing_status = 'completed'
            document.processed_at = timezone.now()
            document.save()
            # RAG处理
            try:
                from ..ai_services import process_document_for_rag
                rag_processing_result = process_document_for_rag(document.id, force_reprocess=True)
            except Exception as e:
                rag_processing_result = False
            # 建立项目与文档的关联
            ProjectDocument.objects.create(
                project=project,
                document=document,
                is_primary=False
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
            url = document.file.url if hasattr(document.file, 'url') else ''
            return Response({
                'message': '文档上传并关联成功',
                'document_id': document.id,
                'filename': file.name,
                'url': url
            })
        else:
            document.processing_status = 'failed'
            document.error_message = extraction_result['error']
            document.save()
            return Response({'error': f'文档处理失败: {extraction_result["error"]}'}, status=500)
    except Exception as e:
        logger.error(f"项目上传文档失败: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
def simple_test_view(request):
    """最简单的测试视图 - 绕过所有DRF限制"""
    print(f"=== 简单测试视图被调用 ===")
    print(f"Method: {request.method}")
    print(f"Path: {request.path}")
    print(f"User: {request.user}")
    print(f"Headers: {dict(request.headers)}")

    from django.http import JsonResponse
    return JsonResponse({
        'message': '简单测试视图工作正常',
        'method': request.method,
        'path': request.path,
        'user': str(request.user),
        'timestamp': str(timezone.now())
    })

@api_view(['GET', 'POST', 'OPTIONS'])
def test_route(request):
    """测试路由是否工作"""
    print(f"=== 测试路由被调用 ===")
    print(f"Method: {request.method}")
    print(f"Path: {request.path}")
    print(f"User: {request.user}")

    return Response({
        'message': '测试路由工作正常',
        'method': request.method,
        'path': request.path,
        'timestamp': str(timezone.now())
    }, status=200)


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


@api_view(['GET', 'POST'])
def test_project_upload(request, project_id):
    """测试项目上传路由"""
    logger.info(f"测试项目上传路由: project_id={project_id}, method={request.method}")
    logger.info(f"请求路径: {request.path}")
    logger.info(f"请求用户: {request.user}")

    return Response({
        'message': '路由测试成功',
        'project_id': project_id,
        'method': request.method,
        'path': request.path,
        'user': str(request.user),
        'files': list(request.FILES.keys()) if request.FILES else []
    })


@api_view(['POST'])
def delete_project(request, project_id):
    """级联删除项目及其所有相关文档信息"""
    try:
        project = get_object_or_404(Project, id=project_id, is_active=True)
        # 级联删除所有项目-文档关联
        project_docs = ProjectDocument.objects.filter(project=project)
        doc_ids = [pd.document.id for pd in project_docs]
        # 删除项目-文档关联
        project_docs.delete()
        # 删除文档（如有需要，可只删除未被其他项目引用的文档）
        from ..documents.models import Document
        for doc_id in doc_ids:
            # 检查该文档是否还被其他项目引用
            if not ProjectDocument.objects.filter(document_id=doc_id).exists():
                try:
                    doc = Document.objects.get(id=doc_id)
                    # 删除文件
                    if doc.file and hasattr(doc.file, 'path') and os.path.exists(doc.file.path):
                        os.remove(doc.file.path)
                    doc.delete()
                except Exception:
                    pass
        # 删除项目统计
        ProjectStats.objects.filter(project=project).delete()
        # 删除项目本身
        project.delete()
        return Response({'success': True, 'message': '项目及相关文档已删除'})
    except Exception as e:
        logger.error(f"级联删除项目失败: {e}")
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def delete_document(request, project_id):
    """级联删除项目下指定文档及其所有相关信息"""
    try:
        filename = request.data.get('filename')
        if not filename:
            return Response({'success': False, 'error': '缺少文档名称'}, status=status.HTTP_400_BAD_REQUEST)
        project = get_object_or_404(Project, id=project_id, is_active=True)
        # 找到对应的文档对象
        proj_doc = ProjectDocument.objects.filter(project=project, document__title=filename).first()
        if not proj_doc:
            return Response({'success': False, 'error': '未找到该文档'}, status=status.HTTP_404_NOT_FOUND)
        doc = proj_doc.document
        # 删除项目-文档关联
        proj_doc.delete()
        # 如果该文档未被其他项目引用，则删除文档及其文件
        if not ProjectDocument.objects.filter(document=doc).exists():
            try:
                if doc.file and hasattr(doc.file, 'path') and os.path.exists(doc.file.path):
                    os.remove(doc.file.path)
                doc.delete()
            except Exception:
                pass
        # 更新项目统计
        try:
            stats = project.stats
            stats.total_documents = project.documents.count()
            stats.save()
        except ProjectStats.DoesNotExist:
            pass
        return Response({'success': True, 'message': '文档及相关信息已删除'})
    except Exception as e:
        logger.error(f"级联删除文档失败: {e}")
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
