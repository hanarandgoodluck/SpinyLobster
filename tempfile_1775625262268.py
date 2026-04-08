# @login_required 先屏蔽登录
@require_http_methods(["POST"])
def save_test_case(request):
    """保存测试用例"""
    from django.db import transaction
    
    try:
        data = json.loads(request.body)
        requirement = data.get('requirement')
        test_cases_list = data.get('test_cases', [])
        llm_model_name = data.get('llm_model_name', 'deepseek-chat')
        project_id = data.get('project_id')
        
        logger.info(f"接收到保存请求 - 用例数量: {len(test_cases_list)}, 项目ID: {project_id}")
        
        if not test_cases_list:
            return JsonResponse({
                'success': False,
                'message': '测试用例数据为空'
            }, status=400)
        
        # 验证项目是否存在（如果提供了project_id）
        project = None
        if project_id:
            from apps.core.models import Project
            project = Project.objects.filter(id=project_id).first()
            if not project:
                logger.warning(f"项目ID {project_id} 不存在，将不关联项目")
        
        # 准备批量创建的测试用例列表
        test_cases_to_create = []
        
        for index, test_case in enumerate(test_cases_list, 1):
            test_steps = test_case.get('test_steps', [])
            expected_results = test_case.get('expected_results', [])
            
            test_case_instance = TestCase(
                title=f"测试用例-{index}",
                description=test_case.get('description', ''),
                test_steps='\n'.join(test_steps) if isinstance(test_steps, list) else test_steps,
                expected_results='\n'.join(expected_results) if isinstance(expected_results, list) else expected_results,
                requirements=requirement,
                llm_provider=llm_model_name,
                status='pending',
                project=project
            )
            
            test_cases_to_create.append(test_case_instance)
        
        # 使用事务批量创建，确保数据一致性
        with transaction.atomic():
            created_test_cases = TestCase.objects.bulk_create(test_cases_to_create)
            
            # 重新查询获取完整的对象（包括自动生成的ID）
            if created_test_cases:
                # 根据描述和要求获取刚创建的用例
                created_ids = list(
                    TestCase.objects.filter(
                        requirements=requirement,
                        status='pending'
                    ).order_by('-id').values_list('id', flat=True)[:len(created_test_cases)]
                )
                created_ids.reverse()
                
                logger.info(f"成功保存 {len(created_test_cases)} 条测试用例，ID列表: {created_ids}")
            else:
                created_ids = []
                logger.warning("没有创建任何测试用例")
        
        return JsonResponse({
            'success': True,
            'message': f'成功保存 {len(created_test_cases)} 条测试用例',
            'test_case_id': created_ids,
            'count': len(created_test_cases)
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
