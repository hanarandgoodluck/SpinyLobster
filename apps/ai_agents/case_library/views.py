from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
from django.core.paginator import Paginator
from django.db.models import Q
from apps.core.models import TestCaseLibrary, Project, TestCaseModule, TestCase
import json
import logging

logger = logging.getLogger(__name__)


@never_cache
def case_library_page(request):
    """用例库页面"""
    response = render(request, 'case_library/test.html')
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response


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
        
        # 项目过滤（在所有统计之前应用，确保 total_all 只对当前项目统计）
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        
        # 统计当前项目的所有用例总数（不受其他过滤条件影响）
        total_all = queryset.count()
        
        # 搜索过滤
        if search:
            queryset = queryset.filter(
                Q(case_number__icontains=search) |
                Q(title__icontains=search) |
                Q(tags__icontains=search)
            )
        
        # 模块过滤（包含子模块）
        if module:
            try:
                logger.info(f'模块过滤: module参数={module}, 类型={type(module)}')
                
                parent_mod = TestCaseModule.objects.get(value=module)
                logger.info(f'找到模块: id={parent_mod.id}, name={parent_mod.name}, value={parent_mod.value}')
                
                # 递归获取所有子模块的 value
                def get_all_module_values(mod):
                    values = [mod.value]
                    for child in mod.children.all():
                        values.extend(get_all_module_values(child))
                    return values
                
                all_values = get_all_module_values(parent_mod)
                logger.info(f'模块树所有value: {all_values}')
                queryset = queryset.filter(module__in=all_values)
            except TestCaseModule.DoesNotExist:
                logger.warning(f'模块不存在: {module}，使用直接过滤')
                queryset = queryset.filter(module=module)
            except Exception as e:
                logger.error(f'模块过滤异常: {str(e)}', exc_info=True)
                queryset = queryset.filter(module=module)
        
        # 优先级过滤
        if priority:
            queryset = queryset.filter(priority=priority)
        
        # 类型过滤
        if case_type:
            queryset = queryset.filter(case_type=case_type)
        
        # 分页
        paginator = Paginator(queryset.order_by('-case_number'), page_size)
        page_obj = paginator.get_page(page)
        
        # 序列化数据
        cases_data = []
        for case in page_obj:
            # 处理优先级显示，容错处理
            try:
                priority_display = case.get_priority_display()
            except (ValueError, AttributeError):
                # 如果获取失败，根据 priority 值手动映射
                priority_map = {
                    'p0': 'P0',
                    'p1': 'P1',
                    'p2': 'P2',
                    'p3': 'P3'
                }
                priority_display = priority_map.get(case.priority, 'P2')
            
            # 处理模块显示：如果模块值不在预定义choices中，则查询模块名称或直接显示模块值
            module_display = case.get_module_display()
            if not module_display or module_display == case.module:
                # 尝试从 TestCaseModule 表中查询模块名称
                try:
                    module_obj = TestCaseModule.objects.get(value=case.module)
                    module_display = module_obj.name
                except:
                    # 如果查询失败，直接显示模块值
                    module_display = case.module
            
            # 处理用例类型显示，容错处理
            try:
                case_type_display = case.get_case_type_display()
            except (ValueError, AttributeError):
                case_type_display = case.case_type
            
            cases_data.append({
                'id': case.id,
                'case_number': case.case_number,
                'title': case.title,
                'module': case.module,
                'module_display': module_display,
                'priority': case.priority,
                'priority_display': priority_display,
                'case_type': case.case_type,
                'case_type_display': case_type_display,
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
                'total_all': total_all,
                'page': page,
                'page_size': page_size,
                'total_pages': paginator.num_pages,
            }
        })
        
    except Exception as e:
        import traceback
        logger.error(f'用例列表接口异常: {str(e)}', exc_info=True)
        logger.error(f'异常堆栈: {traceback.format_exc()}')
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
                    # 将步骤列表格式化为文本（只保留步骤描述，不要预期结果，不添加序号）
                    test_steps = '\n'.join([
                        step.get('step_desc', '')
                        for step in steps_list
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


@require_http_methods(["GET"])
def get_case_detail(request, case_id):
    """获取用例详情"""
    try:
        case = TestCaseLibrary.objects.get(id=case_id)
        
        # 处理优先级显示
        try:
            priority_display = case.get_priority_display()
        except (ValueError, AttributeError):
            priority_map = {
                'p0': 'P0',
                'p1': 'P1',
                'p2': 'P2',
                'p3': 'P3'
            }
            priority_display = priority_map.get(case.priority, 'P2')
        
        # 处理测试步骤（如果是 JSON 格式则解析）
        test_steps_list = []
        if case.test_steps:
            try:
                import json as json_lib
                test_steps_list = json_lib.loads(case.test_steps)
            except:
                # 如果不是 JSON，则按行分割
                steps = case.test_steps.split('\n')
                test_steps_list = [
                    {'step_desc': step.strip(), 'expected_result': ''}
                    for step in steps if step.strip()
                ]
        
        # 如果 test_steps_list 中的步骤没有 expected_result，但有 expected_results 字段，则尝试填充
        if test_steps_list and case.expected_results:
            expected_results_lines = case.expected_results.split('\n')
            for i, step in enumerate(test_steps_list):
                # 如果当前步骤没有 expected_result，则从 expected_results 中取
                if not step.get('expected_result') and i < len(expected_results_lines):
                    step['expected_result'] = expected_results_lines[i]
        
        # 处理模块显示
        module_display = case.get_module_display()
        if not module_display or module_display == case.module:
            try:
                module_obj = TestCaseModule.objects.get(value=case.module)
                module_display = module_obj.name
            except:
                module_display = case.module
        
        case_data = {
            'id': case.id,
            'case_number': case.case_number,
            'title': case.title,
            'module': case.module,
            'module_display': module_display,
            'priority': case.priority,
            'priority_display': priority_display,
            'case_type': case.case_type,
            'case_type_display': case.get_case_type_display(),
            'preconditions': case.preconditions,
            'test_steps': case.test_steps,
            'test_steps_list': test_steps_list,
            'expected_results': case.expected_results,
            'remark': getattr(case, 'remark', ''),
            'maintainer': case.maintainer,
            'tags': case.tags,
            'project_id': case.project.id if case.project else None,
            'project_name': case.project.name if case.project else None,
            'created_at': case.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': case.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
        }
        
        return JsonResponse({
            'success': True,
            'data': case_data
        })
        
    except TestCaseLibrary.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '用例不存在'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@require_http_methods(["PUT"])
def update_case(request, case_id):
    """更新用例"""
    try:
        data = json.loads(request.body)
        case = TestCaseLibrary.objects.get(id=case_id)
        
        # 更新字段
        case.title = data.get('title', case.title)
        case.module = data.get('module', case.module)
        case.priority = data.get('priority', case.priority)
        case.case_type = data.get('case_type', case.case_type)
        case.preconditions = data.get('preconditions', case.preconditions)
        case.remark = data.get('remark', case.remark)
        
        # 处理测试步骤
        test_steps = data.get('test_steps', '')
        if test_steps and isinstance(test_steps, str):
            try:
                import json as json_lib
                steps_list = json_lib.loads(test_steps)
                if isinstance(steps_list, list):
                    # 将步骤列表格式化为文本（只保留步骤描述，不要预期结果，不添加序号）
                    test_steps = '\n'.join([
                        step.get('step_desc', '')
                        for step in steps_list
                    ])
            except:
                pass
        case.test_steps = test_steps
        
        case.expected_results = data.get('expected_results', case.expected_results)
        case.maintainer = data.get('maintainer', case.maintainer)
        case.tags = data.get('tags', case.tags)
        
        # 如果有项目 ID，则更新项目关联
        if 'project_id' in data:
            case.project_id = data['project_id'] if data['project_id'] else None
        
        case.save()
        
        return JsonResponse({
            'success': True,
            'message': '用例更新成功',
            'data': {
                'id': case.id,
                'case_number': case.case_number,
            }
        })
        
    except TestCaseLibrary.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '用例不存在'
        }, status=404)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '无效的 JSON 数据'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'更新失败：{str(e)}'
        }, status=500)


@require_http_methods(["GET"])
def get_approved_test_cases(request):
    """获取测试用例评审中已通过的测试用例"""
    try:
        project_id = request.GET.get('project_id', '')
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 15))
        
        # 查询已通过的测试用例
        queryset = TestCase.objects.filter(status='approved')
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        
        # 分页
        paginator = Paginator(queryset.order_by('-created_at'), page_size)
        page_obj = paginator.get_page(page)
        
        # 序列化数据
        cases_data = []
        for case in page_obj:
            cases_data.append({
                'id': case.id,
                'description': case.description,
                'test_steps': case.test_steps,
                'expected_results': case.expected_results,
                'status': case.status,
                'created_at': case.created_at.strftime('%Y-%m-%d %H:%M:%S') if case.created_at else '',
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
def link_test_cases(request):
    """关联测试用例：将评审通过的用例移入用例库，并从评审列表中移除"""
    try:
        data = json.loads(request.body)
        case_ids = data.get('case_ids', [])
        project_id = data.get('project_id')
        module = data.get('module', 'other')
        
        if not case_ids:
            return JsonResponse({
                'success': False,
                'message': '请选择要关联的测试用例'
            }, status=400)
        
        linked_count = 0
        for case_id in case_ids:
            try:
                # 获取评审通过的用例
                test_case = TestCase.objects.get(id=case_id, status='approved')
                
                # 生成用例编号
                last_case = TestCaseLibrary.objects.order_by('-id').first()
                if last_case:
                    try:
                        last_num = int(last_case.case_number.split('-')[-1])
                        case_number = f"CASE-{last_num + 1:04d}"
                    except:
                        case_number = "CASE-0001"
                else:
                    case_number = "CASE-0001"
                
                # 创建用例库记录
                TestCaseLibrary.objects.create(
                    case_number=case_number,
                    title=test_case.description[:200] if len(test_case.description) > 200 else test_case.description,
                    module=module,
                    priority='p2',
                    case_type='functional',
                    preconditions='',
                    test_steps=test_case.test_steps,
                    expected_results=test_case.expected_results,
                    status='active',
                    maintainer='',
                    tags='AI评审通过',
                    remark=f'从测试用例评审关联（原ID: {test_case.id}）',
                    project_id=project_id if project_id else None
                )
                
                # 从评审列表中移除（删除）
                test_case.delete()
                linked_count += 1
                
            except TestCase.DoesNotExist:
                continue
        
        return JsonResponse({
            'success': True,
            'message': f'成功关联 {linked_count} 条测试用例',
            'data': {'linked_count': linked_count}
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '无效的 JSON 数据'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'关联失败：{str(e)}'
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
        
        def serialize_module(module):
            """递归序列化模块及其子模块，并统计包含所有子模块的用例数"""
            children_data = []
            children = module.children.all().order_by('order', 'name')
            for child in children:
                children_data.append(serialize_module(child))
            
            # 计算当前模块直接关联的用例数（按项目过滤）
            count_query = TestCaseLibrary.objects.filter(module=module.value)
            if project_id:
                count_query = count_query.filter(project_id=project_id)
            direct_count = count_query.count()
            
            # 递归求和：当前模块用例数 + 所有子模块用例数
            children_count = sum(child['count'] for child in children_data)
            
            module_data = {
                'id': module.id,
                'name': module.name,
                'value': module.value,
                'count': direct_count + children_count,
                'children': children_data
            }
            
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
