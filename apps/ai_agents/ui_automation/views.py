"""
UI自动化测试AI助手视图

提供测试用例选择、执行、状态查询和报告查看功能
支持任务卡片管理中心：任务CRUD、执行引擎路由、报告管理
"""

import json
import os
import threading
from pathlib import Path
from django.shortcuts import render
from django.http import JsonResponse, FileResponse, Http404
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.core.paginator import Paginator
from django.db import transaction
from apps.core.models import TestCaseLibrary, AutomationExecutionLog, AutomationTask, TaskCaseRelation
from apps.ai_agents.case_library.automation.tasks import execute_single_case, execute_batch_cases
from apps.utils.logger_manager import get_logger
from apps.utils.progress_registry import get_progress

logger = get_logger(__name__)


def ui_automation_page(request):
    """UI自动化测试主页面 - 任务卡片管理中心"""
    # 获取项目ID
    project_id = request.GET.get('project_id', '')
    
    context = {
        'project_id': project_id,
    }
    
    return render(request, 'ui_automation/ui_automation_v2.html', context)


@require_http_methods(["POST"])
def execute_test_cases(request):
    """执行测试用例"""
    try:
        data = json.loads(request.body)
        case_ids = data.get('case_ids', [])
        
        if not case_ids:
            return JsonResponse({
                'success': False,
                'message': '请选择至少一个测试用例'
            }, status=400)
        
        browser = data.get('browser', 'chromium')
        headless = data.get('headless', True)
        llm_provider = data.get('llm_provider', 'deepseek')
        
        logger.info(f"收到执行请求 - 用例数: {len(case_ids)}, 浏览器: {browser}")
        
        def _bg_execute():
            try:
                if len(case_ids) == 1:
                    result = execute_single_case(
                        case_id=case_ids[0],
                        browser=browser,
                        headless=headless,
                        llm_provider=llm_provider
                    )
                else:
                    result = execute_batch_cases(
                        case_ids=case_ids,
                        browser=browser,
                        headless=headless,
                        llm_provider=llm_provider
                    )
                logger.info(f"后台执行完成: {result}")
            except Exception as e:
                logger.error(f"后台执行异常: {e}", exc_info=True)
        
        thread = threading.Thread(target=_bg_execute, name=f"exec-{len(case_ids)}-cases")
        thread.daemon = True
        thread.start()
        
        return JsonResponse({
            'success': True,
            'message': f'已启动{len(case_ids)}个测试用例的执行',
            'task_count': len(case_ids),
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '无效的JSON数据'
        }, status=400)
    except Exception as e:
        logger.error(f"执行请求处理失败: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'执行失败: {str(e)}'
        }, status=500)


@require_http_methods(["GET"])
def get_execution_status(request, task_uuid: str):
    """获取执行状态"""
    try:
        try:
            execution_log = AutomationExecutionLog.objects.get(task_uuid=task_uuid)
        except AutomationExecutionLog.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': '任务不存在'
            }, status=404)
        
        progress = get_progress(task_uuid)
        
        return JsonResponse({
            'success': True,
            'data': {
                'task_uuid': execution_log.task_uuid,
                'status': execution_log.status,
                'status_display': execution_log.get_status_display(),
                'execution_mode': execution_log.execution_mode,
                'browser': execution_log.browser,
                'headless': execution_log.headless,
                'use_multimodal': execution_log.use_multimodal,
                'progress': progress,
                'execution_time': execution_log.execution_time,
                'started_at': execution_log.started_at.strftime('%Y-%m-%d %H:%M:%S') if execution_log.started_at else None,
                'completed_at': execution_log.completed_at.strftime('%Y-%m-%d %H:%M:%S') if execution_log.completed_at else None,
                'error_message': execution_log.error_message,
                'report_url': execution_log.report_url
            }
        })
        
    except Exception as e:
        logger.error(f"获取执行状态失败: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@require_http_methods(["GET"])
def get_execution_report(request, task_uuid: str):
    """获取执行报告"""
    try:
        try:
            execution_log = AutomationExecutionLog.objects.get(task_uuid=task_uuid)
        except AutomationExecutionLog.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': '任务不存在'
            }, status=404)
        
        if execution_log.status in ['pending', 'running']:
            return JsonResponse({
                'success': False,
                'message': '测试仍在执行中，请稍后再试'
            }, status=400)
        
        return JsonResponse({
            'success': True,
            'data': {
                'task_uuid': execution_log.task_uuid,
                'status': execution_log.status,
                'report_url': execution_log.report_url,
                'allure_report_path': execution_log.allure_report_path,
                'execution_time': execution_log.execution_time,
                'ai_decision': json.loads(execution_log.ai_decision_log) if execution_log.ai_decision_log else None,
                'use_multimodal': execution_log.use_multimodal,
                'multimodal_reason': execution_log.multimodal_reason
            }
        })
        
    except Exception as e:
        logger.error(f"获取执行报告失败: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@require_http_methods(["GET"])
def get_execution_history(request):
    """获取执行历史记录"""
    try:
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))
        case_id = request.GET.get('case_id')
        status = request.GET.get('status')
        
        queryset = AutomationExecutionLog.objects.all()
        
        if case_id:
            queryset = queryset.filter(case_id=case_id)
        
        if status:
            queryset = queryset.filter(status=status)
        
        paginator = Paginator(queryset.order_by('-created_at'), page_size)
        page_obj = paginator.get_page(page)
        
        history_data = []
        for log in page_obj:
            history_data.append({
                'id': log.id,
                'task_uuid': log.task_uuid,
                'case_id': log.case.id if log.case else None,
                'case_number': log.case.case_number if log.case else None,
                'case_title': log.case.title if log.case else None,
                'status': log.status,
                'status_display': log.get_status_display(),
                'execution_mode': log.execution_mode,
                'browser': log.browser,
                'use_multimodal': log.use_multimodal,
                'execution_time': log.execution_time,
                'report_url': log.report_url,
                'created_at': log.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'started_at': log.started_at.strftime('%Y-%m-%d %H:%M:%S') if log.started_at else None,
                'completed_at': log.completed_at.strftime('%Y-%m-%d %H:%M:%S') if log.completed_at else None,
            })
        
        return JsonResponse({
            'success': True,
            'data': {
                'history': history_data,
                'total': paginator.count,
                'page': page,
                'page_size': page_size,
                'total_pages': paginator.num_pages
            }
        })
        
    except Exception as e:
        logger.error(f"获取执行历史失败: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


def serve_allure_report(request, path):
    """提供测试报告静态文件服务（支持 BeautifulReport HTML 报告）"""
    try:
        from django.conf import settings
        from pathlib import Path
        
        # 尝试从路径中提取 task_uuid（格式: {task_uuid}/ 或 {task_uuid}/report.html）
        parts = path.rstrip('/').split('/')
        if not parts:
            raise Http404("无效的报告路径")
        
        task_uuid = parts[0]
        file_name = parts[1] if len(parts) > 1 else 'report.html'
        
        # BeautifulReport 报告路径
        base_dir = Path(settings.BASE_DIR) / 'automation_results' / 'reports' / task_uuid
        file_path = (base_dir / file_name).resolve()
        
        # 安全检查：防止目录遍历
        if not str(file_path).startswith(str(base_dir.resolve())):
            raise Http404("非法文件路径")
        
        # 如果指定文件不存在，尝试找 report.html
        if not file_path.exists() or not file_path.is_file():
            if file_name != 'report.html':
                file_path = base_dir / 'report.html'
            
            if not file_path.exists():
                raise Http404("报告文件不存在")
        
        content_types = {
            '.html': 'text/html; charset=utf-8',
            '.css': 'text/css',
            '.js': 'application/javascript',
            '.json': 'application/json',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.gif': 'image/gif',
            '.svg': 'image/svg+xml',
            '.woff': 'font/woff',
            '.woff2': 'font/woff2',
            '.ttf': 'font/ttf',
        }
        
        ext = file_path.suffix.lower()
        content_type = content_types.get(ext, 'application/octet-stream')
        
        return FileResponse(
            open(file_path, 'rb'),
            content_type=content_type
        )
        
    except Http404:
        raise
    except Exception as e:
        logger.error(f"提供报告文件失败: {e}", exc_info=True)
        raise Http404("文件不存在")


# ==================== 任务卡片管理中心 API ====================

@require_http_methods(["GET"])
def get_task_list(request):
    """获取任务列表（支持分页和过滤）"""
    try:
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))
        project_id = request.GET.get('project_id', '')
        task_type = request.GET.get('task_type', '')
        status = request.GET.get('status', '')
        search = request.GET.get('search', '')
        
        queryset = AutomationTask.objects.all()
        
        # 项目过滤
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        
        # 类型过滤
        if task_type:
            queryset = queryset.filter(task_type=task_type)
        
        # 状态过滤
        if status:
            queryset = queryset.filter(status=status)
        
        # 搜索过滤
        if search:
            queryset = queryset.filter(name__icontains=search)
        
        # 按创建时间倒序
        queryset = queryset.order_by('-created_at')
        
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)
        
        tasks_data = []
        for task in page_obj:
            # 获取关联用例数
            case_count = TaskCaseRelation.objects.filter(task=task).count()
            
            tasks_data.append({
                'id': task.id,
                'name': task.name,
                'description': task.description,
                'task_type': task.task_type,
                'task_type_display': task.get_task_type_display(),
                'status': task.status,
                'status_display': task.get_status_display(),
                'config': task.config,
                'use_multimodal': task.use_multimodal,
                'llm_provider': task.llm_provider,
                'case_count': case_count,
                'last_run_time': task.last_run_time.strftime('%Y-%m-%d %H:%M:%S') if task.last_run_time else None,
                'last_run_status': task.last_run_status,
                'last_run_status_display': dict(AutomationExecutionLog.STATUS_CHOICES).get(task.last_run_status, '未执行') if task.last_run_status else '未执行',
                'total_executions': task.total_executions,
                'success_count': task.success_count,
                'failed_count': task.failed_count,
                'project_id': task.project_id,
                'created_at': task.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': task.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
            })
        
        return JsonResponse({
            'success': True,
            'data': {
                'tasks': tasks_data,
                'total': paginator.count,
                'page': page,
                'page_size': page_size,
                'total_pages': paginator.num_pages
            }
        })
        
    except Exception as e:
        logger.error(f"获取任务列表失败: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@require_http_methods(["POST"])
def create_task(request):
    """创建新任务"""
    try:
        data = json.loads(request.body)
        logger.info(f'创建任务请求数据: {data}')
        
        # 验证必填字段
        name = data.get('name', '').strip()
        if not name:
            logger.warning('任务名称为空')
            return JsonResponse({
                'success': False,
                'message': '任务名称不能为空'
            }, status=400)
        
        task_type = data.get('task_type', 'web')
        if task_type not in ['web', 'api']:
            logger.warning(f'无效的测试类型: {task_type}')
            return JsonResponse({
                'success': False,
                'message': f'无效的测试类型: {task_type}'
            }, status=400)
        
        # 创建任务
        with transaction.atomic():
            task = AutomationTask.objects.create(
                name=name,
                description=data.get('description', ''),
                task_type=task_type,
                config=data.get('config', {}),
                use_multimodal=data.get('use_multimodal', False),
                llm_provider=data.get('llm_provider', 'deepseek'),
                project_id=data.get('project_id') if data.get('project_id') else None,
                created_by=request.user if request.user.is_authenticated else None
            )
            
            # 关联用例
            case_ids = data.get('case_ids', [])
            if case_ids:
                relations = [
                    TaskCaseRelation(task=task, case_id=case_id, order=i)
                    for i, case_id in enumerate(case_ids)
                ]
                TaskCaseRelation.objects.bulk_create(relations)
        
        return JsonResponse({
            'success': True,
            'message': '任务创建成功',
            'data': {
                'id': task.id,
                'name': task.name,
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '无效的JSON数据'
        }, status=400)
    except Exception as e:
        logger.error(f"创建任务失败: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'创建失败: {str(e)}'
        }, status=500)


@require_http_methods(["GET"])
def get_task_detail(request, task_id):
    """获取任务详情"""
    try:
        task = AutomationTask.objects.get(id=task_id)
        
        # 获取关联用例
        relations = TaskCaseRelation.objects.filter(task=task).order_by('order')
        cases = []
        for rel in relations:
            cases.append({
                'id': rel.case.id,
                'case_number': rel.case.case_number,
                'title': rel.case.title,
                'module': rel.case.module,
                'priority': rel.case.priority,
                'order': rel.order
            })
        
        return JsonResponse({
            'success': True,
            'data': {
                'id': task.id,
                'name': task.name,
                'description': task.description,
                'task_type': task.task_type,
                'task_type_display': task.get_task_type_display(),
                'status': task.status,
                'config': task.config,
                'use_multimodal': task.use_multimodal,
                'llm_provider': task.llm_provider,
                'cases': cases,
                'last_run_time': task.last_run_time.strftime('%Y-%m-%d %H:%M:%S') if task.last_run_time else None,
                'last_run_status': task.last_run_status,
                'total_executions': task.total_executions,
                'success_count': task.success_count,
                'failed_count': task.failed_count,
                'created_at': task.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            }
        })
        
    except AutomationTask.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '任务不存在'
        }, status=404)
    except Exception as e:
        logger.error(f"获取任务详情失败: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@require_http_methods(["PUT"])
def update_task(request, task_id):
    """更新任务"""
    try:
        data = json.loads(request.body)
        task = AutomationTask.objects.get(id=task_id)
        
        with transaction.atomic():
            # 更新基本信息
            task.name = data.get('name', task.name)
            task.description = data.get('description', task.description)
            task.task_type = data.get('task_type', task.task_type)
            task.use_multimodal = data.get('use_multimodal', task.use_multimodal)
            task.llm_provider = data.get('llm_provider', task.llm_provider)
            
            # 更新配置（密码留空则不更新）
            if 'config' in data:
                new_config = data['config']
                old_config = task.config
                
                # 如果是Web类型且密码为空，保留旧密码
                if task.task_type == 'web' and not new_config.get('password'):
                    new_config['password'] = old_config.get('password', '')
                
                task.config = new_config
            
            task.save()
            
            # 更新关联用例
            if 'case_ids' in data:
                # 删除旧关联
                TaskCaseRelation.objects.filter(task=task).delete()
                
                # 创建新关联
                case_ids = data['case_ids']
                if case_ids:
                    relations = [
                        TaskCaseRelation(task=task, case_id=case_id, order=i)
                        for i, case_id in enumerate(case_ids)
                    ]
                    TaskCaseRelation.objects.bulk_create(relations)
        
        return JsonResponse({
            'success': True,
            'message': '任务更新成功'
        })
        
    except AutomationTask.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '任务不存在'
        }, status=404)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '无效的JSON数据'
        }, status=400)
    except Exception as e:
        logger.error(f"更新任务失败: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'更新失败: {str(e)}'
        }, status=500)


@require_http_methods(["DELETE"])
def delete_task(request, task_id):
    """删除任务"""
    try:
        task = AutomationTask.objects.get(id=task_id)
        task_name = task.name
        task.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'任务 "{task_name}" 已删除'
        })
        
    except AutomationTask.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '任务不存在'
        }, status=404)
    except Exception as e:
        logger.error(f"删除任务失败: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'删除失败: {str(e)}'
        }, status=500)


@require_http_methods(["POST"])
def execute_task(request, task_id):
    """执行任务（根据任务类型路由到不同执行器）"""
    try:
        task = AutomationTask.objects.get(id=task_id)
        
        # 获取关联用例
        relations = TaskCaseRelation.objects.filter(task=task).order_by('order')
        case_ids = [rel.case_id for rel in relations]
        
        if not case_ids:
            return JsonResponse({
                'success': False,
                'message': '任务没有关联任何用例'
            }, status=400)
        
        # 根据任务类型选择执行策略
        browser = 'chromium'
        headless = False  # 调试模式：显示浏览器窗口
        llm_provider = task.llm_provider
        
        # TODO: 未来可以根据 task_type 路由到不同的执行器
        # if task.task_type == 'api':
        #     result = execute_api_task(task, case_ids)
        # else:
        #     result = execute_web_task(task, case_ids)
        
        def _bg_execute():
            try:
                if len(case_ids) == 1:
                    result = execute_single_case(
                        case_id=case_ids[0],
                        browser=browser,
                        headless=headless,
                        llm_provider=llm_provider,
                        task_name=task.name,  # 传递任务名称
                        task_id=task.id  # 传递任务ID
                    )
                else:
                    result = execute_batch_cases(
                        case_ids=case_ids,
                        browser=browser,
                        headless=headless,
                        llm_provider=llm_provider,
                        task_name=task.name,  # 传递任务名称
                        task_id=task.id  # 传递任务ID
                    )
                
                # 更新任务统计信息
                from django.utils import timezone
                execution_log = AutomationExecutionLog.objects.get(task_uuid=result.get('task_uuid'))
                
                task.last_run_time = timezone.now()
                task.last_run_status = execution_log.status
                task.total_executions += 1
                
                if execution_log.status == 'passed':
                    task.success_count += 1
                elif execution_log.status in ['failed', 'error']:
                    task.failed_count += 1
                
                task.save()
                
                logger.info(f"任务 {task.id} 执行完成，状态: {execution_log.status}")
            except Exception as e:
                logger.error(f"任务后台执行异常: {e}", exc_info=True)
        
        thread = threading.Thread(target=_bg_execute, name=f"task-{task_id}-exec")
        thread.daemon = True
        thread.start()
        
        return JsonResponse({
            'success': True,
            'message': f'任务 "{task.name}" 已开始执行',
            'case_count': len(case_ids)
        })
        
    except AutomationTask.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '任务不存在'
        }, status=404)
    except Exception as e:
        logger.error(f"执行任务失败: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'执行失败: {str(e)}'
        }, status=500)


@require_http_methods(["GET"])
def get_task_execution_history(request, task_id):
    """获取任务的执行历史"""
    try:
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))
        
        # 验证任务存在
        task = AutomationTask.objects.get(id=task_id)
        
        # 获取该任务关联的所有用例的执行记录（通过task外键过滤）
        queryset = AutomationExecutionLog.objects.filter(
            task=task
        ).order_by('-created_at')
        
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)
        
        history_data = []
        for log in page_obj:
            history_data.append({
                'id': log.id,
                'task_uuid': log.task_uuid,
                'case_id': log.case.id if log.case else None,
                'case_number': log.case.case_number if log.case else None,
                'case_title': log.case.title if log.case else None,
                'status': log.status,
                'status_display': log.get_status_display(),
                'execution_mode': log.execution_mode,
                'browser': log.browser,
                'use_multimodal': log.use_multimodal,
                'execution_time': log.execution_time,
                'report_url': log.report_url,
                'created_at': log.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'started_at': log.started_at.strftime('%Y-%m-%d %H:%M:%S') if log.started_at else None,
                'completed_at': log.completed_at.strftime('%Y-%m-%d %H:%M:%S') if log.completed_at else None,
            })
        
        return JsonResponse({
            'success': True,
            'data': {
                'history': history_data,
                'total': paginator.count,
                'page': page,
                'page_size': page_size,
                'total_pages': paginator.num_pages
            }
        })
        
    except AutomationTask.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '任务不存在'
        }, status=404)
    except Exception as e:
        logger.error(f"获取任务执行历史失败: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)
