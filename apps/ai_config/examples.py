"""
AI 配置使用示例

展示如何在其他 Django 应用中使用 AI 配置模块

注意：本文件仅作为参考示例，实际使用时需要根据具体情况调整
使用方法：在 Django shell 中运行以下代码片段
      python manage.py shell -c "from apps.ai_config.examples import xxx"
      
前提条件：
1. 确保在 Django 项目根目录下运行（TestBranin 目录）
2. 确保 apps 目录在 Python 路径中
3. 确保已执行数据库迁移：python manage.py migrate ai_config
"""

# ============================================
# 示例 1: 在视图中使用 AI 配置
# ============================================

from django.http import JsonResponse

# 方式 1：直接导入（推荐，适用于在 apps 目录外使用）
try:
    from apps.ai_config.utils import (
        get_global_ai_config,
        get_project_ai_config,
        get_effective_ai_config,
        is_ai_configured
    )
except ImportError:
    # 方式 2：如果在 apps 目录内使用，使用相对导入
    from .utils import (
        get_global_ai_config,
        get_project_ai_config,
        get_effective_ai_config,
        is_ai_configured
    )

def my_llm_view(request):
    """使用全局 AI 配置的视图示例"""
    
    # 检查 LLM 是否已配置
    if not is_ai_configured('llm'):
        return JsonResponse({
            'error': 'LLM 未配置，请先前往 AI 配置页面进行设置'
        })
    
    # 获取全局配置
    config = get_global_ai_config()
    llm_config = config['llm']
    
    # 使用配置调用 LLM API
    # api_base = llm_config['base_url']
    # api_key = llm_config['api_key']
    # model_name = llm_config['model_name']
    
    return JsonResponse({'status': 'success'})


# ============================================
# 示例 2: 在项目级视图中使用 AI 配置
# ============================================

def project_test_case_generator(request, project_id):
    """项目级测试用例生成视图示例"""
    
    # 获取项目实际生效的配置（考虑全局/项目级）
    config = get_effective_ai_config(project_id=project_id)
    
    if not config.get('llm'):
        return JsonResponse({
            'error': '该项目未配置 LLM，请使用全局配置或设置项目级配置'
        })
    
    llm_config = config['llm']
    # 使用配置...
    
    return JsonResponse({'status': 'success'})


# ============================================
# 示例 3: 在 Service 层中使用
# ============================================

class LLMService:
    """LLM 服务类示例"""
    
    def __init__(self, project_id=None):
        """
        初始化 LLM 服务
        
        Args:
            project_id: 项目 ID，如果提供则使用项目级配置
        """
        self.config = get_effective_ai_config(project_id=project_id)
        self.llm_config = self.config.get('llm', {})
    
    def generate_text(self, prompt):
        """生成文本"""
        if not self.llm_config.get('api_key'):
            raise ValueError("LLM API Key 未配置")
        
        # 使用 self.llm_config['api_base'] 等配置调用 API
        pass


# ============================================
# 示例 4: 与原有 settings.py 配置的结合使用
# ============================================

from django.conf import settings as django_settings

# 确保 settings 已加载
if not django_settings.configured:
    import django
    django.setup()

def hybrid_config_example():
    """
    混合配置示例：优先使用数据库配置，回退到 settings.py
    
    Returns:
        dict: 包含 api_key, api_base, model_name 的配置字典
    """
    
    # 尝试从数据库获取配置
    db_config = get_global_ai_config()
    
    if db_config and db_config['llm'].get('api_key'):
        # 使用数据库配置
        return {
            'api_key': db_config['llm']['api_key'],
            'api_base': db_config['llm']['base_url'],
            'model_name': db_config['llm']['model_name']
        }
    else:
        # 回退到 settings.py 配置
        return {
            'api_key': django_settings.LLM_PROVIDERS['deepseek']['api_key'],
            'api_base': django_settings.LLM_PROVIDERS['deepseek']['api_base'],
            'model_name': django_settings.LLM_PROVIDERS['deepseek']['model']
        }


# ============================================
# 示例 5: 在 Celery 任务中使用（需要 Celery 环境）
# ============================================

# 注意：需要先安装并配置 Celery
# from celery import shared_task

# @shared_task
def async_generate_test_cases(project_id, requirements):
    """
    异步生成测试用例任务（同步版本示例）
    
    Args:
        project_id: 项目 ID
        requirements: 需求描述
        
    Returns:
        list: 生成的测试用例列表
    """
    
    # 在 Celery 任务中获取配置
    config = get_effective_ai_config(project_id=project_id)
    
    if not is_ai_configured('llm'):
        raise ValueError("LLM 未配置")
    
    # 使用配置执行任务
    llm_service = LLMService(project_id=project_id)
    # test_cases = llm_service.generate_test_cases(requirements)
    test_cases = []  # 示例占位符
    
    return test_cases


# ============================================
# 示例 6: Vision 模型配置使用
# ============================================

def image_analysis_view(request):
    """图像分析视图示例"""
    
    if not is_ai_configured('vision'):
        return JsonResponse({
            'error': 'Vision 模型未配置'
        })
    
    config = get_global_ai_config()
    vision_config = config['vision']
    
    # 使用 Vision 配置调用多模态 API
    # api_base = vision_config['base_url']
    # api_key = vision_config['api_key']
    # model_name = vision_config['model_name']
    
    return JsonResponse({'status': 'success'})
