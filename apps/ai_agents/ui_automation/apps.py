"""
UI自动化测试AI助手应用配置
"""

from django.apps import AppConfig


class UiAutomationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.ai_agents.ui_automation'
    verbose_name = 'UI自动化测试'
