"""
测试报告服务 - BeautifulReport HTML 报告、日志捕获、敏感信息过滤
（无需 Java 环境）
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from apps.utils.logger_manager import get_logger

logger = get_logger(__name__)


class ReportService:
    """测试报告服务"""

    # 敏感信息正则表达式
    SENSITIVE_PATTERNS = [
        (r'password["\s:=]+["\']([^"\']+)["\']', 'password="***"'),
        (r'pwd["\s:=]+["\']([^"\']+)["\']', 'pwd="***"'),
        (r'token["\s:=]+["\']([^"\']+)["\']', 'token="***"'),
        (r'api[_\-]?key["\s:=]+["\']([^"\']+)["\']', 'api_key="***"'),
        (r'secret["\s:=]+["\']([^"\']+)["\']', 'secret="***"'),
    ]

    def __init__(self, base_output_dir: str = None):
        self.base_output_dir = base_output_dir or os.path.join(
            Path(__file__).resolve().parent.parent.parent.parent,
            'automation_results'
        )
        os.makedirs(self.base_output_dir, exist_ok=True)

    def filter_sensitive_info(self, text: str) -> str:
        """过滤日志中的敏感信息"""
        if not text:
            return ""
        
        filtered = text
        for pattern, replacement in self.SENSITIVE_PATTERNS:
            filtered = re.sub(pattern, replacement, filtered, flags=re.IGNORECASE)
        
        return filtered

    def package_report_for_download(self, report_dir: str, task_uuid: str) -> str:
        """
        打包报告为 ZIP 文件供下载
        
        Args:
            report_dir: 报告目录或文件路径
            task_uuid: 任务 UUID
            
        Returns:
            ZIP 文件路径
        """
        try:
            import zipfile
            
            download_dir = os.path.join(self.base_output_dir, 'downloads')
            os.makedirs(download_dir, exist_ok=True)
            
            zip_path = os.path.join(download_dir, f'report_{task_uuid}.zip')
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # 如果是文件，直接添加
                if os.path.isfile(report_dir):
                    zipf.write(report_dir, os.path.basename(report_dir))
                else:
                    # 如果是目录，遍历添加
                    for root, dirs, files in os.walk(report_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, report_dir)
                            zipf.write(file_path, arcname)
            
            logger.info(f"报告打包成功: {zip_path}")
            return zip_path

        except Exception as e:
            logger.error(f"打包报告失败: {e}", exc_info=True)
            return ""

    def create_error_report(self, task_uuid: str, error_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建错误报告记录
        
        Args:
            task_uuid: 任务 UUID
            error_info: 错误信息字典
            
        Returns:
            报告信息
        """
        from apps.core.models import TaskExecutionReport
        
        # 过滤敏感信息
        error_summary = self.filter_sensitive_info(
            error_info.get('error_message', '')[:1000]
        )
        error_stack = self.filter_sensitive_info(
            error_info.get('stack_trace', '')
        )
        
        # 确定报告路径
        report_path = os.path.join(self.base_output_dir, 'reports', task_uuid)
        
        # 创建报告记录
        report = TaskExecutionReport.objects.create(
            task_uuid=task_uuid,
            report_path=report_path,
            status=error_info.get('status', 'ERROR'),
            error_log_summary=error_summary,
            error_stack_trace=error_stack,
            screenshot_path=error_info.get('screenshot_path', ''),
            ai_diagnosis=error_info.get('ai_diagnosis', ''),
            execution_time=error_info.get('execution_time')
        )
        
        logger.info(f"错误报告创建成功: {task_uuid}")
        
        return {
            'id': report.id,
            'task_uuid': report.task_uuid,
            'status': report.status,
            'error_log_summary': report.error_log_summary,
            'report_url': f"/ui_automation/report/{task_uuid}/index.html"
        }
