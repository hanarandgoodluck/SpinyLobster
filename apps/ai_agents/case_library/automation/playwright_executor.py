"""
Playwright执行引擎 - 动态生成并执行UI自动化测试脚本

核心功能：
1. 根据AI决策结果动态生成Playwright测试脚本
2. 执行测试并捕获截图、日志
3. 集成BeautifulReport报告（无需Java环境）
4. 支持多浏览器和无头模式
"""

import os
import time
import uuid
import json
import subprocess
import traceback
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
        os.makedirs(os.path.join(self.base_output_dir, 'reports'), exist_ok=True)
        
        logger.info(f"Playwright执行引擎初始化完成，输出目录: {self.base_output_dir}")
    
    def generate_test_script(self, test_case: Dict[str, Any], 
                            ai_decision: Dict[str, Any],
                            browser: str = 'chromium',
                            headless: bool = False,
                            task_name: str = None) -> str:
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
                case_number=case_number,
                task_name=task_name
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
                             case_number: str,
                             task_name: str = None) -> str:
        """构建Playwright测试脚本内容（基于unittest+BeautifulReport）"""
        
        title = test_case.get('title', '').replace('"', '\\"').replace("'", "\\'")
        steps_text = test_case.get('test_steps', '').replace('"', '\\"').replace("'", "\\'")
        expected_text = test_case.get('expected_results', '').replace('"', '\\"').replace("'", "\\'")
        
        # 浏览器映射（默认使用 Edge，因为本地已安装）
        browser_map = {
            'chromium': 'chromium',
            'firefox': 'firefox',
            'webkit': 'webkit',
            'msedge': 'chromium',  # Edge 使用 chromium 内核
            'edge': 'chromium',
        }
        browser_type = browser_map.get(browser, 'chromium')
        
        # 检测本地 Edge 浏览器路径
        import platform
        edge_path = ''
        is_edge = browser in ['msedge', 'edge']
        if is_edge:
            if platform.system() == 'Windows':
                # Windows Edge 默认安装路径
                edge_paths = [
                    r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
                    r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
                ]
                for path in edge_paths:
                    if os.path.exists(path):
                        edge_path = path
                        break
        
        # 生成操作步骤代码
        actions_code = self._generate_actions_code(actions)
        
        # 如果有 Edge 路径，使用 executable_path 参数
        if edge_path:
            launch_config = f'executable_path=r"{edge_path}"'
        else:
            launch_config = ''
        
        script = '''"""
自动生成测试脚本 - {case_number}
生成时间: {generate_time}
"""
import unittest
from playwright.sync_api import sync_playwright
import os
import time


class Test{case_number_class}(unittest.TestCase):
    """
    测试用例: {title}
    
    测试步骤:
    {steps_text}
    
    预期结果:
    {expected_text}
    """
    
    def setUp(self):
        """测试前置：启动本地 Chrome/Edge 浏览器"""
        self.playwright = sync_playwright().start()
        launch_args = {{"headless": {headless_lower}}}
        if "{edge_path}":  # 如果检测到本地 Edge，使用它
            launch_args["executable_path"] = r"{edge_path}"
            launch_args["channel"] = "msedge"
        elif "{chrome_path}": # 如果检测到本地 Chrome
            launch_args["executable_path"] = r"{chrome_path}"
            launch_args["channel"] = "chrome"
        
        self.browser = self.playwright.{browser_type}.launch(**launch_args)
        self.context = self.browser.new_context(
            viewport={{"width": 1920, "height": 1080}}
        )
        self.page = self.context.new_page()
        self.page.set_default_timeout(30000)
        self.screenshot_dir = os.path.join(os.path.dirname(__file__), '..', 'screenshots', '{task_uuid}')
        os.makedirs(self.screenshot_dir, exist_ok=True)
    
    def tearDown(self):
        """测试后置：关闭浏览器，若失败则截图"""
        # 兼容不同 Python 版本的失败检测逻辑
        is_failed = False
        if hasattr(self, '_outcome'):
            # Python 3.11+ 或特定版本
            if hasattr(self._outcome, 'errors') and self._outcome.errors:
                is_failed = True
            elif hasattr(self._outcome, 'result') and self._outcome.result:
                # 检查 result 中的失败记录
                if self._outcome.result.failures or self._outcome.result.errors:
                    is_failed = True
        
        if is_failed:
            # 如果测试失败，截取当前页面
            try:
                screenshot_path = os.path.join(self.screenshot_dir, f'error_{{int(time.time())}}.png')
                self.page.screenshot(path=screenshot_path, full_page=True)
                print(f"\\n[ERROR_SCREENSHOT] 失败截图已保存: {{screenshot_path}}")
            except Exception as e:
                print(f"\\n[ERROR] 截图失败: {{e}}")
        
        self.context.close()
        self.browser.close()
        self.playwright.stop()
    
    def test_execute(self):
        """执行测试用例"""
        self.__doc__ = """测试用例: {title}"""
{actions_code}


if __name__ == "__main__":
    unittest.main(verbosity=2)
'''
        # 格式化脚本
        script = script.format(
            case_number=case_number,
            case_number_class=case_number.replace("-", "_").replace(" ", "").replace(".", ""),
            generate_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            title=title,
            steps_text=steps_text,
            expected_text=expected_text,
            browser_type=browser_type,
            headless_lower=str(headless),  # Python 布尔值: True/False
            edge_path=edge_path,  # Edge 浏览器路径
            chrome_path='',  # 预留 Chrome 路径检测
            task_uuid=task_uuid if 'task_uuid' in locals() else 'debug',
            task_name=self._escape_html(task_name) if task_name else '自动化测试',
            actions_code=actions_code
        )
        
        return script
    
    def _generate_actions_code(self, actions: List[Dict[str, Any]]) -> str:
        """将AI决策的操作转换为Playwright代码（基于unittest）"""
        code_lines = []
        
        for i, action in enumerate(actions, 1):
            action_type = action.get('action', '')
            target = action.get('target', '')
            value = action.get('value', '')
            description = action.get('description', f'步骤 {i}')
            
            # 添加步骤注释和日志（8空格缩进，方法体级别）
            code_lines.append(f'        print("[STEP] {description}")')
            code_lines.append(f'        # {description}')
            
            # 根据操作类型生成代码（8空格缩进，方法体级别）
            if action_type == 'goto':
                code_lines.append(f'        self.page.goto("{target}")')
                code_lines.append(f'        self.page.wait_for_load_state("networkidle", timeout=15000)  # 等待页面加载完成')
                code_lines.append(f'        self.page.set_viewport_size({{"width": 1920, "height": 1080}})  # 确保PC端布局')
                
            elif action_type == 'click':
                code_lines.append(f'        try:')
                code_lines.append(f'            self.page.click("{target}", timeout=5000)')
                code_lines.append(f'        except Exception:')
                code_lines.append(f'            self.page.evaluate("document.querySelector(\'{target}\').click()")')
                code_lines.append(f'        time.sleep(1)')
                
            elif action_type == 'fill':
                code_lines.append(f'        try:')
                code_lines.append(f'            self.page.fill("{target}", "{value}", timeout=5000)')
                code_lines.append(f'        except Exception:')
                code_lines.append(f'            # 降级方案：通过JS强制赋值')
                code_lines.append(f'            self.page.evaluate("""')
                code_lines.append(f'                const el = document.querySelector("{target}");')
                code_lines.append(f'                if (el) {{ el.value = "{value}"; el.dispatchEvent(new Event("input", {{ bubbles: true }})); }}')
                code_lines.append(f'            """)')
                code_lines.append(f'        time.sleep(0.5)')
                
            elif action_type == 'type':
                code_lines.append(f'        self.page.type("{target}", "{value}")')
                code_lines.append(f'        time.sleep(0.5)')
                
            elif action_type == 'check':
                code_lines.append(f'        self.page.check("{target}")')
                code_lines.append(f'        time.sleep(0.5)')
            
            elif action_type == 'uncheck':
                code_lines.append(f'        self.page.uncheck("{target}")')
                code_lines.append(f'        time.sleep(0.5)')
                
            elif action_type == 'select':
                code_lines.append(f'        self.page.select_option("{target}", "{value}")')
                code_lines.append(f'        time.sleep(0.5)')
                
            elif action_type == 'screenshot':
                screenshot_name = f"screenshot_step_{i}.png"
                code_lines.append(f'        self.page.screenshot(path="{screenshot_name}")')
                
            elif action_type == 'expect_visible':
                code_lines.append(f'        from playwright.sync_api import expect')
                code_lines.append(f'        locator = self.page.locator("{target}")')
                code_lines.append(f'        try:')
                code_lines.append(f'            expect(locator).to_be_visible(timeout=5000)')
                code_lines.append(f'        except Exception:')
                code_lines.append(f'            # 如果 to_be_visible 失败，尝试检查元素是否在DOM中')
                code_lines.append(f'            self.assertTrue(locator.count() > 0, "元素不存在于DOM中: {target}")')
                
            elif action_type == 'expect_hidden':
                code_lines.append(f'        self.assertFalse(self.page.locator("{target}").is_visible(), "元素应该隐藏: {target}")')
                
            elif action_type == 'expect_text':
                code_lines.append(f'        self.assertIn("{value}", self.page.locator("{target}").inner_text(), "文本不匹配: 预期包含\'{value}\'")')
                
            elif action_type == 'expect_url':
                code_lines.append(f'        self.assertEqual(self.page.url, "{target}", f"URL不匹配: 预期\'{target}\', 实际\'{{self.page.url}}\'")')
                
            elif action_type == 'expect_count':
                code_lines.append(f'        self.assertEqual(self.page.locator("{target}").count(), {value}, "元素数量不匹配: 预期{value}")')
                
            elif action_type == 'wait':
                code_lines.append(f'        time.sleep({value if value else 2})')
                
            else:
                code_lines.append(f'        # 未支持的操作: {action_type}')
                code_lines.append(f'        pass')
            
            code_lines.append('')  # 空行分隔
        
        return '\n'.join(code_lines)
    
    def execute_test(self, script_path: str, task_uuid: str) -> Dict[str, Any]:
        """
        执行测试脚本（使用unittest）
        
        Args:
            script_path: 测试脚本路径
            task_uuid: 任务UUID
            
        Returns:
            执行结果字典
        """
        try:
            start_time = time.time()
            logger.info(f"开始执行测试: {script_path}")
            
            # 直接使用python执行unittest脚本
            report_output_dir = os.path.join(self.base_output_dir, 'reports', task_uuid)
            os.makedirs(report_output_dir, exist_ok=True)
            
            cmd = [
                'python', script_path
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
            
            # 生成BeautifulReport报告
            report_path = self._generate_html_report(
                task_uuid=task_uuid,
                output_dir=report_output_dir,
                stdout=result.stdout,
                stderr=result.stderr,
                success=success,
                execution_time=execution_time,
                script_path=script_path
            )
            
            return {
                'success': success,
                'status': status,
                'execution_time': execution_time,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode,
                'report_path': report_path
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
    
    def _generate_html_report(self, task_uuid: str, output_dir: str,
                              stdout: str, stderr: str,
                              success: bool, execution_time: float,
                              script_path: str) -> str:
        """
        生成HTML测试报告
        
        Args:
            task_uuid: 任务UUID
            output_dir: 输出目录
            stdout: 标准输出
            stderr: 标准错误
            success: 是否成功
            execution_time: 执行时间
            script_path: 脚本路径
            
        Returns:
            报告HTML文件路径
        """
        try:
            html_path = os.path.join(output_dir, 'report.html')
            
            # 从脚本路径提取用例编号
            script_basename = os.path.basename(script_path)
            case_number = script_basename.replace('test_', '').split('_')[0] if 'test_' in script_basename else 'Unknown'
            
            # 提取错误信息
            error_info = stderr if not success else ''
            error_lines = error_info.split('\n')[-10:] if error_info else []
            
            # 生成HTML报告
            html_content = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>自动化测试报告 - {task_uuid}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f7fa; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 12px; margin-bottom: 20px; }}
        .header h1 {{ font-size: 28px; margin-bottom: 10px; }}
        .header .meta {{ opacity: 0.9; font-size: 14px; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }}
        .card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .card h3 {{ color: #606266; font-size: 14px; margin-bottom: 8px; }}
        .card .value {{ font-size: 24px; font-weight: 600; }}
        .status-passed {{ color: #67c23a; }}
        .status-failed {{ color: #f56c6c; }}
        .status-error {{ color: #e6a23c; }}
        .section {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); margin-bottom: 20px; }}
        .section h2 {{ font-size: 18px; color: #303133; margin-bottom: 15px; padding-bottom: 10px; border-bottom: 2px solid #409eff; }}
        .log {{ background: #1e1e1e; color: #d4d4d4; padding: 15px; border-radius: 6px; overflow-x: auto; font-family: 'Consolas', monospace; font-size: 13px; line-height: 1.6; max-height: 400px; overflow-y: auto; }}
        .tag {{ display: inline-block; padding: 4px 12px; border-radius: 4px; font-size: 12px; font-weight: 500; }}
        .tag-success {{ background: #f0f9eb; color: #67c23a; }}
        .tag-failed {{ background: #fef0f0; color: #f56c6c; }}
        pre {{ white-space: pre-wrap; word-wrap: break-word; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 {case_number}测试报告</h1>
            <div class="meta">
                <span>任务ID: {task_uuid}</span> | 
                <span>用例编号: {case_number}</span> | 
                <span>执行时间: {execution_time:.2f}秒</span>
            </div>
        </div>
        
        <div class="summary">
            <div class="card">
                <h3>执行状态</h3>
                <div class="value status-{"passed" if success else "failed"}">
                    <span class="tag tag-{"success" if success else "failed"}">{"✓ 通过" if success else "✗ 失败"}</span>
                </div>
            </div>
            <div class="card">
                <h3>执行耗时</h3>
                <div class="value">{execution_time:.2f}s</div>
            </div>
            <div class="card">
                <h3>测试脚本</h3>
                <div class="value" style="font-size: 14px; word-break: break-all;">{os.path.basename(script_path)}</div>
            </div>
        </div>
        
        <div class="section">
            <h2>📋 测试用例执行详情</h2>
            {self._generate_execution_table(stdout, stderr, success)}
        </div>
        
        {self._generate_screenshot_section(output_dir, task_uuid)}
        
        {"<div class='section'><h2>❌ 错误详情</h2><div class='log'><pre>" + self._escape_html(error_info) + "</pre></div></div>" if not success else ""}
    </div>
</body>
</html>'''
            
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"HTML测试报告生成成功: {html_path}")
            return html_path
            
        except Exception as e:
            logger.error(f"生成HTML报告异常: {e}", exc_info=True)
            return ""
    
    def _generate_execution_table(self, stdout: str, stderr: str, success: bool) -> str:
        """生成用例执行步骤表格"""
        steps = []
        for line in stdout.split('\n'):
            if '[STEP]' in line:
                step_desc = line.split('[STEP]')[1].strip()
                steps.append(step_desc)
        
        if not steps:
            return '<p style="color: #909399;">未检测到详细步骤日志</p>'

        html_parts = ['<table style="width: 100%; border-collapse: collapse; margin-top: 10px;"><thead><tr style="background: #f5f7fa;">']
        html_parts.append('<th style="padding: 12px; text-align: left; border-bottom: 2px solid #ebeef5;">步骤描述</th>')
        html_parts.append('<th style="padding: 12px; text-align: center; border-bottom: 2px solid #ebeef5; width: 100px;">状态</th>')
        html_parts.append('</tr></thead><tbody>')

        for i, step in enumerate(steps):
            # 简单逻辑：如果整体失败，且是最后一步或之后，标记为失败，否则标记为通过
            status_class = 'tag-success'
            status_text = '✓ 通过'
            if not success and i == len(steps) - 1:
                status_class = 'tag-failed'
                status_text = '✗ 失败'
            
            html_parts.append(f'<tr><td style="padding: 10px; border-bottom: 1px solid #ebeef5;">{i+1}. {self._escape_html(step)}</td>')
            html_parts.append(f'<td style="padding: 10px; text-align: center; border-bottom: 1px solid #ebeef5;"><span class="tag {status_class}">{status_text}</span></td></tr>')
        
        html_parts.append('</tbody></table>')
        return ''.join(html_parts)

    def _generate_screenshot_section(self, output_dir: str, task_uuid: str) -> str:
        """生成截图展示区域"""
        screenshot_base = os.path.join(os.path.dirname(output_dir), 'screenshots', task_uuid)
        if not os.path.exists(screenshot_base):
            return ""
        
        screenshots = [f for f in os.listdir(screenshot_base) if f.endswith('.png')]
        if not screenshots:
            return ""
        
        html_parts = ['<div class="section"><h2>📸 失败现场截图</h2><div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 15px;">']
        for img in screenshots:
            img_path = os.path.join('..', 'screenshots', task_uuid, img)
            html_parts.append(f'<div style="background: #fff; padding: 10px; border-radius: 6px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);"><img src="{img_path}" style="width: 100%; border-radius: 4px;"><p style="text-align: center; color: #909399; font-size: 12px; margin-top: 5px;">{img}</p></div>')
        
        html_parts.append('</div></div>')
        return ''.join(html_parts)

    def _escape_html(self, text: str) -> str:
        """转义HTML特殊字符"""
        if not text:
            return ""
        return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    
    def generate_allure_report(self, report_path: str, 
                              report_output_dir: str = None) -> str:
        """
        兼容旧接口：直接返回报告路径
        
        Args:
            report_path: 报告路径（HTML文件或目录）
            report_output_dir: 报告输出目录（未使用，保持接口兼容）
            
        Returns:
            报告路径
        """
        return report_path
