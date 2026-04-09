# UI自动化测试AI助手 - 安装配置指南

## 功能概述

本模块实现了基于现有用例库的智能UI自动化测试执行功能，包括：

- ✅ AI智能分析测试用例，自动判断是否需要多模态能力
- ✅ 动态生成Playwright测试脚本
- ✅ 异步执行测试（支持单用例和批量执行）
- ✅ 自动生成Allure可视化报告
- ✅ 实时进度监控和状态反馈

## 前置依赖安装

### 1. Python依赖

确保已安装以下Python包（已在requirements.txt中）：

```bash
pip install playwright pytest pytest-allure-pytest
```

### 2. Playwright浏览器安装

安装Playwright及其浏览器驱动：

```bash
playwright install
playwright install-deps  # Linux系统需要
```

这将安装Chromium、Firefox和WebKit浏览器。

### 3. Allure命令行工具安装

#### macOS:
```bash
brew install allure
```

#### Windows:
```bash
choco install allure
# 或从 https://github.com/allure-framework/allure2/releases 下载
```

#### Linux:
```bash
sudo apt-get install allure
# 或
sudo yum install allure
```

验证安装：
```bash
allure --version
```

## 数据库迁移

运行数据库迁移以创建自动化执行日志表：

```bash
python manage.py makemigrations core
python manage.py migrate core
```

## 配置说明

### LLM配置

确保在AI配置页面或settings.py中配置了LLM提供商（DeepSeek或通义千问）。

### 目录结构

执行产生的文件将保存在项目根目录的 `automation_results/` 文件夹：

```
automation_results/
├── scripts/              # 生成的Playwright测试脚本
├── screenshots/          # 测试截图
├── videos/              # 浏览器录制视频（非无头模式）
├── allure-results/      # Allure原始结果数据
└── allure-report/       # Allure HTML报告
```

## 使用方法

### 1. 访问用例库页面

访问：`http://localhost:9002/case_library/?project_id=<项目ID>`

### 2. 选择测试用例

在用例列表中勾选一个或多个测试用例。

### 3. 点击"AI执行"按钮

点击工具栏中的"AI执行"按钮，弹出配置对话框。

### 4. 配置执行参数

- **浏览器类型**: Chrome/Firefox/Safari
- **无头模式**: 是否显示浏览器窗口
- **LLM提供商**: DeepSeek或通义千问

### 5. 开始执行

点击"开始执行"，系统将：
1. AI分析每个用例
2. 生成Playwright脚本
3. 异步执行测试
4. 生成Allure报告

### 6. 查看执行进度

执行过程中会显示实时监控对话框，包括：
- 执行进度百分比
- 当前步骤说明
- AI决策信息（是否使用多模态）
- 执行时长

### 7. 查看报告

执行完成后，点击"查看报告"按钮在新标签页打开Allure报告。

也可以手动访问报告：
```bash
# 启动Allure报告服务
allure open automation_results/allure-report
```

## API接口

### 执行测试用例
```
POST /case_library/api/automation/execute/
Body: {
    "case_ids": [1, 2, 3],
    "browser": "chromium",
    "headless": true,
    "llm_provider": "deepseek"
}
```

### 查询执行状态
```
GET /case_library/api/automation/status/<task_uuid>/
```

### 获取执行报告
```
GET /case_library/api/automation/report/<task_uuid>/
```

### 查询执行历史
```
GET /case_library/api/automation/history/?page=1&page_size=20
```

## 故障排查

### 问题1: Playwright未安装

**错误**: `playwright not found`

**解决**:
```bash
pip install playwright
playwright install
```

### 问题2: Allure命令不存在

**错误**: `Allure命令行工具未安装`

**解决**: 参考上面的Allure安装步骤

### 问题3: 测试执行超时

**原因**: 测试用例执行时间超过5分钟

**解决**: 
- 检查测试步骤是否合理
- 增加超时时间（修改 `playwright_executor.py` 中的timeout参数）

### 问题4: AI分析失败

**错误**: `无法解析AI决策结果`

**解决**:
- 检查LLM配置是否正确
- 确保API Key有效
- 查看日志了解详细错误

## 性能优化建议

1. **批量执行**: 对于大量用例，建议使用批量执行而非逐个执行
2. **无头模式**: 生产环境建议开启无头模式以提升执行速度
3. **并行执行**: 未来可考虑使用Celery实现真正的并行执行
4. **缓存机制**: AI决策结果可以缓存，避免重复分析相同用例

## 安全注意事项

1. **API Key保护**: 不要在代码中硬编码API Key
2. **脚本隔离**: 每个任务生成独立的脚本文件，避免冲突
3. **超时控制**: 所有执行都有超时限制，防止无限等待
4. **资源清理**: 执行完成后及时清理临时文件

## 后续优化方向

- [ ] 集成Celery实现真正的分布式异步任务
- [ ] 支持多模态模型（GPT-4V、Qwen-VL等）进行视觉验证
- [ ] 添加测试用例执行历史记录和趋势分析
- [ ] 支持定时任务和CI/CD集成
- [ ] 提供测试报告对比功能
- [ ] 增加测试数据管理功能

## 技术支持

如有问题，请查看日志文件：
- Django日志: `logs/apps.ai_agents.case_library.views.log`
- AI决策日志: `logs/ai_decision_engine.log`
- 执行引擎日志: `logs/playwright_executor.log`
