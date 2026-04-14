"""
AI 智能模块映射服务 - 基于语义相似度自动匹配需求到模块
"""
import logging
from typing import List, Dict, Optional, Tuple
from django.conf import settings

logger = logging.getLogger(__name__)


class ModuleMapper:
    """模块映射器 - 使用 AI 进行需求与模块的语义匹配"""
    
    def __init__(self):
        self.llm_service = None
        self._init_llm_service()
    
    def _init_llm_service(self):
        """初始化 LLM 服务"""
        try:
            from apps.llm import LLMServiceFactory
            # 使用默认 provider
            provider = getattr(settings, 'LLM_PROVIDERS', {}).get('default_provider', 'deepseek')
            self.llm_service = LLMServiceFactory.create(provider)
            logger.info(f"LLM 服务初始化成功: {provider}")
        except Exception as e:
            logger.error(f"LLM 服务初始化失败: {str(e)}", exc_info=True)
            raise
    
    def build_module_tree_text(self, modules: List[Dict]) -> str:
        """
        将模块树转换为文本格式，用于 AI 理解
        
        Args:
            modules: 模块树列表，格式如 [{'name': '用户中心', 'value': 'user_center', 'children': [...]}]
        
        Returns:
            结构化的模块树文本
        """
        def _format_module(module, level=0):
            indent = "  " * level
            text = f"{indent}- {module['name']} (标识: {module['value']})\n"
            
            if module.get('children'):
                for child in module['children']:
                    text += _format_module(child, level + 1)
            
            return text
        
        result = ""
        for module in modules:
            result += _format_module(module)
        
        return result
    
    def map_requirement_to_module(
        self, 
        requirement_text: str, 
        modules: List[Dict]
    ) -> Tuple[Optional[str], float, str]:
        """
        将需求文本映射到最匹配的模块
        
        Args:
            requirement_text: 需求文本内容
            modules: 可用的模块树列表
        
        Returns:
            (模块value, 置信度分数 0-1, 匹配置信度等级 'high'/'medium'/'low')
        """
        if not modules:
            logger.warning("模块列表为空，无法进行映射")
            return None, 0.0, 'low'
        
        try:
            # 构建模块树文本
            module_tree_text = self.build_module_tree_text(modules)
            
            # 构建 Prompt
            prompt = f"""你是一个专业的需求分析专家。请分析以下需求内容，并将其归类到给定的模块树中。

## 需求内容
{requirement_text}

## 可用模块树
{module_tree_text}

## 任务要求
1. 仔细理解需求内容的核心功能点
2. 从模块树中选择**最匹配**的一个模块（必须是叶子节点或具体模块）
3. 返回该模块的标识（value字段）
4. 评估匹配的置信度（0-1之间的小数）

## 输出格式
请严格按照以下 JSON 格式返回结果：
{{
    "module_value": "模块的value值",
    "confidence_score": 0.85,
    "reason": "简要说明选择该模块的原因"
}}

注意：
- 只返回 JSON，不要有其他文字
- confidence_score 范围是 0.0 到 1.0
- 如果需求内容与任何模块都不相关，module_value 返回 null，confidence_score 返回 0.0
"""
            
            # 调用 LLM
            messages = [
                {"role": "system", "content": "你是一个专业的需求分析和分类专家。"},
                {"role": "user", "content": prompt}
            ]
            
            response = self.llm_service.invoke(messages)
            result_text = response.content if hasattr(response, 'content') else str(response)
            
            logger.debug(f"LLM 原始响应: {result_text}")
            
            # 解析 JSON 响应
            import json
            import re
            
            # 尝试提取 JSON
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                result = json.loads(json_str)
                
                module_value = result.get('module_value')
                confidence_score = float(result.get('confidence_score', 0.0))
                reason = result.get('reason', '')
                
                # 确定置信度等级
                if confidence_score >= 0.8:
                    confidence_level = 'high'
                elif confidence_score >= 0.6:
                    confidence_level = 'medium'
                else:
                    confidence_level = 'low'
                
                logger.info(
                    f"需求映射完成 - 模块: {module_value}, "
                    f"置信度: {confidence_score:.2f} ({confidence_level}), "
                    f"原因: {reason}"
                )
                
                return module_value, confidence_score, confidence_level
            else:
                logger.warning(f"无法从 LLM 响应中提取 JSON: {result_text}")
                return None, 0.0, 'low'
                
        except Exception as e:
            logger.error(f"模块映射失败: {str(e)}", exc_info=True)
            return None, 0.0, 'low'
    
    def batch_map_requirements(
        self, 
        requirements: List[str], 
        modules: List[Dict]
    ) -> List[Tuple[Optional[str], float, str]]:
        """
        批量映射需求到模块
        
        Args:
            requirements: 需求文本列表
            modules: 可用的模块树列表
        
        Returns:
            映射结果列表，每个元素为 (module_value, confidence_score, confidence_level)
        """
        results = []
        total = len(requirements)
        
        for idx, req_text in enumerate(requirements, 1):
            logger.info(f"正在映射第 {idx}/{total} 个需求...")
            result = self.map_requirement_to_module(req_text, modules)
            results.append(result)
        
        return results


# 全局实例
module_mapper = ModuleMapper()
