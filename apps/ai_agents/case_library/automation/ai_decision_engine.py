"""
AI决策引擎 - 分析测试用例并决定是否需要多模态能力

核心功能：
1. 接收自然语言描述的测试用例步骤
2. 使用LLM分析是否需要视觉验证（多模态）
3. 生成Playwright执行指令
4. 返回结构化JSON决策结果
"""

import json
import logging
from typing import Dict, Any, Optional, List
from apps.llm.utils import get_agent_llm_configs
from apps.llm.base import LLMServiceFactory
from apps.utils.logger_manager import get_logger

logger = get_logger(__name__)


class AIDecisionEngine:
    """AI决策引擎 - 分析测试用例并生成执行策略"""
    
    def __init__(self, llm_provider: str = 'deepseek'):
        """
        初始化AI决策引擎
        
        Args:
            llm_provider: LLM提供商名称
        """
        self.llm_provider = llm_provider
        try:
            # 获取LLM配置
            DEFAULT_PROVIDER, PROVIDERS = get_agent_llm_configs("case_library")
            provider_config = PROVIDERS.get(llm_provider, PROVIDERS.get(DEFAULT_PROVIDER))
            
            if not provider_config:
                raise ValueError(f"未找到LLM提供商配置: {llm_provider}")
            
            # 创建LLM服务实例
            self.llm_service = LLMServiceFactory.create(
                provider=llm_provider,
                **provider_config
            )
            logger.info(f"AI决策引擎初始化成功，使用LLM: {llm_provider}")
        except Exception as e:
            logger.error(f"AI决策引擎初始化失败: {e}")
            raise
    
    def analyze_test_case(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析单个测试用例，生成执行决策
        
        Args:
            test_case: 测试用例字典，包含title, test_steps, expected_results等
            
        Returns:
            决策结果字典，格式：
            {
                "use_multimodal": bool,
                "reason": str,
                "playwright_actions": [...],
                "confidence": float,
                "ai_analysis": str
            }
        """
        try:
            prompt = self._build_analysis_prompt(test_case)
            logger.info(f"开始分析测试用例: {test_case.get('title', 'Unknown')}")
            
            # 调用LLM进行分析
            response = self.llm_service.invoke(prompt)
            
            # 解析JSON响应
            decision = self._parse_decision(response.content if hasattr(response, 'content') else str(response))
            
            logger.info(f"AI决策完成 - 使用多模态: {decision.get('use_multimodal')}, "
                       f"原因: {decision.get('reason', '')[:50]}")
            
            return decision
            
        except Exception as e:
            logger.error(f"AI决策分析失败: {e}", exc_info=True)
            # 返回默认决策（不使用多模态）
            return {
                "use_multimodal": False,
                "reason": f"AI分析失败: {str(e)}",
                "playwright_actions": [],
                "confidence": 0.0,
                "ai_analysis": f"分析出错: {str(e)}"
            }
    
    def _build_analysis_prompt(self, test_case: Dict[str, Any]) -> str:
        """构建AI分析Prompt"""
        
        title = test_case.get('title', '')
        steps = test_case.get('test_steps', '')
        expected = test_case.get('expected_results', '')
        preconditions = test_case.get('preconditions', '')
        
        prompt = f"""你是一位资深的UI自动化测试专家。请分析以下测试用例，生成 Playwright 自动化测试脚本的操作步骤。

## 测试用例信息

**用例标题**: {title}

**前置条件**: {preconditions}

**测试步骤**:
{steps}

**预期结果**:
{expected}

## 可用操作类型（playwright_actions）

请根据测试步骤选择以下操作类型：

### 页面操作
- **goto**: 导航到URL，target为完整URL
- **click**: 点击元素，target为CSS选择器
- **fill**: 填写输入框，target为选择器，value为输入内容
- **type**: 模拟键盘输入，target为选择器，value为输入内容
- **check**: 勾选复选框，target为选择器
- **uncheck**: 取消勾选复选框，target为选择器
- **select**: 下拉框选择，target为选择器，value为选项值

### 断言验证（重要：所有预期结果必须使用断言）
- **expect_visible**: 验证元素可见，target为选择器
- **expect_hidden**: 验证元素隐藏，target为选择器
- **expect_text**: 验证元素包含指定文本，target为选择器，value为预期文本
- **expect_url**: 验证当前URL，target为URL（完全匹配）
- **expect_count**: 验证元素数量，target为选择器，value为数量（数字字符串）

### 其他操作
- **screenshot**: 截图，用于关键步骤记录
- **wait**: 等待，value为秒数（如 "2"）

## 输出格式

必须严格按照以下JSON格式返回（不要添加任何额外文本）：

```json
{{
  "use_multimodal": false,
  "reason": "基于页面元素和验证需求的分析",
  "playwright_actions": [
    {{
      "action": "goto",
      "target": "https://www.baidu.com",
      "value": "",
      "description": "导航至百度首页"
    }},
    {{
      "action": "expect_visible",
      "target": "input#kw",
      "value": "",
      "description": "验证搜索输入框存在且可见"
    }}
  ],
  "confidence": 0.9,
  "ai_analysis": "详细的分析过程"
}}
```

## 重要规则

1. **每个测试步骤**都应该有对应的 playwright action
2. **预期结果必须使用断言**（expect_visible/expect_text/expect_url 等）
3. **选择器要准确**：使用 id、class 或其他可靠的 CSS 选择器
4. **goto 必须是第一个操作**，用于打开目标页面
5. **复杂操作可以拆分为多个步骤**

请开始分析：
"""
        return prompt
    
    def _parse_decision(self, response_text: str) -> Dict[str, Any]:
        """解析LLM返回的决策结果"""
        try:
            # 尝试提取JSON代码块
            import re
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response_text)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 如果没有代码块标记，尝试直接解析
                json_str = response_text.strip()
            
            decision = json.loads(json_str)
            
            # 验证必要字段
            required_fields = ['use_multimodal', 'reason', 'playwright_actions']
            for field in required_fields:
                if field not in decision:
                    raise ValueError(f"缺少必要字段: {field}")
            
            # 设置默认值
            decision.setdefault('confidence', 0.5)
            decision.setdefault('ai_analysis', '')
            
            return decision
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}\n原始响应: {response_text[:200]}")
            raise ValueError(f"无法解析AI决策结果: {str(e)}")
        except Exception as e:
            logger.error(f"决策解析异常: {e}")
            raise
