"""
AI 配置工具模块
提供从数据库加载 AI 配置的辅助函数
"""

from typing import Dict, Optional, Any
from apps.ai_config.models import AIConfig


def get_global_ai_config() -> Optional[Dict[str, Any]]:
    """
    从数据库获取全局 AI 配置
    
    Returns:
        dict: 包含 LLM 和 Vision 配置的字典，如果不存在则返回 None
        {
            'llm': {
                'base_url': '...',
                'api_key': '...',
                'model_name': '...'
            },
            'vision': {
                'base_url': '...',
                'api_key': '...',
                'model_name': '...'
            }
        }
    """
    config = AIConfig.objects.filter(config_type='global').first()
    if not config:
        return None
    
    return {
        'llm': {
            'base_url': config.llm_base_url or '',
            'api_key': config.llm_api_key or '',
            'model_name': config.llm_model_name or ''
        },
        'vision': {
            'base_url': config.vision_base_url or '',
            'api_key': config.vision_api_key or '',
            'model_name': config.vision_model_name or ''
        }
    }


def get_project_ai_config(project_id: int) -> Optional[Dict[str, Any]]:
    """
    从数据库获取项目 AI 配置
    
    Args:
        project_id: 项目 ID
        
    Returns:
        dict: 包含项目配置和使用全局开关的字典，如果不存在则返回 None
        {
            'use_global': True/False,
            'llm': {...},
            'vision': {...}
        }
    """
    config = AIConfig.objects.filter(
        config_type='project', 
        project_id=project_id
    ).first()
    
    if not config:
        return None
    
    return {
        'use_global': config.use_global,
        'llm': {
            'base_url': config.llm_base_url or '',
            'api_key': config.llm_api_key or '',
            'model_name': config.llm_model_name or ''
        },
        'vision': {
            'base_url': config.vision_base_url or '',
            'api_key': config.vision_api_key or '',
            'model_name': config.vision_model_name or ''
        }
    }


def get_effective_ai_config(project_id: Optional[int] = None) -> Dict[str, Any]:
    """
    获取实际生效的 AI 配置（考虑全局和项目级）
    
    Args:
        project_id: 项目 ID，如果为 None 则返回全局配置
        
    Returns:
        dict: 实际生效的配置
    """
    # 如果没有项目 ID，返回全局配置
    if project_id is None:
        return get_global_ai_config() or {}
    
    # 尝试获取项目配置
    project_config = get_project_ai_config(project_id)
    
    # 如果项目配置不存在或不使用全局配置，返回项目配置
    if project_config and not project_config['use_global']:
        return {
            'llm': project_config['llm'],
            'vision': project_config['vision']
        }
    
    # 否则返回全局配置
    return get_global_ai_config() or {}


def is_ai_configured(model_type: str = 'llm') -> bool:
    """
    检查 AI 模型是否已配置
    
    Args:
        model_type: 'llm' 或 'vision'
        
    Returns:
        bool: 是否已配置
    """
    config = get_global_ai_config()
    if not config:
        return False
    
    model_config = config.get(model_type, {})
    return bool(
        model_config.get('base_url') and 
        model_config.get('api_key') and 
        model_config.get('model_name')
    )
