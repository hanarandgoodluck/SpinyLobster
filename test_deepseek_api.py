#!/usr/bin/env python
"""
测试 DeepSeek API 配置是否正确
"""
import os
import sys
import django

# 设置 Django 环境
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.llm import LLMServiceFactory
from apps.llm.utils import get_agent_llm_configs
from django.conf import settings

def test_deepseek_api():
    """测试 DeepSeek API 是否可用"""
    print("=" * 60)
    print("开始测试 DeepSeek API 配置...")
    print("=" * 60)
    
    # 1. 检查配置文件中的 API key
    llm_config = getattr(settings, 'LLM_PROVIDERS', {})
    deepseek_config = llm_config.get('deepseek', {})
    api_key = deepseek_config.get('api_key')
    
    print(f"\n1. 检查配置文件:")
    print(f"   - API Key: {api_key[:20]}...{api_key[-10:] if api_key else 'None'}")
    print(f"   - Model: {deepseek_config.get('model', 'Not set')}")
    print(f"   - API Base: {deepseek_config.get('api_base', 'Not set')}")
    
    if not api_key:
        print("\n❌ 错误：配置文件中未找到 API Key")
        return False
    
    # 2. 尝试创建 LLM 服务实例
    print(f"\n2. 创建 DeepSeek LLM 服务实例...")
    try:
        llm_service = LLMServiceFactory.create(
            provider='deepseek',
            **deepseek_config
        )
        print(f"   ✅ LLM 服务实例创建成功!")
        print(f"   - 类型：{type(llm_service)}")
    except Exception as e:
        print(f"   ❌ LLM 服务实例创建失败：{str(e)}")
        return False
    
    # 3. 测试调用 API
    print(f"\n3. 测试调用 DeepSeek API...")
    try:
        from langchain_core.messages import HumanMessage
        
        messages = [
            HumanMessage(content="你好，请用一句话介绍你自己。")
        ]
        
        print(f"   - 发送消息：你好，请用一句话介绍你自己。")
        print(f"   - 正在调用 API...")
        
        response = llm_service.invoke(messages)
        
        print(f"\n   ✅ API 调用成功!")
        print(f"   - 响应内容：{response.content}")
        print(f"\n{'=' * 60}")
        print("🎉 测试完成 - DeepSeek API 配置正确且可用!")
        print(f"{'=' * 60}")
        return True
        
    except Exception as e:
        print(f"\n   ❌ API 调用失败：{str(e)}")
        print(f"\n{'=' * 60}")
        print("⚠️  测试完成 - API Key 配置成功但调用失败")
        print(f"   可能原因：网络连接问题、API Key 无效或额度不足")
        print(f"{'=' * 60}")
        return False

if __name__ == "__main__":
    success = test_deepseek_api()
    sys.exit(0 if success else 1)
