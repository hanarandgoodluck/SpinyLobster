from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
import json
import requests
from .models import AIConfig
from apps.core.models import Project


def ai_config_view(request):
    """AI 配置页面"""
    return render(request, 'ai_config/ai_config_fixed.html')


@csrf_exempt
def get_global_config(request):
    """获取全局配置"""
    try:
        config = AIConfig.objects.filter(config_type='global').first()
        if not config:
            # 创建默认全局配置
            config = AIConfig.objects.create(config_type='global')
        
        return JsonResponse({
            'success': True,
            'config': config.to_dict()
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@csrf_exempt
def save_global_config(request):
    """保存全局配置"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '方法不允许'}, status=405)
    
    try:
        data = json.loads(request.body)
        
        # 获取或创建全局配置
        config = AIConfig.objects.filter(config_type='global').first()
        if not config:
            config = AIConfig.objects.create(config_type='global')
        
        # 更新 LLM 配置
        llm_data = data.get('llm', {})
        config.llm_base_url = llm_data.get('base_url', '')
        config.llm_api_key = llm_data.get('api_key', '')
        config.llm_model_name = llm_data.get('model_name', '')
        
        # 更新 Vision 配置
        vision_data = data.get('vision', {})
        config.vision_base_url = vision_data.get('base_url', '')
        config.vision_api_key = vision_data.get('api_key', '')
        config.vision_model_name = vision_data.get('model_name', '')
        
        config.save()
        
        return JsonResponse({
            'success': True,
            'message': '全局配置已保存',
            'config': config.to_dict()
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'保存失败：{str(e)}'
        }, status=500)


@csrf_exempt
def get_project_config(request, project_id):
    """获取项目配置"""
    try:
        project = Project.objects.get(id=project_id)
        config = AIConfig.objects.filter(config_type='project', project=project).first()
        
        if not config:
            # 创建默认项目配置（使用全局设置）
            config = AIConfig.objects.create(
                config_type='project',
                project=project,
                use_global=True
            )
        
        return JsonResponse({
            'success': True,
            'config': config.to_dict()
        })
    except Project.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '项目不存在'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@csrf_exempt
def save_project_config(request, project_id):
    """保存项目配置"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '方法不允许'}, status=405)
    
    try:
        project = Project.objects.get(id=project_id)
        data = json.loads(request.body)
        
        # 获取或创建项目配置
        config = AIConfig.objects.filter(config_type='project', project=project).first()
        if not config:
            config = AIConfig.objects.create(
                config_type='project',
                project=project,
                use_global=data.get('use_global', True)
            )
        
        # 更新配置
        config.use_global = data.get('use_global', True)
        
        # 只有当不使用全局配置时才保存项目级配置
        if not config.use_global:
            llm_data = data.get('llm', {})
            config.llm_base_url = llm_data.get('base_url', '')
            config.llm_api_key = llm_data.get('api_key', '')
            config.llm_model_name = llm_data.get('model_name', '')
            
            vision_data = data.get('vision', {})
            config.vision_base_url = vision_data.get('base_url', '')
            config.vision_api_key = vision_data.get('api_key', '')
            config.vision_model_name = vision_data.get('model_name', '')
        else:
            # 如果使用全局配置，清空项目级配置
            config.llm_base_url = ''
            config.llm_api_key = ''
            config.llm_model_name = ''
            config.vision_base_url = ''
            config.vision_api_key = ''
            config.vision_model_name = ''
        
        config.save()
        
        return JsonResponse({
            'success': True,
            'message': '项目配置已保存',
            'config': config.to_dict()
        })
    except Project.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '项目不存在'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'保存失败：{str(e)}'
        }, status=500)


@csrf_exempt
def test_connection(request):
    """测试 API 连接"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '方法不允许'}, status=405)
    
    try:
        data = json.loads(request.body)
        base_url = data.get('base_url', '').strip()
        api_key = data.get('api_key', '').strip()
        model_type = data.get('model_type', 'llm')  # 'llm' or 'vision'
        
        if not base_url:
            return JsonResponse({
                'success': False,
                'message': 'API Base URL 不能为空'
            })
        
        # 标准化 base_url（移除末尾的斜杠）
        base_url = base_url.rstrip('/')
        
        # 尝试获取模型列表或发送简单请求
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        # 首先尝试 /v1/models 端点
        models_url = f'{base_url}/v1/models'
        try:
            response = requests.get(models_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                return JsonResponse({
                    'success': True,
                    'message': f'{model_type.upper()} 连接成功！',
                    'details': 'API 响应正常，已获取模型列表'
                })
            elif response.status_code in [401, 403]:
                return JsonResponse({
                    'success': False,
                    'message': '认证失败：API Key 无效或已过期'
                })
            elif response.status_code == 404:
                # 尝试备用端点 /chat/completions
                return test_completion_endpoint(base_url, api_key, model_type)
            else:
                return JsonResponse({
                    'success': False,
                    'message': f'连接失败：HTTP {response.status_code}'
                })
        except requests.exceptions.Timeout:
            return JsonResponse({
                'success': False,
                'message': '连接超时：请检查网络或 API 地址'
            })
        except requests.exceptions.ConnectionError:
            return JsonResponse({
                'success': False,
                'message': '无法连接：API 地址错误或网络不可达'
            })
        except Exception as e:
            # 尝试备用端点
            return test_completion_endpoint(base_url, api_key, model_type)
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '无效的请求数据'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'测试失败：{str(e)}'
        }, status=500)


def test_completion_endpoint(base_url, api_key, model_type):
    """测试 completion 端点"""
    try:
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        # DeepSeek 等大多数 API 都支持 /v1/chat/completions 端点
        url = f'{base_url}/v1/chat/completions'
        test_data = {
            'model': 'deepseek-chat',  # 使用 DeepSeek 默认模型
            'messages': [{'role': 'user', 'content': 'Hello'}],
            'max_tokens': 1
        }
        
        response = requests.post(url, json=test_data, headers=headers, timeout=10)
        
        if response.status_code in [200, 400]:
            # 200: 成功，400: 可能是模型名不对，但证明连接和认证没问题
            return JsonResponse({
                'success': True,
                'message': f'{model_type.upper()} 连接成功！',
                'details': 'API 端点可访问，认证通过'
            })
        elif response.status_code in [401, 403]:
            return JsonResponse({
                'success': False,
                'message': '认证失败：API Key 无效或已过期'
            })
        elif response.status_code == 404:
            return JsonResponse({
                'success': False,
                'message': 'API 端点不存在：请检查 Base URL 是否正确'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': f'连接测试失败：HTTP {response.status_code}'
            })
    except requests.exceptions.Timeout:
        return JsonResponse({
            'success': False,
            'message': '连接超时：请检查网络或 API 地址'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'测试失败：{str(e)}'
        })