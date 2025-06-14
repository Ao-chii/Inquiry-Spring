import logging
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
            projects = Project.objects.filter(is_active=True).order_by('-created_at')
            project_list = []

            for project in projects:
                # 获取项目文档信息 - 适应前端期望格式
                documents = []
                for proj_doc in project.documents.all():
                    doc = proj_doc.document
                    if doc.is_processed:
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
            
            # 返回前端期望的格式
            return Response({
                'message': '项目创建成功',
                'project': {
                    'id': project.id,
                    'name': project.name,
                    'description': project.description,
                    'createTime': project.created_at.strftime('%Y-%m-%d'),  # 前端期望的时间格式
                    'documents': []  # 新项目没有文档
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


@csrf_exempt
@api_view(['GET', 'POST', 'OPTIONS'])
def project_upload_document(request, project_id):
    """为项目上传文档 - 支持大整数ID的测试版本"""

    # 强制输出调试信息
    print(f"=== 函数被调用 ===")
    print(f"Method: {request.method}")
    print(f"Project ID: {project_id} (type: {type(project_id)})")
    print(f"Path: {request.path}")
    print(f"User: {request.user}")
    print(f"Headers: {dict(request.headers)}")
    print(f"=== 调试信息结束 ===")

    # 转换project_id为整数（如果是字符串）
    try:
        project_id_int = int(project_id)
    except (ValueError, TypeError):
        return Response({
            'error': f'无效的项目ID: {project_id}',
            'project_id': project_id
        }, status=400)

    # 立即返回成功响应，不做任何复杂处理
    return Response({
        'message': '测试成功 - 函数被正确调用',
        'method': request.method,
        'project_id': project_id,
        'project_id_int': project_id_int,
        'path': request.path,
        'timestamp': str(timezone.now()),
        'success': True
    }, status=200)




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
