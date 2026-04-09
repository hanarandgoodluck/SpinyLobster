"""
自动化测试执行任务 - 异步处理UI自动化测试

使用后台线程执行测试，避免阻塞Django主线程
集成AI决策、Playwright执行和Allure报告生成
"""

import uuid
import time
import json
from typing import List, Dict, Any
from datetime import datetime
from django.utils import timezone
from apps.core.models import TestCaseLibrary, AutomationExecutionLog
from apps.ai_agents.case_library.automation.ai_decision_engine import AIDecisionEngine
from apps.ai_agents.case_library.automation.playwright_executor import PlaywrightExecutor
from apps.utils.logger_manager import get_logger, set_task_context, clear_task_context
from apps.utils.progress_registry import set_progress

logger = get_logger(__name__)


def execute_single_case(case_id: int, task_uuid: str = None, 
                       browser: str = 'chromium', headless: bool = True,
                       llm_provider: str = 'deepseek') -> Dict[str, Any]:
    """
    异步执行单个测试用例
    
    Args:
        case_id: 用例库ID
        task_uuid: 任务UUID（可选，不传则自动生成）
        browser: 浏览器类型
        headless: 是否无头模式
        llm_provider: LLM提供商
        
    Returns:
        执行结果
    """
    if not task_uuid:
        task_uuid = f"exec_{uuid.uuid4().hex[:12]}"
    
    # 设置任务上下文
    set_task_context(task_uuid)
    
    execution_log = None
    start_time = time.time()
    
    try:
        logger.info(f"[{task_uuid}] 开始执行测试用例 ID={case_id}")
        
        # 1. 获取测试用例
        try:
            test_case = TestCaseLibrary.objects.get(id=case_id)
        except TestCaseLibrary.DoesNotExist:
            raise ValueError(f"测试用例不存在: ID={case_id}")
        
        # 2. 创建执行日志记录
        execution_log = AutomationExecutionLog.objects.create(
            case=test_case,
            task_uuid=task_uuid,
            status='pending',
            execution_mode='single',
            browser=browser,
            headless=headless
        )
        
        # 3. 更新状态为执行中
        execution_log.status = 'running'
        execution_log.started_at = timezone.now()
        execution_log.save()
        
        set_progress(task_uuid, {
            'step': 1,
            'message': '正在分析测试用例...',
            'percentage': 10
        })
        
        # 4. AI决策分析
        logger.info(f"[{task_uuid}] 步骤1/4: AI决策分析")
        ai_engine = AIDecisionEngine(llm_provider=llm_provider)
        
        test_case_data = {
            'id': test_case.id,
            'case_number': test_case.case_number,
            'title': test_case.title,
            'test_steps': test_case.test_steps,
            'expected_results': test_case.expected_results,
            'preconditions': test_case.preconditions
        }
        
        ai_decision = ai_engine.analyze_test_case(test_case_data)
        
        # 保存AI决策日志
        execution_log.ai_decision_log = json.dumps(ai_decision, ensure_ascii=False, indent=2)
        execution_log.use_multimodal = ai_decision.get('use_multimodal', False)
        execution_log.multimodal_reason = ai_decision.get('reason', '')
        execution_log.save()
        
        set_progress(task_uuid, {
            'step': 2,
            'message': f'AI分析完成 - {"需要" if ai_decision["use_multimodal"] else "不需要"}多模态',
            'percentage': 30
        })
        
        # 5. 生成Playwright脚本
        logger.info(f"[{task_uuid}] 步骤2/4: 生成Playwright测试脚本")
        executor = PlaywrightExecutor()
        
        script_path = executor.generate_test_script(
            test_case=test_case_data,
            ai_decision=ai_decision,
            browser=browser,
            headless=headless
        )
        
        execution_log.script_path = script_path
        execution_log.save()
        
        set_progress(task_uuid, {
            'step': 3,
            'message': '测试脚本生成完成，准备执行...',
            'percentage': 50
        })
        
        # 6. 执行测试
        logger.info(f"[{task_uuid}] 步骤3/4: 执行Playwright测试")
        exec_result = executor.execute_test(script_path, task_uuid)
        
        # 7. 生成Allure报告
        logger.info(f"[{task_uuid}] 步骤4/4: 生成Allure报告")
        set_progress(task_uuid, {
            'step': 4,
            'message': '正在生成Allure报告...',
            'percentage': 80
        })
        
        report_path = ""
        if exec_result.get('allure_results_dir'):
            report_path = executor.generate_allure_report(
                exec_result['allure_results_dir']
            )
        
        # 8. 更新执行日志
        execution_time = time.time() - start_time
        execution_log.execution_time = execution_time
        execution_log.completed_at = timezone.now()
        
        if exec_result['success']:
            execution_log.status = 'passed'
            execution_log.report_url = f"/automation/report/{task_uuid}/"
            execution_log.allure_report_path = report_path
            logger.info(f"[{task_uuid}] ✅ 测试通过")
        else:
            execution_log.status = 'failed'
            execution_log.error_message = exec_result.get('error_message', '') or exec_result.get('stderr', '')[:500]
            logger.warning(f"[{task_uuid}] ❌ 测试失败: {execution_log.error_message[:100]}")
        
        execution_log.save()
        
        set_progress(task_uuid, {
            'step': 5,
            'message': f'执行完成 - {execution_log.get_status_display()}',
            'percentage': 100
        })
        
        return {
            'success': True,
            'task_uuid': task_uuid,
            'status': execution_log.status,
            'execution_time': execution_time,
            'report_url': execution_log.report_url,
            'use_multimodal': execution_log.use_multimodal
        }
        
    except Exception as e:
        logger.error(f"[{task_uuid}] 执行异常: {e}", exc_info=True)
        
        # 更新执行日志为错误状态
        if execution_log:
            execution_log.status = 'error'
            execution_log.error_message = str(e)
            execution_log.completed_at = timezone.now()
            execution_log.execution_time = time.time() - start_time
            execution_log.save()
        
        return {
            'success': False,
            'task_uuid': task_uuid,
            'error_message': str(e)
        }
    
    finally:
        # 清除任务上下文
        clear_task_context()


def execute_batch_cases(case_ids: List[int], task_uuid: str = None,
                       browser: str = 'chromium', headless: bool = True,
                       llm_provider: str = 'deepseek') -> Dict[str, Any]:
    """
    批量执行测试用例
    
    Args:
        case_ids: 用例ID列表
        task_uuid: 任务UUID
        browser: 浏览器类型
        headless: 是否无头模式
        llm_provider: LLM提供商
        
    Returns:
        批量执行结果
    """
    if not task_uuid:
        task_uuid = f"batch_{uuid.uuid4().hex[:12]}"
    
    set_task_context(task_uuid)
    
    total = len(case_ids)
    results = []
    success_count = 0
    failed_count = 0
    
    try:
        logger.info(f"[{task_uuid}] 开始批量执行 {total} 个测试用例")
        
        for i, case_id in enumerate(case_ids, 1):
            set_progress(task_uuid, {
                'step': i,
                'total': total,
                'message': f'执行第 {i}/{total} 个用例',
                'percentage': int((i - 1) / total * 100)
            })
            
            # 为每个用例生成独立的task_uuid
            case_task_uuid = f"{task_uuid}_case{i}"
            
            result = execute_single_case(
                case_id=case_id,
                task_uuid=case_task_uuid,
                browser=browser,
                headless=headless,
                llm_provider=llm_provider
            )
            
            results.append(result)
            
            if result['success']:
                success_count += 1
            else:
                failed_count += 1
        
        # 最终进度
        set_progress(task_uuid, {
            'step': total,
            'total': total,
            'message': f'批量执行完成 - 成功: {success_count}, 失败: {failed_count}',
            'percentage': 100
        })
        
        logger.info(f"[{task_uuid}] 批量执行完成 - 成功: {success_count}, 失败: {failed_count}")
        
        return {
            'success': True,
            'task_uuid': task_uuid,
            'total': total,
            'success_count': success_count,
            'failed_count': failed_count,
            'results': results
        }
        
    except Exception as e:
        logger.error(f"[{task_uuid}] 批量执行异常: {e}", exc_info=True)
        return {
            'success': False,
            'task_uuid': task_uuid,
            'error_message': str(e)
        }
    
    finally:
        clear_task_context()
