import logging
import json
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods, require_GET
from django.core.paginator import Paginator
from django.db.models import Q

from .models import RequirementDoc, RequirementNode
from apps.core.models import Project
from .services.document_parser import DocumentParserFactory
from .services.document_structured_parser import DocumentStructuredParserFactory

logger = logging.getLogger(__name__)


@require_GET
def index(request):
    """需求导入页面"""
    project_id = request.GET.get('project_id')
    return render_index_page(request, project_id)


def render_index_page(request, project_id=None):
    from django.template.response import TemplateResponse
    return TemplateResponse(request, 'ai_requirement_analysis/index.html', {
        'project_id': project_id
    })


@require_GET
def get_tree_data(request):
    """获取树形数据"""
    try:
        project_id = request.GET.get('project_id')
        
        if not project_id:
            return JsonResponse({
                'success': False,
                'message': '缺少项目ID'
            }, status=400)
        
        # 获取该项目的所有节点
        nodes = RequirementNode.objects.filter(
            project_id=project_id
        ).order_by('order', '-created_at')
        
        # 构建树形结构
        tree = build_tree(nodes)
        
        return JsonResponse({
            'success': True,
            'tree': tree
        })
    except Exception as e:
        logger.error(f"获取树数据失败: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'获取树数据失败: {str(e)}'
        }, status=500)


def build_tree(nodes):
    """将扁平节点列表转换为树形结构"""
    node_dict = {}
    root_nodes = []
    
    # 首先将所有节点放入字典
    for node in nodes:
        node_dict[node.id] = {
            'id': node.id,
            'name': node.name,
            'node_type': node.node_type,
            'parent_id': node.parent_id,
            'content': node.content,
            'order': node.order,
            'created_at': node.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'children_count': 0,
            'children': []
        }
    
    # 然后构建父子关系
    for node in nodes:
        node_data = node_dict[node.id]
        
        if node.parent_id is None or node.parent_id not in node_dict:
            # 根节点
            root_nodes.append(node_data)
        else:
            # 子节点
            parent_data = node_dict[node.parent_id]
            parent_data['children'].append(node_data)
            parent_data['children_count'] += 1
    
    # 按排序字段排序
    root_nodes.sort(key=lambda x: x['order'])
    sort_children(root_nodes)
    
    return root_nodes


def sort_children(nodes):
    """递归排序子节点"""
    for node in nodes:
        if node['children']:
            node['children'].sort(key=lambda x: x['order'])
            sort_children(node['children'])


@require_http_methods(["POST"])
def add_node(request):
    """添加节点"""
    try:
        data = json.loads(request.body)
        project_id = data.get('project_id')
        name = data.get('name')
        node_type = data.get('node_type', 'folder')
        parent_id = data.get('parent_id')
        content = data.get('content', '')
        
        if not project_id or not name:
            return JsonResponse({
                'success': False,
                'message': '缺少必要参数'
            }, status=400)
        
        # 验证父节点是否存在（如果有）
        if parent_id:
            try:
                parent = RequirementNode.objects.get(id=parent_id)
            except RequirementNode.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': '父节点不存在'
                }, status=400)
        
        # 创建新节点
        max_order = RequirementNode.objects.filter(
            project_id=project_id,
            parent_id=parent_id
        ).aggregate(models.Max('order'))['order__max'] or 0
        
        node = RequirementNode.objects.create(
            project_id=project_id,
            parent_id=parent_id,
            name=name,
            node_type=node_type,
            content=content,
            order=max_order + 1
        )
        
        logger.info(f"成功添加节点: {node.id} - {name}")
        
        return JsonResponse({
            'success': True,
            'message': '添加成功',
            'node_id': node.id
        })
    except Exception as e:
        logger.error(f"添加节点失败: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'添加失败: {str(e)}'
        }, status=500)


@require_http_methods(["PUT"])
def update_node(request):
    """更新节点"""
    try:
        node_id = request.GET.get('id')
        
        if not node_id:
            return JsonResponse({
                'success': False,
                'message': '缺少节点ID'
            }, status=400)
        
        try:
            node = RequirementNode.objects.get(id=node_id)
        except RequirementNode.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': '节点不存在'
            }, status=400)
        
        data = json.loads(request.body)
        
        # 更新字段
        if 'name' in data:
            node.name = data['name']
        if 'content' in data:
            node.content = data['content']
        if 'node_type' in data:
            node.node_type = data['node_type']
        
        node.save()
        
        logger.info(f"更新节点成功: {node.id} - {node.name}")
        
        return JsonResponse({
            'success': True,
            'message': '更新成功'
        })
    except Exception as e:
        logger.error(f"更新节点失败: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'更新失败: {str(e)}'
        }, status=500)


@require_http_methods(["DELETE"])
def delete_node(request):
    """删除节点"""
    try:
        node_id = request.GET.get('id')
        
        if not node_id:
            return JsonResponse({
                'success': False,
                'message': '缺少节点ID'
            }, status=400)
        
        # 级联删除（包括子节点）
        deleted_count, _ = RequirementNode.objects.filter(id=node_id).delete()
        
        logger.info(f"删除节点 {node_id}，影响 {deleted_count} 条记录")
        
        return JsonResponse({
            'success': True,
            'message': '删除成功',
            'deleted_count': deleted_count
        })
    except Exception as e:
        logger.error(f"删除节点失败: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'删除失败: {str(e)}'
        }, status=500)


@require_http_methods(["POST"])
def upload_document(request):
    """上传并解析文档"""
    try:
        uploaded_file = request.FILES.get('file')
        project_id = request.POST.get('project_id')
        
        if not uploaded_file:
            return JsonResponse({
                'success': False,
                'message': '没有选择文件'
            }, status=400)
        
        if not project_id:
            return JsonResponse({
                'success': False,
                'message': '缺少项目ID'
            }, status=400)
        
        # 保存原始文档
        import os
        import uuid
        from django.conf import settings
        
        upload_dir = os.path.join(settings.MEDIA_ROOT, 'requirements')
        os.makedirs(upload_dir, exist_ok=True)
        
        file_ext = uploaded_file.name.split('.')[-1].lower()
        filename = f"{uuid.uuid4().hex}.{file_ext}"
        file_path = os.path.join(upload_dir, filename)
        
        # 写入文件
        with open(file_path, 'wb+') as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)
        
        # 验证文件是否成功保存
        if not os.path.exists(file_path):
            logger.error(f"文件保存失败: {file_path}")
            return JsonResponse({
                'success': False,
                'message': '文件保存失败'
            }, status=500)
        
        file_size_saved = os.path.getsize(file_path)
        logger.info(f"文件保存成功: {file_path}, 大小: {file_size_saved} bytes")
        
        if file_size_saved == 0:
            logger.error(f"保存的文件大小为 0: {file_path}")
            return JsonResponse({
                'success': False,
                'message': '保存的文件为空'
            }, status=500)
        
        # 创建文档记录
        doc = RequirementDoc.objects.create(
            project_id=project_id,
            filename=uploaded_file.name,
            file_path=file_path,
            file_type=file_ext,
            file_size=file_size_saved
        )
        
        # 使用结构化解析器解析文档
        try:
            structured_data = DocumentStructuredParserFactory.parse_file(file_path)
        except Exception as e:
            logger.warning(f"结构化解析失败，回退到普通解析: {str(e)}")
            # 回退到普通解析
            parser = DocumentParserFactory.get_parser(file_ext)
            if not parser:
                return JsonResponse({
                    'success': False,
                    'message': f'不支持的文件类型: {file_ext}'
                }, status=400)
            
            content = parser.parse(file_path)
            if not content:
                return JsonResponse({
                    'success': False,
                    'message': '文档内容为空或解析失败'
                }, status=400)
            
            # 根据文档标题创建根目录
            title = uploaded_file.name.rsplit('.', 1)[0]
            
            root_folder = RequirementNode.objects.create(
                project_id=project_id,
                parent_id=None,
                name=title,
                node_type='folder',
                order=RequirementNode.objects.filter(
                    project_id=project_id,
                    parent_id=None
                ).count() + 1
            )
            
            if content.strip():
                RequirementNode.objects.create(
                    project_id=project_id,
                    parent_id=root_folder.id,
                    name='需求内容',
                    node_type='requirement',
                    content=content,
                    source_doc=doc,
                    order=1
                )
            
            logger.info(f"文档上传并解析成功: {uploaded_file.name}")
            return JsonResponse({
                'success': True,
                'message': f'文档上传成功，已创建 "{title}" 目录',
                'doc_id': doc.id,
                'root_folder_id': root_folder.id
            })
        
        # 使用结构化数据创建树形菜单
        title = structured_data.get('title', uploaded_file.name.rsplit('.', 1)[0])
        sections = structured_data.get('sections', [])
        
        # 创建根文件夹（文件名称）
        root_folder = RequirementNode.objects.create(
            project_id=project_id,
            parent_id=None,
            name=title,
            node_type='folder',
            order=RequirementNode.objects.filter(
                project_id=project_id,
                parent_id=None
            ).count() + 1
        )
        
        # 创建1级菜单（文档标题）
        for idx, section in enumerate(sections, 1):
            level1_folder = RequirementNode.objects.create(
                project_id=project_id,
                parent_id=root_folder.id,
                name=section.get('title', f'章节{idx}'),
                node_type='folder',
                order=idx
            )
            
            # 处理1级标题的内容
            if section.get('content'):
                RequirementNode.objects.create(
                    project_id=project_id,
                    parent_id=level1_folder.id,
                    name='内容',
                    node_type='requirement',
                    content=section.get('content'),
                    source_doc=doc,
                    order=0
                )
            
            # 创建2级菜单（子标题）
            subsections = section.get('subsections', [])
            for sub_idx, subsection in enumerate(subsections, 1):
                level2_folder = RequirementNode.objects.create(
                    project_id=project_id,
                    parent_id=level1_folder.id,
                    name=subsection.get('title', f'子章节{sub_idx}'),
                    node_type='folder',
                    order=sub_idx
                )
                
                # 处理2级标题的内容
                if subsection.get('content'):
                    RequirementNode.objects.create(
                        project_id=project_id,
                        parent_id=level2_folder.id,
                        name='内容',
                        node_type='requirement',
                        content=subsection.get('content'),
                        source_doc=doc,
                        order=0
                    )
        
        logger.info(f"文档上传并解析成功: {uploaded_file.name}，创建 {len(sections)} 个1级章节")
        
        return JsonResponse({
            'success': True,
            'message': f'文档上传成功，已创建 "{title}" 目录',
            'doc_id': doc.id,
            'root_folder_id': root_folder.id
        })
    except Exception as e:
        logger.error(f"上传文档失败: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'上传失败: {str(e)}'
        }, status=500)


# 导入 models 用于聚合查询
from django.db import models
