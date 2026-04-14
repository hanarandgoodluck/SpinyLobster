from django.db import models
from apps.core.models import Project


class RequirementDoc(models.Model):
    """原始需求文档模型"""
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='requirement_docs',
        verbose_name="所属项目"
    )
    filename = models.CharField(max_length=255, verbose_name="文件名")
    file_path = models.CharField(max_length=500, verbose_name="文件路径")
    file_type = models.CharField(
        max_length=20,
        choices=[
            ('docx', 'Word文档'),
            ('pdf', 'PDF文档'),
            ('md', 'Markdown'),
            ('txt', '文本文件'),
            ('xlsx', 'Excel表格'),
        ],
        verbose_name="文件类型"
    )
    file_size = models.IntegerField(verbose_name="文件大小(字节)")
    upload_time = models.DateTimeField(auto_now_add=True, verbose_name="上传时间")
    uploaded_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="上传人"
    )
    
    def __str__(self):
        return self.filename
    
    class Meta:
        verbose_name = "需求文档"
        verbose_name_plural = "需求文档"
        ordering = ['-upload_time']


class RequirementNode(models.Model):
    """需求节点模型 - 支持树形结构（文件夹和需求项）"""
    NODE_TYPE_CHOICES = [
        ('folder', '文件夹'),
        ('requirement', '需求项'),
    ]
    
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='requirement_nodes',
        verbose_name="所属项目"
    )
    
    # 父节点（支持树形结构）
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name="父节点"
    )
    
    # 节点类型
    node_type = models.CharField(
        max_length=20,
        choices=NODE_TYPE_CHOICES,
        default='folder',
        verbose_name="节点类型"
    )
    
    # 节点名称
    name = models.CharField(max_length=255, verbose_name="节点名称")
    
    # 排序
    order = models.IntegerField(default=0, verbose_name="排序")
    
    # 需求项内容（仅当 node_type='requirement' 时有效）
    content = models.TextField(blank=True, default='', verbose_name="需求内容")
    
    # 关联的原始文档
    source_doc = models.ForeignKey(
        RequirementDoc,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='nodes',
        verbose_name="来源文档"
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    def __str__(self):
        return f"{self.name} ({self.get_node_type_display()})"
    
    class Meta:
        verbose_name = "需求节点"
        verbose_name_plural = "需求节点"
        ordering = ['order', '-created_at']
        indexes = [
            models.Index(fields=['project', 'node_type']),
            models.Index(fields=['project', 'parent']),
        ]
