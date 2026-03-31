"""
URL configuration for test_brain project.
"""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.core.urls')),
    # AI 模型配置
    path('ai_config/', include('apps.ai_config.urls')),
    # metersphere 上接口测试用例生成路由
    path('iface_case_generator/', include('apps.ai_agents.iface_case_generator.urls')),
    path('java_code_analyzer/', include('apps.ai_agents.java_code_analyzer.urls')),
    path('prd_analyzer/', include('apps.ai_agents.prd_analyzer.urls')),
    path('test_case_generator/', include('apps.ai_agents.test_case_generator.urls')),
    path('test_case_reviewer/', include('apps.ai_agents.test_case_reviewer.urls')),
    path('case_library/', include('apps.ai_agents.case_library.urls')),

]