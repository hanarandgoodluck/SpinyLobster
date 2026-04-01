from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import json

from .models import TestCase, KnowledgeBase, Project
from ..knowledge.service import get_knowledgeService_instance

# 初始化服务
from django.conf import settings
from apps.llm import LLMServiceFactory
# from ..knowledge.vector_store import MilvusVectorStore
# from ..knowledge.embedding import BGEM3Embedder
from apps.utils.logger_manager import get_logger
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import os
from datetime import datetime
from apps.knowledge.milvus_helper import process_singel_file

import hashlib



logger = get_logger(__name__)

# 获取LLM配置
llm_config = getattr(settings, 'LLM_PROVIDERS', {})

# 获取默认提供商
DEFAULT_PROVIDER = llm_config.get('default_provider', 'deepseek')

# 创建提供商字典，排除'default_provider'键
PROVIDERS = {k: v for k, v in llm_config.items() if k != 'default_provider'}

# 获取默认提供商的配置
DEFAULT_LLM_CONFIG = PROVIDERS.get(DEFAULT_PROVIDER, {})

# 创建 LLM 服务实例
try:
    llm_service = LLMServiceFactory.create(
        provider=DEFAULT_PROVIDER,
        **DEFAULT_LLM_CONFIG
    )
except ValueError as e:
    logger.warning(f"无法创建 LLM 服务：{e}")
    llm_service = None

knowledge_service = None
try:
    knowledge_service = get_knowledgeService_instance()
except LookupError as e:
    logger.warning(f"无法创建 Knowledge 服务：{e}")
    knowledge_service = None

# test_case_generator = TestCaseGeneratorAgent(llm_service, knowledge_service)
#test_case_reviewer = TestCaseReviewerAgent(llm_service, knowledge_service)

# @login_required 先屏蔽登录
def index(request):
    """页面 - 首页视图"""
    # 优化数据库查询，使用缓存和更高效的查询方式
    # 使用 aggregate 比 count() 更快，避免 SELECT COUNT(*)
    from django.db.models import Count, Q
    
    # 一次性获取所有统计数据，减少数据库查询次数
    stats = TestCase.objects.aggregate(
        total=Count('id'),
        pending=Count('id', filter=Q(status='pending')),
        approved=Count('id', filter=Q(status='approved')),
        rejected=Count('id', filter=Q(status='rejected'))
    )
    
    # 获取最近的测试用例 (使用 select_related 优化关联查询)
    recent_test_cases = TestCase.objects.select_related('project').order_by('-created_at')[:10]
    
    context = {
        'total_test_cases': stats['total'] or 0,
        'pending_count': stats['pending'] or 0,
        'approved_count': stats['approved'] or 0,
        'rejected_count': stats['rejected'] or 0,
        'recent_test_cases': recent_test_cases,
    }
    
    return render(request, 'index.html', context)


def format_test_cases_to_html(test_cases):
    """将测试用例格式化为HTML"""
    html = ""
    for i, test_case in enumerate(test_cases):
        html += f"<div class='test-case mb-4'>"
        html += f"<h4>测试用例 #{i+1}: {test_case.get('description', '无描述')}</h4>"
        
        # 测试步骤
        html += "<div class='test-steps mb-3'>"
        html += "<h5>测试步骤:</h5>"
        html += "<ol>"
        for step in test_case.get('test_steps', []):
            html += f"<li>{step}</li>"
        html += "</ol>"
        html += "</div>"
        
        # 预期结果
        html += "<div class='expected-results'>"
        html += "<h5>预期结果:</h5>"
        html += "<ol>"
        for result in test_case.get('expected_results', []):
            html += f"<li>{result}</li>"
        html += "</ol>"
        html += "</div>"
        
        html += "</div>"
    
    return html


# @login_required 先屏蔽登录
def knowledge_view(request):
    """知识库管理页面"""
    return render(request, 'knowledge.html')

# @login_required 先屏蔽登录
@require_http_methods(["POST"])
def add_knowledge(request):
    """添加知识条目"""
    try:
        data = json.loads(request.body)
        title = data.get('title')
        content = data.get('content')
        
        if not title or not content:
            return JsonResponse({
                'success': False,
                'message': '标题和内容不能为空'
            })
        
        # 添加到知识库
        knowledge_id = knowledge_service.add_knowledge(title, content)
        
        return JsonResponse({
            'success': True,
            'message': '知识条目添加成功',
            'knowledge_id': knowledge_id
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })

# @login_required 先屏蔽登录
def knowledge_list(request):
    """获取知识库列表"""
    try:
        knowledge_items = KnowledgeBase.objects.all().order_by('-created_at')
        
        items = []
        for item in knowledge_items:
            items.append({
                'id': item.id,
                'title': item.title,
                'content': item.content,
                'created_at': item.created_at.isoformat()
            })
        
        return JsonResponse({
            'success': True,
            'knowledge_items': items
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })

# @login_required 先屏蔽登录
@require_http_methods(["POST"])
def search_knowledge(request):
    """搜索知识库"""
    try:
        data = json.loads(request.body)
        query = data.get('query')
        
        if not query:
            return JsonResponse({
                'success': False,
                'message': '搜索关键词不能为空'
            })
        
        # 搜索知识库
        query_embedding = knowledge_service.embedder.get_embeddings(query)[0]
        logger.info(f"查询文本: '{query}', 向量维度: {len(query_embedding)}, 前5个维度: {query_embedding[:5]}")
        results = knowledge_service.search_knowledge(query)
        
        return JsonResponse({
            'success': True,
            'results': results
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })

@csrf_exempt
def upload_single_file(request):
    """处理文件上传的视图函数"""
    if request.method == 'GET':
        return render(request, 'upload.html')
    elif request.method == 'POST':
        if 'single_file' in request.FILES:  # 修改这里匹配前端的 name 属性
            uploaded_file = request.FILES['single_file']  # 修改这里匹配前端的 name 属性
            file_path = os.path.join(settings.MEDIA_ROOT, uploaded_file.name)
            
            # 先检查文件是否存在
            if os.path.exists(file_path):
                return JsonResponse({
                    'success': False,
                    'error': '文件已存在'
                })
                
            try:
                # 1. 接收文件
                logger.info(f"Uploaded file: {uploaded_file}")
                if not uploaded_file:
                    return JsonResponse({'success': False, 'error': '未接收到文件'})
                
                file_categories = {
                    "CSV": [".csv"],
                    "E-mail": [".eml", ".msg", ".p7s"],
                    "EPUB": [".epub"],
                    "Excel": [".xls", ".xlsx"],
                    "HTML": [".html"],
                    "Image": [".bmp", ".heic", ".jpeg", ".png", ".tiff"],
                    "Markdown": [".md"],
                    "Org Mode": [".org"],
                    "Open Office": [".odt"],
                    "PDF": [".pdf"],
                    "Plain text": [".txt"],
                    "PowerPoint": [".ppt", ".pptx"],
                    "reStructured Text": [".rst"],
                    "Rich Text": [".rtf"],
                    "TSV": [".tsv"],
                    "Word": [".doc", ".docx"],
                    "XML": [".xml"]
                }
                file_type = os.path.splitext(uploaded_file.name)[1]
                logger.info(f"上传文件类型: {file_type}")
                logger.info(f"上传文件名: {uploaded_file.name}")
                
                if not file_type:
                    logger.error("文件没有扩展名")
                    return JsonResponse({'success': False, 'error': '文件必须包含扩展名'})
                
                # 获取所有支持的文件扩展名
                supported_extensions = [ext.lower() for exts in file_categories.values() for ext in exts]

                if file_type not in supported_extensions:
                    return JsonResponse({'success': False, 'error': '不支持的文件类型'})
                
                # 2. 保存临时文件
                save_dir = 'uploads/'
                os.makedirs(save_dir, exist_ok=True)
                file_path = os.path.join(save_dir, f"{uploaded_file.name}")
                with open(file_path, 'wb+') as f:
                    for chunk in uploaded_file.chunks():
                        f.write(chunk)
                logger.info(f"临时文件保存成功, 文件保存路径: {file_path}")

                # 3. 处理文件
                chunks = process_singel_file(file_path)  # 获取原始数据和文本
                if not chunks:
                    return JsonResponse({'success': False, 'error': '文件中无有效内容'})

                # 提取所有chunk.text并记录日志
                if isinstance(chunks, list):
                    # 直接从chunks中提取text属性
                    text_contents = []
                    for i, chunk in enumerate(chunks):
                        if hasattr(chunk, 'text'):
                            text_contents.append(str(chunk.text))
                        else:
                            text_contents.append(str(chunk))
                
                    logger.info(f"共提取了 {len(text_contents)} 个文本内容")
                else:
                    # 单一文本块的情况
                    if hasattr(chunks, 'text'):
                        text_contents = [str(chunks.text)]
                    else:
                        text_contents = [str(chunks)]
                    logger.info(f"提取了单个文本内容: {text_contents[0][:100]}...")

                # 直接生成所有文本内容的向量
                logger.info("开始生成向量")
                start_time = datetime.now()

                try:
                    # 直接为所有文本内容生成向量
                    all_embeddings = knowledge_service.embedder.get_embeddings(texts=text_contents, show_progress_bar=False)
                    logger.info(f"成功生成 {len(all_embeddings)} 个向量")
                    
                    # 确保embeddings是列表格式
                    embeddings_list = []
                    for emb in all_embeddings:
                        if hasattr(emb, 'tolist'):
                            emb = emb.tolist()
                        embeddings_list.append(emb)
                    
                    # 准备插入数据
                    data_to_insert = []
                    for i in range(len(text_contents)):
                        item = {
                            "embedding": embeddings_list[i],  # 单个embedding向量
                            "content": text_contents[i],      # 文本内容
                            "metadata": '{}',                 # 元数据
                            "source": file_path,              # 来源
                            "doc_type": file_type,            # 文档类型
                            "chunk_id": f"{hashlib.md5(os.path.basename(file_path).encode()).hexdigest()[:10]}_{i:04d}",  # 块ID
                            "upload_time": datetime.now().isoformat()  # 上传时间
                        }
                        data_to_insert.append(item)
                    
                    # 插入数据到Milvus
                    logger.info(f"开始往milvus中插入 {len(data_to_insert)} 条数据")
                    knowledge_service.vector_store.add_data(data_to_insert)
                    logger.info("数据插入完成")
                    
                    total_time = (datetime.now() - start_time).total_seconds()
                    logger.info(f"向量生成和插入完成，总耗时: {total_time:.2f} 秒")
                    
                    return JsonResponse({
                        'success': True, 
                        'count': len(text_contents),
                        'message': f'成功导入文件到知识库'
                    })
                    
                except Exception as e:
                    logger.error(f"生成或插入向量时出错: {str(e)}", exc_info=True)
                    return JsonResponse({
                        'success': False, 
                        'error': str(e)
                    })
                
            except Exception as e:
                logger.error(f"处理上传文件时出错: {str(e)}", exc_info=True)
                return JsonResponse({
                    'success': False, 
                    'error': str(e)
                })
            finally:
                # 清理临时文件
                if os.path.exists(file_path):
                    pass
                    # os.remove(file_path)
        else:
            return JsonResponse({
                'success': False,
                'error': '未接收到文件'
            })
    
    return JsonResponse({
        'success': False,
        'error': '不支持的请求方法'
    })


# ============== 项目管理相关视图 ==============

def project_list_view(request):
    """项目管理页面"""
    return render(request, 'project_list.html')

@require_http_methods(["GET", "POST"])
def project_list_create(request):
    """
    获取项目列表或创建新项目
    GET: 获取所有项目
    POST: 创建新项目
    """
    try:
        if request.method == "GET":
            # 获取所有项目，按创建时间倒序
            # 使用 select_related 和 prefetch_related 优化查询
            projects = Project.objects.all().order_by('-created_at')
            
            project_list = []
            for project in projects:
                project_list.append({
                    'id': project.id,
                    'name': project.name,
                    'version': project.version,
                    'description': project.description,
                    'created_at': project.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'updated_at': project.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'test_case_count': project.test_cases.count()
                })
            
            return JsonResponse({
                'success': True,
                'projects': project_list
            })
        
        elif request.method == "POST":
            data = json.loads(request.body)
            name = data.get('name')
            version = data.get('version')
            description = data.get('description', '')
            
            logger.info(f"创建项目 - name: {name}, version: {version}, description: {description}")
            
            if not name or not version:
                return JsonResponse({
                    'success': False,
                    'message': '项目名称和版本不能为空'
                }, status=400)
            
            # 检查是否已存在同名同版本的项目
            existing = Project.objects.filter(name=name, version=version).first()
            logger.info(f"检查是否存在：name={name}, version={version}, existing={existing}")
            if existing:
                return JsonResponse({
                    'success': False,
                    'message': f'项目名称"{name}"和版本"{version}"的组合已存在。请修改项目名称或版本号。'
                }, status=400)
            
            # 创建新项目
            project = Project.objects.create(
                name=name,
                version=version,
                description=description
            )
            
            return JsonResponse({
                'success': True,
                'message': '项目创建成功',
                'project': {
                    'id': project.id,
                    'name': project.name,
                    'version': project.version,
                    'description': project.description
                }
            })
    
    except Exception as e:
        logger.error(f"项目管理出错：{str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'服务器错误：{str(e)}'
        }, status=500)


@require_http_methods(["GET", "PUT", "DELETE"])
def project_detail(request, project_id):
    """
    获取项目详情、更新或删除项目
    """
    try:
        project = Project.objects.filter(id=project_id).first()
        
        if not project:
            return JsonResponse({
                'success': False,
                'message': '项目不存在'
            }, status=404)
        
        if request.method == "GET":
            # 获取项目详情
            return JsonResponse({
                'success': True,
                'project': {
                    'id': project.id,
                    'name': project.name,
                    'version': project.version,
                    'description': project.description,
                    'created_at': project.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'updated_at': project.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'test_case_count': project.test_cases.count()
                }
            })
        
        elif request.method == "PUT":
            # 更新项目
            data = json.loads(request.body)
            
            if 'name' in data:
                project.name = data['name']
            if 'version' in data:
                project.version = data['version']
            if 'description' in data:
                project.description = data['description']
            
            project.save()
            
            return JsonResponse({
                'success': True,
                'message': '项目更新成功',
                'project': {
                    'id': project.id,
                    'name': project.name,
                    'version': project.version,
                    'description': project.description
                }
            })
        
        elif request.method == "DELETE":
            # 删除项目
            project_name = project.name
            project.delete()
            
            return JsonResponse({
                'success': True,
                'message': f'项目 "{project_name}" 已删除'
            })
    
    except Exception as e:
        logger.error(f"项目操作出错：{str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'服务器错误：{str(e)}'
        }, status=500)


def project_detail_view(request, project_id):
    """
    项目详情页面 - 展示项目信息和功能菜单
    """
    try:
        project = Project.objects.get(id=project_id)
        
        # 获取该项目下的测试用例统计
        total_test_cases = TestCase.objects.filter(project=project).count()
        pending_count = TestCase.objects.filter(project=project, status='pending').count()
        approved_count = TestCase.objects.filter(project=project, status='approved').count()
        rejected_count = TestCase.objects.filter(project=project, status='rejected').count()
        
        # 获取最近的测试用例（最多 10 条）
        recent_test_cases = TestCase.objects.filter(project=project).order_by('-created_at')[:10]
        
        context = {
            'project': project,
            'total_test_cases': total_test_cases,
            'pending_count': pending_count,
            'approved_count': approved_count,
            'rejected_count': rejected_count,
            'recent_test_cases': recent_test_cases,
        }
        
        return render(request, 'project_detail.html', context)
    
    except Project.DoesNotExist:
        return render(request, 'error.html', {'message': '项目不存在'}, status=404)
    except Exception as e:
        logger.error(f"加载项目详情页出错：{str(e)}", exc_info=True)
        return render(request, 'error.html', {'message': str(e)}, status=500)

