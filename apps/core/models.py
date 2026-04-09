from django.db import models
from django.contrib.auth.models import User

class Project(models.Model):
    """项目模型"""
    name = models.CharField(max_length=200, verbose_name="项目名称")
    version = models.CharField(max_length=50, verbose_name="项目版本")
    description = models.TextField(blank=True, verbose_name="项目描述")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    def __str__(self):
        return f"{self.name} (v{self.version})"
    
    class Meta:
        verbose_name = "项目"
        verbose_name_plural = "项目"
        ordering = ['-created_at']

class TestCase(models.Model):
    """测试用例模型"""
    STATUS_CHOICES = [
        ('pending', '待评审'),
        ('approved', '评审通过'),
        ('rejected', '评审未通过'),
    ]

    BU_CHOICES = [
        ('education', '教育'),
        ('user_center', '用户中心'),
        ('collaboration', '协同'),
        ('im', 'IM'),
        ('workspace', '工作台'),
        ('recruitment', '招聘'),
        ('work_management', '工作管理'),
        ('ai_application', 'AI 应用'),
        ('operation_platform', '运营平台'),
    ]
    
    PRIORITY_CHOICES = [
        ('p0', 'P0'),
        ('p1', 'P1'),
        ('p2', 'P2'),
        ('p3', 'P3'),
    ]
    
    title = models.CharField(max_length=200, verbose_name="测试用例标题")
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='test_cases',
        verbose_name="所属项目",
        null=True,
        blank=True
    )
    description = models.TextField(verbose_name="测试用例描述")
    requirements = models.TextField(verbose_name="需求描述", blank=True)
    code_snippet = models.TextField(verbose_name="代码片段", blank=True)
    test_steps = models.TextField(verbose_name="测试步骤")
    expected_results = models.TextField(verbose_name="预期结果")
    actual_results = models.TextField(verbose_name="实际结果", blank=True)
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending',
        verbose_name="评审状态"
    )
    created_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='created_testcases',
        verbose_name="创建者",
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    llm_provider = models.CharField(max_length=50, null=True, blank=True)
    bu = models.CharField(max_length=50, choices=BU_CHOICES, blank=True, verbose_name='BU')
    feature = models.CharField(max_length=100, blank=True, verbose_name='Feature')
    priority = models.CharField(max_length=2, choices=PRIORITY_CHOICES, blank=True, verbose_name='Priority')
    
    def __str__(self):
        return (
            f"用例描述：\n{self.description}\n\n"
            f"测试步骤：\n{self.test_steps}\n\n"
            f"预期结果：\n{self.expected_results}\n"
        )
    
    class Meta:
        verbose_name = "测试用例"
        verbose_name_plural = "测试用例"

class TestCaseReview(models.Model):
    """测试用例评审记录"""
    test_case = models.ForeignKey(
        TestCase, 
        on_delete=models.CASCADE, 
        related_name='reviews',
        verbose_name="测试用例"
    )
    reviewer = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='reviews',
        verbose_name="评审人"
    )
    review_comments = models.TextField(verbose_name="评审意见")
    review_date = models.DateTimeField(auto_now_add=True, verbose_name="评审时间")
    
    def __str__(self):
        return f"Review for {self.test_case.title}"
    
    class Meta:
        verbose_name = "测试用例评审"
        verbose_name_plural = "测试用例评审"

class KnowledgeBase(models.Model):
    """知识库条目"""
    title = models.CharField(max_length=200, verbose_name="知识条目标题")
    content = models.TextField(verbose_name="知识内容")
    vector_id = models.CharField(max_length=100, blank=True, verbose_name="向量 ID")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    def __str__(self):
        return self.title
    
    class Meta:
        verbose_name = "知识库"
        verbose_name_plural = "知识库"


class TestCaseLibrary(models.Model):
    """用例库模型"""
    STATUS_CHOICES = [
        ('active', '启用'),
        ('inactive', '停用'),
    ]
    
    PRIORITY_CHOICES = [
        ('p0', 'P0'),
        ('p1', 'P1'),
        ('p2', 'P2'),
        ('p3', 'P3'),
    ]
    
    TYPE_CHOICES = [
        ('functional', '功能测试'),
        ('performance', '性能测试'),
        ('compatibility', '兼容性测试'),
        ('security', '安全性测试'),
        ('ui', 'UI 测试'),
        ('api', '接口测试'),
    ]
    
    MODULE_CHOICES = [
        ('user_center', '用户中心'),
        ('education', '教育'),
        ('collaboration', '协同'),
        ('im', 'IM'),
        ('workspace', '工作台'),
        ('recruitment', '招聘'),
        ('work_management', '工作管理'),
        ('ai_application', 'AI 应用'),
        ('operation_platform', '运营平台'),
        ('other', '其他'),
    ]
    
    case_number = models.CharField(max_length=50, unique=True, verbose_name="用例编号")
    title = models.CharField(max_length=500, verbose_name="标题")
    module = models.CharField(max_length=50, choices=MODULE_CHOICES, default='other', verbose_name='模块')
    priority = models.CharField(max_length=2, choices=PRIORITY_CHOICES, default='p2', verbose_name='优先级')
    case_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='functional', verbose_name='用例类型')
    preconditions = models.TextField(blank=True, verbose_name='前置条件')
    test_steps = models.TextField(verbose_name='测试步骤')
    expected_results = models.TextField(verbose_name='预期结果')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name='状态')
    maintainer = models.CharField(max_length=100, blank=True, verbose_name='维护人')
    project = models.ForeignKey(
        Project,
        on_delete=models.SET_NULL,
        related_name='case_library',
        verbose_name="所属项目",
        null=True,
        blank=True
    )
    tags = models.CharField(max_length=500, blank=True, verbose_name='标签，多个标签用逗号分隔')
    remark = models.TextField(blank=True, verbose_name='备注')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    def __str__(self):
        return f"{self.case_number} - {self.title}"
    
    class Meta:
        verbose_name = "用例库"
        verbose_name_plural = "用例库"
        ordering = ['-case_number']


class TestCaseModule(models.Model):
    """用例模块模型"""
    name = models.CharField(max_length=100, verbose_name="模块名称")
    value = models.CharField(max_length=100, unique=True, verbose_name="模块标识")
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        related_name='children',
        verbose_name="父模块",
        null=True,
        blank=True
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='case_modules',
        verbose_name="所属项目",
        null=True,
        blank=True
    )
    order = models.IntegerField(default=0, verbose_name="排序")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "用例模块"
        verbose_name_plural = "用例模块"
        ordering = ['order', 'name']


class AutomationExecutionLog(models.Model):
    """自动化测试执行日志模型"""
    STATUS_CHOICES = [
        ('pending', '等待中'),
        ('running', '执行中'),
        ('passed', '通过'),
        ('failed', '失败'),
        ('error', '错误'),
    ]
    
    EXECUTION_MODE_CHOICES = [
        ('single', '单用例执行'),
        ('batch', '批量执行'),
    ]
    
    BROWSER_CHOICES = [
        ('chromium', 'Chrome'),
        ('firefox', 'Firefox'),
        ('webkit', 'Safari'),
    ]
    
    # 关联用例
    case = models.ForeignKey(
        TestCaseLibrary,
        on_delete=models.CASCADE,
        related_name='execution_logs',
        verbose_name="关联用例",
        null=True,
        blank=True
    )
    
    # 任务标识
    task_uuid = models.CharField(max_length=100, unique=True, verbose_name="任务UUID")
    
    # 执行状态
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="执行状态"
    )
    
    # 执行模式
    execution_mode = models.CharField(
        max_length=20,
        choices=EXECUTION_MODE_CHOICES,
        default='single',
        verbose_name="执行模式"
    )
    
    # 浏览器配置
    browser = models.CharField(
        max_length=20,
        choices=BROWSER_CHOICES,
        default='chromium',
        verbose_name="浏览器类型"
    )
    
    headless = models.BooleanField(default=True, verbose_name="无头模式")
    
    # AI决策日志
    ai_decision_log = models.TextField(blank=True, verbose_name="AI决策日志")
    use_multimodal = models.BooleanField(default=False, verbose_name="是否使用多模态")
    multimodal_reason = models.TextField(blank=True, verbose_name="多模态使用原因")
    
    # Playwright脚本路径
    script_path = models.CharField(max_length=500, blank=True, verbose_name="脚本路径")
    
    # 报告信息
    report_url = models.CharField(max_length=500, blank=True, verbose_name="Allure报告URL")
    allure_report_path = models.CharField(max_length=500, blank=True, verbose_name="Allure报告路径")
    
    # 执行结果
    error_message = models.TextField(blank=True, verbose_name="错误信息")
    execution_time = models.FloatField(null=True, blank=True, verbose_name="执行时长(秒)")
    
    # 时间戳
    started_at = models.DateTimeField(null=True, blank=True, verbose_name="开始时间")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="完成时间")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    def __str__(self):
        return f"{self.task_uuid} - {self.get_status_display()}"
    
    class Meta:
        verbose_name = "自动化执行日志"
        verbose_name_plural = "自动化执行日志"
        ordering = ['-created_at']