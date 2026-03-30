from django.urls import path
from . import views

app_name = 'ai_config'

urlpatterns = [
    # 页面
    path('', views.ai_config_view, name='ai_config'),
    
    # 全局配置 API
    path('api/global/', views.get_global_config, name='get_global_config'),
    path('api/global/save/', views.save_global_config, name='save_global_config'),
    
    # 项目配置 API
    path('api/project/<int:project_id>/', views.get_project_config, name='get_project_config'),
    path('api/project/<int:project_id>/save/', views.save_project_config, name='save_project_config'),
    
    # 连接测试 API
    path('api/test-connection/', views.test_connection, name='test_connection'),
]
