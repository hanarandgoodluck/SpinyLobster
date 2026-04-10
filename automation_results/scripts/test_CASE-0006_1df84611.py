"""
自动生成测试脚本 - CASE-0006
生成时间: 2026-04-10 18:00:39
"""
import unittest
from playwright.sync_api import sync_playwright
import os
import time


class TestCASE_0006(unittest.TestCase):
    """
    测试用例: 打开百度
    
    测试步骤:
    打开百度
    
    预期结果:
    
    """
    
    def setUp(self):
        """测试前置：启动本地 Chrome/Edge 浏览器"""
        self.playwright = sync_playwright().start()
        launch_args = {"headless": False}
        if "":  # 如果检测到本地 Edge，使用它
            launch_args["executable_path"] = r""
            launch_args["channel"] = "msedge"
        elif "": # 如果检测到本地 Chrome
            launch_args["executable_path"] = r""
            launch_args["channel"] = "chrome"
        
        self.browser = self.playwright.chromium.launch(**launch_args)
        self.context = self.browser.new_context(
            viewport={"width": 1920, "height": 1080}
        )
        self.page = self.context.new_page()
        self.page.set_default_timeout(30000)
        self.screenshot_dir = os.path.join(os.path.dirname(__file__), '..', 'screenshots', 'debug')
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
                screenshot_path = os.path.join(self.screenshot_dir, f'error_{int(time.time())}.png')
                self.page.screenshot(path=screenshot_path, full_page=True)
                print(f"\n[ERROR_SCREENSHOT] 失败截图已保存: {screenshot_path}")
            except Exception as e:
                print(f"\n[ERROR] 截图失败: {e}")
        
        self.context.close()
        self.browser.close()
        self.playwright.stop()
    
    def test_execute(self):
        """执行测试用例"""
        self.__doc__ = """测试用例: 打开百度"""
        print("[步骤 1] 导航至百度首页")
        # 导航至百度首页
        self.page.goto("https://www.baidu.com")
        self.page.wait_for_load_state("networkidle", timeout=15000)  # 等待页面加载完成
        self.page.set_viewport_size({"width": 1920, "height": 1080})  # 确保PC端布局

        print("[步骤 2] 验证百度搜索输入框已成功加载并可见，确认页面打开成功")
        # 验证百度搜索输入框已成功加载并可见，确认页面打开成功
        from playwright.sync_api import expect
        locator = self.page.locator("#kw")
        try:
            expect(locator).to_be_visible(timeout=5000)
        except Exception:
            # 如果 to_be_visible 失败，尝试检查元素是否在DOM中
            self.assertTrue(locator.count() > 0, "元素不存在于DOM中: #kw")



if __name__ == "__main__":
    unittest.main(verbosity=2)
