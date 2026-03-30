"""
自定义上下文处理器 - 为所有模板提供当前选中的项目信息
"""
from apps.core.models import Project


def current_project(request):
    """
    获取当前选中的项目并传递给所有模板
    
    通过 URL 查询参数 project_id 来识别当前项目
    例如：/test_case_generator/?project_id=1
    """
    project_id = request.GET.get('project_id')
    
    if project_id:
        try:
            project = Project.objects.get(id=project_id)
            return {'current_project': project}
        except Project.DoesNotExist:
            pass
    
    # 如果没有 project_id 或项目不存在，返回 None
    return {'current_project': None}
