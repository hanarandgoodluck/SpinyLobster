"""
UI自动化测试AI助手视图

提供测试用例选择、执行、状态查询和报告查看功能
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
from apps.core.models import TestCaseLibrary, AutomationExecutionLog
from apps.ai_agents.case_library.automation.tasks import execute_single_case, execute_batch_cases
from apps.utils.logger_manager import get_logger
from apps.utils.progress_registry import get_progress

logger = get_logger(__name__)


def ui_automation_page(request):
    """UI自动化测试主页面"""
    # 获取项目ID
    project_id = request.GET.get('project_id', '')
    
    context = {
        'project_id': project_id,
    }
    
    return render(request, 'ui_automation/ui_automation.html', context)


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
    """提供Allure报告静态文件服务"""
    try:
        base_dir = Path(settings.BASE_DIR) / 'automation_results' / 'allure-report'
        
        file_path = (base_dir / path).resolve()
        if not str(file_path).startswith(str(base_dir.resolve())):
            raise Http404("非法文件路径")
        
        if not file_path.exists() or not file_path.is_file():
            index_path = base_dir / 'index.html'
            if index_path.exists():
                file_path = index_path
            else:
                raise Http404("报告文件不存在")
        
        content_types = {
            '.html': 'text/html',
            '.css': 'text/css',
            '.js': 'application/javascript',
            '.json': 'application/json',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.gif': 'image/gif',
            '.svg': 'image/svg+xml',
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
