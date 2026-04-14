from django.urls import path
from . import views

app_name = 'ai_requirement_analysis'

urlpatterns = [
    # 主页面
    path('', views.index, name='index'),
    
    # API 接口
    path('api/tree/', views.get_tree_data, name='get_tree_data'),
    path('api/add-node/', views.add_node, name='add_node'),
    path('api/update-node/', views.update_node, name='update_node'),
    path('api/delete-node/', views.delete_node, name='delete_node'),
    path('api/upload-document/', views.upload_document, name='upload_document'),
]
