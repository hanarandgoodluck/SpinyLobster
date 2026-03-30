from django.urls import path
from . import views
from .views_sse import stream_logs

urlpatterns = [
    # 页面路由
    path('', views.index, name='index'),
    path('projects/', views.project_list_view, name='project_list'),
    path('projects/<int:project_id>/', views.project_detail_view, name='project_detail_view'),

    path('knowledge/', views.knowledge_view, name='knowledge'),
    
    #知识库文件上传页面
    path('upload/', views.upload_single_file, name='upload_single_file'),

    path('api/add-knowledge/', views.add_knowledge, name='add_knowledge'),
    path('api/knowledge-list/', views.knowledge_list, name='knowledge_list'),
    path('api/search-knowledge/', views.search_knowledge, name='search_knowledge'),   
    path('api/stream-logs/', stream_logs, name='stream_logs'),
    
    # 项目管理路由
    path('api/projects/', views.project_list_create, name='project_list_create'),
    path('api/projects/<int:project_id>/', views.project_detail, name='project_detail'),
] 