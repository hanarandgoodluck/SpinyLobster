# import os
import json
from django.http import JsonResponse
from apps.llm import LLMServiceFactory
from apps.ai_agents.test_case_generator.generator import TestCaseGeneratorAgent
from apps.core.models import TestCase
from apps.utils.logger_manager import get_logger
from django.views.decorators.http import require_http_methods
from django.shortcuts import render
from apps.knowledge.service import get_knowledgeService_instance
from apps.llm.utils import get_agent_llm_configs



logger = get_logger(__name__)

DEFAULT_PROVIDER, PROVIDERS = get_agent_llm_configs("test_case_generator")

# 初始化 knowledge_service，如果 knowledge 应用未启用则设为 None
try:
    from apps.knowledge.service import get_knowledgeService_instance
    knowledge_service = get_knowledgeService_instance()
except (LookupError, ImportError) as e:
    logger.warning(f"无法创建 Knowledge 服务：{e}")
    knowledge_service = None



# @login_required 先屏蔽登录
def generate(request):
    """
    页面 - 测试用例生成页面视图函数
    """
    logger.info("===== 进入 generate 视图函数 =====")
    logger.info(f"请求方法：{request.method}")
    
    # 从数据库获取全局 AI 配置
    llm_model_name = 'deepseek-chat'  # 默认值
    try:
        from apps.ai_config.utils import get_global_ai_config
        
        # 同步方式获取配置
        db_config = get_global_ai_config()
        if db_config and db_config.get('llm'):
            llm_model_name = db_config.get('llm', {}).get('model_name', 'deepseek-chat')
            logger.info(f"从数据库加载 AI 配置成功，模型：{llm_model_name}")
        else:
            logger.info("数据库中没有 AI 配置，使用默认值")
    except Exception as e:
        logger.warning(f"从数据库加载 AI 配置失败：{e}")
        llm_model_name = 'deepseek-chat'
    
    context = {
        'llm_providers': PROVIDERS,
        'llm_provider': DEFAULT_PROVIDER,
        'llm_model_name': llm_model_name,  # 从 AI 配置读取的模型名称
        'requirement': '',
        # 'api_description': '',
        'test_cases': None  # 初始化为 None
    }
    
    if request.method == 'GET':
        return render(request, 'generate.html', context)
    
    # POST 请求参数解析
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        logger.error("JSON解析错误", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': '无效的JSON数据'
        }, status=400)
    
    # 参数获取和验证
    requirements = data.get('requirements', '')
    if not requirements:
        return JsonResponse({
            'success': False,
            'message': '需求描述不能为空'
        })
            
    llm_model_name = data.get('llm_model_name', 'deepseek-chat')  # 从 AI 配置读取的模型名称
    case_design_methods = data.get('case_design_methods', [])  # 获取测试方法
    case_categories = data.get('case_categories', [])         # 获取测试类型
    case_count = int(data.get('case_count', 10))            # 获取生成用例条数
        
    logger.info(f"接收到的数据：{json.dumps(data, ensure_ascii=False)}")
        
    try:
        # 使用工厂创建选定的 LLM 服务
        logger.info(f"使用模型 {llm_model_name} 生成测试用例")
        # 注意：LLMServiceFactory.create 会自动从数据库加载 AI 配置
        llm_service = LLMServiceFactory.create('deepseek')
        
        
        generator_agent = TestCaseGeneratorAgent(llm_service=llm_service, knowledge_service=knowledge_service, case_design_methods=case_design_methods, case_categories=case_categories, case_count=case_count)
        logger.info(f"开始生成测试用例 - 需求: {requirements}...")
        logger.info(f"选择的测试用例设计方法: {case_design_methods}")
        logger.info(f"选择的测试用例类型: {case_categories}")
        logger.info(f"需要生成的用例条数: {case_count}")
        
        # 生成测试用例（同步方式）
        test_cases = generator_agent.generate(requirements, input_type="requirement")

        logger.info(f"测试用例生成成功 - 生成数量：{len(test_cases)}")
                
        return JsonResponse({
            'success': True,
            'test_cases': test_cases
        })
            
    except Exception as e:
        logger.error(f"生成测试用例时出错: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


# @login_required 先屏蔽登录
@require_http_methods(["POST"])
def save_test_case(request):
    """保存测试用例"""
    try:
        data = json.loads(request.body)
        requirement = data.get('requirement')
        test_cases_list = data.get('test_cases', [])
        llm_model_name = data.get('llm_model_name', 'deepseek-chat')
        project_id = data.get('project_id')  # 获取项目 ID
        
        # logger.info(f"接收到的保存请求数据：{json.dumps(data, ensure_ascii=False, indent=2)}")
        
        if not test_cases_list:
            return JsonResponse({
                'success': False,
                'message': '测试用例数据为空'
            }, status=400)
        
        # 准备批量创建的测试用例列表
        test_cases_to_create = []
        
        # 遍历测试用例数据，创建 TestCase 实例
        for index, test_case in enumerate(test_cases_list, 1):
            test_case_instance = TestCase(
                title=f"测试用例-{index}",  # 可以根据需求调整标题格式
                description=test_case.get('description', ''),
                test_steps='\n'.join(test_case.get('test_steps', [])),
                expected_results='\n'.join(test_case.get('expected_results', [])),
                requirements=requirement,
                llm_provider=llm_model_name,  # 使用模型名称作为 provider
                status='pending'  # 默认状态为待评审
                # created_by=request.user  # 如果需要记录创建用户，取消注释此行
            )
            
            # 如果提供了项目 ID，则关联到对应项目
            if project_id:
                from apps.core.models import Project
                project = Project.objects.filter(id=project_id).first()
                if project:
                    test_case_instance.project = project
            
            test_cases_to_create.append(test_case_instance)
        
        # 批量创建测试用例
        created_test_cases = TestCase.objects.bulk_create(test_cases_to_create)
        
        logger.info(f"成功保存 {len(created_test_cases)} 条测试用例")
        
        return JsonResponse({
            'success': True,
            'message': f'成功保存 {len(created_test_cases)} 条测试用例',
            'test_case_id': [case.id for case in created_test_cases]
        })
        
    except json.JSONDecodeError:
        logger.error("JSON 解析错误", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': '无效的 JSON 数据'
        }, status=400)
    except Exception as e:
        logger.error(f"保存测试用例时出错：{str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'保存失败：{str(e)}'
        }, status=500)