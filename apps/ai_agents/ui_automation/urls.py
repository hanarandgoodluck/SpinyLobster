"""
UI自动化测试AI助手 URL配置
"""

from django.urls import path
from . import views

app_name = 'ui_automation'

urlpatterns = [
    # 主页面
    path('', views.ui_automation_page, name='ui_automation_page'),
    
    # API 路由 - 执行测试
    path('api/execute/', views.execute_test_cases, name='execute_test_cases'),
    path('api/status/<str:task_uuid>/', views.get_execution_status, name='get_execution_status'),
    path('api/report/<str:task_uuid>/', views.get_execution_report, name='get_execution_report'),
    path('api/history/', views.get_execution_history, name='get_execution_history'),
    
    # Allure报告服务
    path('report/<path:path>', views.serve_allure_report, name='serve_allure_report'),
]
