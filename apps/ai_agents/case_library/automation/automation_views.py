"""
自动化测试执行 API 视图

提供测试用例执行、状态查询、报告获取等接口
"""

import json
import os
import threading
from pathlib import Path
from django.http import JsonResponse, FileResponse, Http404
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from apps.core.models import AutomationExecutionLog
from apps.ai_agents.case_library.automation.tasks import execute_single_case, execute_batch_cases
from apps.utils.logger_manager import get_logger
from apps.utils.progress_registry import get_progress

logger = get_logger(__name__)


@require_http_methods(["POST"])
def execute_test_cases(request):
    """
    执行测试用例（支持单个和批量）
    
    Request Body:
    {
        "case_ids": [1, 2, 3],  // 用例ID列表
        "browser": "chromium",   // 浏览器类型: chromium/firefox/webkit
        "headless": true,         // 是否无头模式
        "llm_provider": "deepseek" // LLM提供商
    }
    """
    try:
        data = json.loads(request.body)
        case_ids = data.get('case_ids', [])
        
        if not case_ids:
            return JsonResponse({
                'success': False,
                'message': '请选择至少一个测试用例'
            }, status=400)
        
        # 获取配置参数
        browser = data.get('browser', 'chromium')
        headless = data.get('headless', True)
        llm_provider = data.get('llm_provider', 'deepseek')
        
        logger.info(f"收到执行请求 - 用例数: {len(case_ids)}, 浏览器: {browser}, 无头模式: {headless}")
        
        # 启动后台线程执行
        def _bg_execute():
            try:
                if len(case_ids) == 1:
                    # 单个用例执行
                    result = execute_single_case(
                        case_id=case_ids[0],
                        browser=browser,
                        headless=headless,
                        llm_provider=llm_provider
                    )
                else:
                    # 批量执行
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
        
        # 立即返回任务信息
        return JsonResponse({
            'success': True,
            'message': f'已启动{len(case_ids)}个测试用例的执行',
            'task_count': len(case_ids),
            'execution_mode': 'single' if len(case_ids) == 1 else 'batch'
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
    """
    获取执行状态
    
    Args:
        task_uuid: 任务UUID
        
    Returns:
        执行状态和进度信息
    """
    try:
        # 查询执行日志
        try:
            execution_log = AutomationExecutionLog.objects.get(task_uuid=task_uuid)
        except AutomationExecutionLog.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': '任务不存在'
            }, status=404)
        
        # 获取实时进度
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
    """
    获取执行报告
    
    Args:
        task_uuid: 任务UUID
        
    Returns:
        报告信息和访问链接
    """
    try:
        # 查询执行日志
        try:
            execution_log = AutomationExecutionLog.objects.get(task_uuid=task_uuid)
        except AutomationExecutionLog.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': '任务不存在'
            }, status=404)
        
        # 检查是否已完成
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
    """
    获取执行历史记录
    
    Query Params:
        page: 页码 (默认1)
        page_size: 每页数量 (默认20)
        case_id: 用例ID筛选 (可选)
        status: 状态筛选 (可选)
    """
    try:
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))
        case_id = request.GET.get('case_id')
        status = request.GET.get('status')
        
        # 构建查询集
        queryset = AutomationExecutionLog.objects.all()
        
        if case_id:
            queryset = queryset.filter(case_id=case_id)
        
        if status:
            queryset = queryset.filter(status=status)
        
        # 分页
        from django.core.paginator import Paginator
        paginator = Paginator(queryset.order_by('-created_at'), page_size)
        page_obj = paginator.get_page(page)
        
        # 序列化数据
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
    """
    提供Allure报告静态文件服务
    
    Args:
        path: 文件路径
        
    Returns:
        文件响应
    """
    try:
        # Allure报告基础目录
        base_dir = Path(settings.BASE_DIR) / 'automation_results' / 'allure-report'
        
        # 安全检查：防止路径遍历攻击
        file_path = (base_dir / path).resolve()
        if not str(file_path).startswith(str(base_dir.resolve())):
            raise Http404("非法文件路径")
        
        if not file_path.exists() or not file_path.is_file():
            # 如果是目录或不存在，尝试返回index.html
            index_path = base_dir / 'index.html'
            if index_path.exists():
                file_path = index_path
            else:
                raise Http404("报告文件不存在")
        
        # 确定Content-Type
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
