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
    
    # ==================== 任务卡片管理中心 API ====================
    # 任务 CRUD
    path('api/tasks/', views.get_task_list, name='get_task_list'),
    path('api/tasks/create/', views.create_task, name='create_task'),
    path('api/tasks/<int:task_id>/', views.get_task_detail, name='get_task_detail'),
    path('api/tasks/<int:task_id>/update/', views.update_task, name='update_task'),
    path('api/tasks/<int:task_id>/delete/', views.delete_task, name='delete_task'),
    
    # 任务执行
    path('api/tasks/<int:task_id>/execute/', views.execute_task, name='execute_task'),
    
    # 任务执行历史
    path('api/tasks/<int:task_id>/history/', views.get_task_execution_history, name='get_task_execution_history'),
]
