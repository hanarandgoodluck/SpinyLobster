from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q
from apps.core.models import TestCaseLibrary, Project, TestCaseModule
import json


def case_library_page(request):
    """用例库页面"""
    return render(request, 'case_library/test.html')


@require_http_methods(["GET"])
def case_library_list(request):
    """获取用例库列表"""
    try:
        # 获取查询参数
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))
        search = request.GET.get('search', '')
        module = request.GET.get('module', '')
        priority = request.GET.get('priority', '')
        case_type = request.GET.get('type', '')
        project_id = request.GET.get('project_id', '')
        
        # 基础查询集
        queryset = TestCaseLibrary.objects.all()
        
        # 搜索过滤
        if search:
            queryset = queryset.filter(
                Q(case_number__icontains=search) |
                Q(title__icontains=search) |
                Q(tags__icontains=search)
            )
        
        # 模块过滤
        if module:
            queryset = queryset.filter(module=module)
        
        # 优先级过滤
        if priority:
            queryset = queryset.filter(priority=priority)
        
        # 类型过滤
        if case_type:
            queryset = queryset.filter(case_type=case_type)
        
        # 项目过滤
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        
        # 分页
        paginator = Paginator(queryset.order_by('-case_number'), page_size)
        page_obj = paginator.get_page(page)
        
        # 序列化数据
        cases_data = []
        for case in page_obj:
            cases_data.append({
                'id': case.id,
                'case_number': case.case_number,
                'title': case.title,
                'module': case.module,
                'module_display': case.get_module_display(),
                'priority': case.priority,
                'priority_display': case.get_priority_display(),
                'case_type': case.case_type,
                'case_type_display': case.get_case_type_display(),
                'status': case.status,
                'status_display': case.get_status_display(),
                'maintainer': case.maintainer,
                'project_id': case.project.id if case.project else None,
                'project_name': case.project.name if case.project else None,
                'tags': case.tags,
                'created_at': case.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': case.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
            })
        
        return JsonResponse({
            'success': True,
            'data': {
                'cases': cases_data,
                'total': paginator.count,
                'page': page,
                'page_size': page_size,
                'total_pages': paginator.num_pages,
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@require_http_methods(["POST"])
def create_case(request):
    """创建用例"""
    try:
        data = json.loads(request.body)
        
        # 生成用例编号
        case_number = data.get('case_number', '')
        if not case_number:
            # 自动生成编号
            last_case = TestCaseLibrary.objects.order_by('-id').first()
            if last_case:
                # 提取最后一个用例的编号数字部分并 +1
                try:
                    last_num = int(last_case.case_number.split('-')[-1])
                    case_number = f"CASE-{last_num + 1:04d}"
                except:
                    case_number = "CASE-0001"
            else:
                case_number = "CASE-0001"
        
        # 处理测试步骤（如果是 JSON 字符串则解析）
        test_steps = data.get('test_steps', '')
        if test_steps and isinstance(test_steps, str):
            try:
                # 如果是 JSON 字符串，解析为列表
                import json as json_lib
                steps_list = json_lib.loads(test_steps)
                if isinstance(steps_list, list):
                    # 将步骤列表格式化为文本
                    test_steps = '\n'.join([
                        f"{i+1}. {step.get('step_desc', '')} -> {step.get('expected_result', '')}"
                        for i, step in enumerate(steps_list)
                    ])
            except:
                pass
        
        # 创建用例
        case = TestCaseLibrary.objects.create(
            case_number=case_number,
            title=data.get('title', ''),
            module=data.get('module', 'other'),
            priority=data.get('priority', 'p2'),
            case_type=data.get('case_type', 'functional'),
            preconditions=data.get('preconditions', ''),
            test_steps=test_steps,
            expected_results=data.get('expected_results', ''),
            status=data.get('status', 'active'),
            maintainer=data.get('maintainer', ''),
            tags=data.get('tags', ''),
            remark=data.get('remark', ''),  # 新增备注字段
            project_id=data.get('project_id') if data.get('project_id') else None
        )
        
        return JsonResponse({
            'success': True,
            'message': '用例创建成功',
            'data': {
                'id': case.id,
                'case_number': case.case_number,
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '无效的 JSON 数据'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'创建失败：{str(e)}'
        }, status=500)


@require_http_methods(["PUT"])
def update_case(request):
    """更新用例"""
    try:
        data = json.loads(request.body)
        case_id = data.get('id')
        
        if not case_id:
            return JsonResponse({
                'success': False,
                'message': '用例 ID 不能为空'
            }, status=400)
        
        case = TestCaseLibrary.objects.get(id=case_id)
        
        # 更新字段
        if 'title' in data:
            case.title = data['title']
        if 'module' in data:
            case.module = data['module']
        if 'priority' in data:
            case.priority = data['priority']
        if 'case_type' in data:
            case.case_type = data['case_type']
        if 'preconditions' in data:
            case.preconditions = data['preconditions']
        if 'test_steps' in data:
            case.test_steps = data['test_steps']
        if 'expected_results' in data:
            case.expected_results = data['expected_results']
        if 'status' in data:
            case.status = data['status']
        if 'maintainer' in data:
            case.maintainer = data['maintainer']
        if 'tags' in data:
            case.tags = data['tags']
        if 'project_id' in data:
            case.project_id = data['project_id'] if data['project_id'] else None
        
        case.save()
        
        return JsonResponse({
            'success': True,
            'message': '用例更新成功'
        })
        
    except TestCaseLibrary.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '用例不存在'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'更新失败：{str(e)}'
        }, status=500)


@require_http_methods(["DELETE"])
def delete_case(request):
    """删除用例"""
    try:
        data = json.loads(request.body)
        case_id = data.get('id')
        
        if not case_id:
            return JsonResponse({
                'success': False,
                'message': '用例 ID 不能为空'
            }, status=400)
        
        case = TestCaseLibrary.objects.get(id=case_id)
        case.delete()
        
        return JsonResponse({
            'success': True,
            'message': '用例删除成功'
        })
        
    except TestCaseLibrary.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '用例不存在'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'删除失败：{str(e)}'
        }, status=500)


def case_library_page(request):
    """用例库页面"""
    # 获取所有项目和模块选项用于筛选
    projects = Project.objects.all()
    modules = TestCaseLibrary.MODULE_CHOICES
    priorities = TestCaseLibrary.PRIORITY_CHOICES
    types = TestCaseLibrary.TYPE_CHOICES
    
    context = {
        'projects': projects,
        'modules': modules,
        'priorities': priorities,
        'types': types,
    }
    
    return render(request, 'case_library/case_library.html', context)


@require_http_methods(["GET"])
def get_modules(request):
    """获取模块列表（包含子模块）"""
    try:
        project_id = request.GET.get('project_id', '')
        
        # 基础查询集 - 查询所有一级模块
        queryset = TestCaseModule.objects.filter(parent__isnull=True)
        
        # 项目过滤
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        
        # 序列化数据（递归获取子模块）
        def serialize_module(module):
            """递归序列化模块及其子模块"""
            module_data = {
                'id': module.id,
                'name': module.name,
                'value': module.value,
                'count': TestCaseLibrary.objects.filter(module=module.value).count(),
                'children': []
            }
            
            # 获取子模块
            children = module.children.all().order_by('order', 'name')
            for child in children:
                module_data['children'].append(serialize_module(child))
            
            return module_data
        
        modules_data = []
        for module in queryset.order_by('order', 'name'):
            modules_data.append(serialize_module(module))
        
        return JsonResponse({
            'success': True,
            'data': modules_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@require_http_methods(["POST"])
def create_module(request):
    """创建模块"""
    try:
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        
        if not name:
            return JsonResponse({
                'success': False,
                'message': '模块名称不能为空'
            }, status=400)
        
        # 生成模块标识
        import re
        value = name.lower()
        value = re.sub(r'\s+', '_', value)
        
        # 检查是否已存在
        if TestCaseModule.objects.filter(value=value).exists():
            return JsonResponse({
                'success': False,
                'message': '模块已存在'
            }, status=400)
        
        # 获取项目 ID
        project_id = data.get('project_id')
        
        # 获取父模块 ID（如果是创建子模块）
        parent_id = data.get('parent_id')
        
        # 创建模块
        module = TestCaseModule.objects.create(
            name=name,
            value=value,
            project_id=project_id if project_id else None,
            parent_id=parent_id if parent_id else None
        )
        
        return JsonResponse({
            'success': True,
            'message': '模块创建成功',
            'data': {
                'id': module.id,
                'name': module.name,
                'value': module.value
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '无效的 JSON 数据'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'创建失败：{str(e)}'
        }, status=500)


@require_http_methods(["POST"])
def update_module(request, module_id):
    """更新模块"""
    try:
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        
        if not name:
            return JsonResponse({
                'success': False,
                'message': '模块名称不能为空'
            }, status=400)
        
        module = TestCaseModule.objects.get(id=module_id)
        module.name = name
        module.save()
        
        return JsonResponse({
            'success': True,
            'message': '模块更新成功',
            'data': {
                'id': module.id,
                'name': module.name,
                'value': module.value
            }
        })
        
    except TestCaseModule.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '模块不存在'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'更新失败：{str(e)}'
        }, status=500)


@require_http_methods(["POST"])
def delete_module(request, module_id):
    """删除模块"""
    try:
        module = TestCaseModule.objects.get(id=module_id)
        
        # 检查是否有子模块
        if module.children.exists():
            return JsonResponse({
                'success': False,
                'message': '请先删除子模块'
            }, status=400)
        
        # 检查是否有关联的用例
        if TestCaseLibrary.objects.filter(module=module.value).exists():
            return JsonResponse({
                'success': False,
                'message': '模块下有用例，无法删除'
            }, status=400)
        
        module_name = module.name
        module.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'模块"{module_name}"删除成功'
        })
        
    except TestCaseModule.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '模块不存在'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'删除失败：{str(e)}'
        }, status=500)
