from django.urls import path
from . import views
from .automation import automation_views

app_name = 'case_library'

urlpatterns = [
    # 页面路由
    path('', views.case_library_page, name='case_library_page'),
    
    # API 路由
    path('api/list/', views.case_library_list, name='case_library_list'),
    path('api/create/', views.create_case, name='create_case'),
    path('api/update/<int:case_id>/', views.update_case, name='update_case'),
    path('api/delete/', views.delete_case, name='delete_case'),
    path('api/detail/<int:case_id>/', views.get_case_detail, name='get_case_detail'),
    path('api/modules/', views.get_modules, name='get_modules'),
    path('api/modules/create/', views.create_module, name='create_module'),
    path('api/modules/<int:module_id>/update/', views.update_module, name='update_module'),
    path('api/modules/<int:module_id>/delete/', views.delete_module, name='delete_module'),
    # 关联测试用例
    path('api/approved-cases/', views.get_approved_test_cases, name='get_approved_test_cases'),
    path('api/link-cases/', views.link_test_cases, name='link_test_cases'),
    
    # 自动化执行 API
    path('api/automation/execute/', automation_views.execute_test_cases, name='execute_test_cases'),
    path('api/automation/status/<str:task_uuid>/', automation_views.get_execution_status, name='get_execution_status'),
    path('api/automation/report/<str:task_uuid>/', automation_views.get_execution_report, name='get_execution_report'),
    path('api/automation/history/', automation_views.get_execution_history, name='get_execution_history'),
    
    # Allure报告静态文件服务
    path('report/<path:path>', automation_views.serve_allure_report, name='serve_allure_report'),
]
