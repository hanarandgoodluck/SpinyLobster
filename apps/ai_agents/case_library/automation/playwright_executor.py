"""
Playwright执行引擎 - 动态生成并执行UI自动化测试脚本

核心功能：
1. 根据AI决策结果动态生成Playwright测试脚本
2. 执行测试并捕获截图、日志
3. 集成Allure报告
4. 支持多浏览器和无头模式
"""

import os
import time
import uuid
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from apps.utils.logger_manager import get_logger

logger = get_logger(__name__)


class PlaywrightExecutor:
    """Playwright测试执行引擎"""
    
    def __init__(self, base_output_dir: str = None):
        """
        初始化执行引擎
        
        Args:
            base_output_dir: 输出目录基础路径
        """
        self.base_output_dir = base_output_dir or os.path.join(
            Path(__file__).resolve().parent.parent.parent.parent.parent,
            'automation_results'
        )
        
        # 确保目录存在
        os.makedirs(self.base_output_dir, exist_ok=True)
        os.makedirs(os.path.join(self.base_output_dir, 'scripts'), exist_ok=True)
        os.makedirs(os.path.join(self.base_output_dir, 'screenshots'), exist_ok=True)
        os.makedirs(os.path.join(self.base_output_dir, 'allure-results'), exist_ok=True)
        
        logger.info(f"Playwright执行引擎初始化完成，输出目录: {self.base_output_dir}")
    
    def generate_test_script(self, test_case: Dict[str, Any], 
                            ai_decision: Dict[str, Any],
                            browser: str = 'chromium',
                            headless: bool = True) -> str:
        """
        根据AI决策生成Playwright测试脚本
        
        Args:
            test_case: 测试用例信息
            ai_decision: AI决策结果
            browser: 浏览器类型 (chromium/firefox/webkit)
            headless: 是否无头模式
            
        Returns:
            生成的脚本文件路径
        """
        try:
            case_id = test_case.get('id', 'unknown')
            case_number = test_case.get('case_number', 'CASE-0000')
            title = test_case.get('title', 'Untitled')
            actions = ai_decision.get('playwright_actions', [])
            
            # 生成唯一的脚本文件名
            script_name = f"test_{case_number}_{uuid.uuid4().hex[:8]}.py"
            script_path = os.path.join(self.base_output_dir, 'scripts', script_name)
            
            # 生成Python测试脚本
            script_content = self._build_script_content(
                test_case=test_case,
                actions=actions,
                browser=browser,
                headless=headless,
                case_number=case_number
            )
            
            # 写入文件
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script_content)
            
            logger.info(f"测试脚本生成成功: {script_path}")
            return script_path
            
        except Exception as e:
            logger.error(f"生成测试脚本失败: {e}", exc_info=True)
            raise
    
    def _build_script_content(self, test_case: Dict[str, Any],
                             actions: List[Dict[str, Any]],
                             browser: str,
                             headless: bool,
                             case_number: str) -> str:
        """构建Playwright测试脚本内容"""
        
        title = test_case.get('title', '').replace('"', '\\"')
        steps_text = test_case.get('test_steps', '').replace('"', '\\"')
        expected_text = test_case.get('expected_results', '').replace('"', '\\"')
        
        # 浏览器映射
        browser_map = {
            'chromium': 'chromium',
            'firefox': 'firefox',
            'webkit': 'webkit'
        }
        browser_type = browser_map.get(browser, 'chromium')
        
        # 生成操作步骤代码
        actions_code = self._generate_actions_code(actions)
        
        script = f'''"""
自动生成测试脚本 - {case_number}
生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
import pytest
import allure
from playwright.sync_api import sync_playwright, expect
import os
import time


def test_{case_number.replace("-", "_").lower()}():
    """
    测试用例: {title}
    
    测试步骤:
    {steps_text}
    
    预期结果:
    {expected_text}
    """
    
    # Allure报告配置
    allure.dynamic.title("{title}")
    allure.dynamic.description("""
    **测试步骤**:
    {steps_text}
    
    **预期结果**:
    {expected_text}
    """)
    allure.dynamic.tag("auto-generated")
    allure.dynamic.tag("{case_number}")
    
    # 启动浏览器
    with sync_playwright() as p:
        browser = p.{browser_type}.launch(headless={str(headless).lower()})
        context = browser.new_context(
            viewport={{"width": 1920, "height": 1080}},
            record_video_dir="videos/" if not {str(headless).lower()} else None
        )
        page = context.new_page()
        
        # 启用截图和追踪
        page.set_default_timeout(30000)
        
        try:
{actions_code}
            
            # 测试通过
            allure.attach(
                page.screenshot(full_page=True),
                name="最终页面截图",
                attachment_type=allure.attachment_type.PNG
            )
            pytest.skip("测试执行完成")
            
        except Exception as e:
            # 测试失败时截图
            screenshot = page.screenshot(full_page=True)
            allure.attach(
                screenshot,
                name="失败时页面截图",
                attachment_type=allure.attachment_type.PNG
            )
            raise e
            
        finally:
            context.close()
            browser.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--alluredir=./allure-results"])
'''
        return script
    
    def _generate_actions_code(self, actions: List[Dict[str, Any]]) -> str:
        """将AI决策的操作转换为Playwright代码"""
        code_lines = []
        
        for i, action in enumerate(actions, 1):
            action_type = action.get('action', '')
            target = action.get('target', '')
            value = action.get('value', '')
            description = action.get('description', f'步骤 {i}')
            
            # 添加Allure步骤标记
            code_lines.append(f'            with allure.step("{description}"):')
            
            # 根据操作类型生成代码
            if action_type == 'goto':
                code_lines.append(f'                page.goto("{target}")')
                code_lines.append(f'                time.sleep(2)  # 等待页面加载')
                
            elif action_type == 'click':
                code_lines.append(f'                page.click("{target}")')
                code_lines.append(f'                time.sleep(1)')
                
            elif action_type == 'fill':
                code_lines.append(f'                page.fill("{target}", "{value}")')
                code_lines.append(f'                time.sleep(0.5)')
                
            elif action_type == 'type':
                code_lines.append(f'                page.type("{target}", "{value}")')
                code_lines.append(f'                time.sleep(0.5)')
                
            elif action_type == 'check':
                code_lines.append(f'                page.check("{target}")')
                code_lines.append(f'                time.sleep(0.5)')
                
            elif action_type == 'select':
                code_lines.append(f'                page.select_option("{target}", "{value}")')
                code_lines.append(f'                time.sleep(0.5)')
                
            elif action_type == 'screenshot':
                screenshot_name = f"screenshot_step_{i}.png"
                code_lines.append(f'                screenshot = page.screenshot(path="{screenshot_name}")')
                code_lines.append(f'                allure.attach(screenshot, name="{description}", attachment_type=allure.attachment_type.PNG)')
                
            elif action_type == 'expect_visible':
                code_lines.append(f'                expect(page.locator("{target}")).to_be_visible()')
                
            elif action_type == 'expect_text':
                code_lines.append(f'                expect(page.locator("{target}")).to_contain_text("{value}")')
                
            elif action_type == 'wait':
                code_lines.append(f'                time.sleep({value if value else 2})')
                
            else:
                code_lines.append(f'                # 未支持的操作: {action_type}')
                code_lines.append(f'                pass')
            
            code_lines.append('')  # 空行分隔
        
        return '\n'.join(code_lines)
    
    def execute_test(self, script_path: str, task_uuid: str) -> Dict[str, Any]:
        """
        执行测试脚本
        
        Args:
            script_path: 测试脚本路径
            task_uuid: 任务UUID
            
        Returns:
            执行结果字典
        """
        try:
            start_time = time.time()
            logger.info(f"开始执行测试: {script_path}")
            
            # 构建pytest命令
            allure_results_dir = os.path.join(self.base_output_dir, 'allure-results')
            cmd = [
                'python', '-m', 'pytest',
                script_path,
                '-v',
                f'--alluredir={allure_results_dir}',
                '--tb=short'
            ]
            
            # 执行测试
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5分钟超时
                cwd=self.base_output_dir
            )
            
            execution_time = time.time() - start_time
            
            # 解析执行结果
            success = result.returncode == 0
            status = 'passed' if success else 'failed'
            
            logger.info(f"测试执行完成 - 状态: {status}, 耗时: {execution_time:.2f}s")
            
            return {
                'success': success,
                'status': status,
                'execution_time': execution_time,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode,
                'allure_results_dir': allure_results_dir
            }
            
        except subprocess.TimeoutExpired:
            logger.error(f"测试执行超时: {script_path}")
            return {
                'success': False,
                'status': 'error',
                'execution_time': 300,
                'error_message': '测试执行超时（超过5分钟）'
            }
        except Exception as e:
            logger.error(f"测试执行异常: {e}", exc_info=True)
            return {
                'success': False,
                'status': 'error',
                'execution_time': time.time() - start_time if 'start_time' in locals() else 0,
                'error_message': str(e)
            }
    
    def generate_allure_report(self, allure_results_dir: str, 
                              report_output_dir: str = None) -> str:
        """
        生成Allure报告
        
        Args:
            allure_results_dir: Allure结果目录
            report_output_dir: 报告输出目录
            
        Returns:
            报告HTML目录路径
        """
        try:
            if not report_output_dir:
                report_output_dir = os.path.join(self.base_output_dir, 'allure-report')
            
            # 确保输出目录存在
            os.makedirs(report_output_dir, exist_ok=True)
            
            # 检查allure命令行工具是否可用
            try:
                result = subprocess.run(
                    ['allure', '--version'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                logger.info(f"Allure版本: {result.stdout.strip()}")
            except FileNotFoundError:
                logger.warning("Allure命令行工具未安装，跳过报告生成")
                return ""
            
            # 生成报告
            cmd = [
                'allure', 'generate',
                allure_results_dir,
                '-o', report_output_dir,
                '--clean'
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                logger.info(f"Allure报告生成成功: {report_output_dir}")
                return report_output_dir
            else:
                logger.error(f"Allure报告生成失败: {result.stderr}")
                return ""
                
        except Exception as e:
            logger.error(f"生成Allure报告异常: {e}", exc_info=True)
            return ""
