from django.urls import path
from . import views

app_name = 'case_library'

urlpatterns = [
    # 页面路由
    path('', views.case_library_page, name='case_library_page'),
    
    # API 路由
    path('api/list/', views.case_library_list, name='case_library_list'),
    path('api/create/', views.create_case, name='create_case'),
    path('api/update/', views.update_case, name='update_case'),
    path('api/delete/', views.delete_case, name='delete_case'),
    path('api/modules/', views.get_modules, name='get_modules'),
    path('api/modules/create/', views.create_module, name='create_module'),
    path('api/modules/<int:module_id>/update/', views.update_module, name='update_module'),
    path('api/modules/<int:module_id>/delete/', views.delete_module, name='delete_module'),
]
