from django.db import models
import json


class AIConfig(models.Model):
    """AI 模型配置模型 - 支持全局和项目级配置"""
    
    CONFIG_TYPE_CHOICES = [
        ('global', '全局配置'),
        ('project', '项目配置'),
    ]
    
    config_type = models.CharField(
        max_length=10,
        choices=CONFIG_TYPE_CHOICES,
        default='global',
        verbose_name="配置类型"
    )
    
    # 关联项目（仅项目级配置需要）
    project = models.ForeignKey(
        'core.Project',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='ai_configs',
        verbose_name="关联项目"
    )
    
    # LLM 配置
    llm_base_url = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name="LLM API Base URL"
    )
    llm_api_key = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name="LLM API Key"
    )
    llm_model_name = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        verbose_name="LLM Model Name"
    )
    
    # Vision 配置
    vision_base_url = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name="Vision API Base URL"
    )
    vision_api_key = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name="Vision API Key"
    )
    vision_model_name = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        verbose_name="Vision Model Name"
    )
    
    # 项目级配置特有字段
    use_global = models.BooleanField(
        default=True,
        verbose_name="使用全局配置"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="创建时间"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="更新时间"
    )
    
    class Meta:
        verbose_name = "AI 模型配置"
        verbose_name_plural = "AI 模型配置"
        unique_together = ['config_type', 'project']
    
    def __str__(self):
        if self.config_type == 'global':
            return "全局 AI 配置"
        else:
            return f"项目 {self.project.name} 的 AI 配置"
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'config_type': self.config_type,
            'use_global': self.use_global,
            'llm': {
                'base_url': self.llm_base_url or '',
                'api_key': self.llm_api_key or '',
                'model_name': self.llm_model_name or ''
            },
            'vision': {
                'base_url': self.vision_base_url or '',
                'api_key': self.vision_api_key or '',
                'model_name': self.vision_model_name or ''
            },
            'updated_at': str(self.updated_at)
        }
