const { createApp } = Vue;

document.addEventListener('DOMContentLoaded', function() {
    const app = createApp({
        data() {
            return {
                // 用例列表
                cases: [],
                total: 0,
                currentPage: 1,
                pageSize: 10,
                searchText: '',
                selectedPriority: '',
                selectedModule: '',
                selectedCases: [],
                jumpPage: 1,
                testType: 'web',
                
                // 模块树
                moduleTree: [],
                
                // 执行配置
                executeDialogVisible: false,
                executionMonitorVisible: false,
                executing: false,
                executeConfig: {
                    browser: 'chromium',
                    headless: true,
                    llm_provider: 'deepseek'
                },
                
                // 执行监控
                currentExecution: null,
                executionProgress: {},
                executionPollTimer: null,
                
                // 用例详情
                detailDialogVisible: false,
                currentCase: null
            };
        },
        
        methods: {
            getCookie(name) {
                const cookies = document.cookie.split(';');
                for (const cookie of cookies) {
                    const [key, value] = cookie.trim().split('=');
                    if (key === name) return decodeURIComponent(value);
                }
                return null;
            },
            
            async fetchApi(url, options = {}) {
                const defaultOptions = {
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCookie('csrftoken')
                    }
                };
                const response = await fetch(url, { ...defaultOptions, ...options });
                return response.json();
            },
            
            // 加载用例列表
            async loadCases() {
                try {
                    const projectId = this.getProjectId();
                    const params = new URLSearchParams({
                        page: this.currentPage,
                        page_size: this.pageSize,
                        search: this.searchText,
                    });
                    
                    if (projectId) params.append('project_id', projectId);
                    if (this.selectedModule) params.append('module', this.selectedModule);
                    if (this.selectedPriority) params.append('priority', this.selectedPriority);
                    
                    const data = await this.fetchApi(`/case_library/api/list/?${params}`);
                    
                    if (data.success) {
                        this.cases = data.data.cases || [];
                        this.total = data.data.total;
                        this.jumpPage = this.currentPage;
                    } else {
                        ElementPlus.ElMessage.error('加载用例失败：' + data.message);
                    }
                } catch (error) {
                    console.error('加载用例失败:', error);
                    ElementPlus.ElMessage.error('加载用例失败');
                }
            },
            
            // 加载模块树
            async loadModules() {
                try {
                    const projectId = this.getProjectId();
                    const params = projectId ? new URLSearchParams({ project_id: projectId }) : '';
                    const data = await this.fetchApi(`/case_library/api/modules/?${params}`);
                    
                    if (data.success) {
                        // 将模块数据转换为树形结构
                        this.moduleTree = this.buildModuleTree(data.data);
                    } else {
                        console.error('加载模块失败：', data.message);
                    }
                } catch (error) {
                    console.error('加载模块树失败:', error);
                }
            },
            
            // 构建模块树
            buildModuleTree(modulesData) {
                const tree = [];
                
                // 添加“所有模块”选项
                tree.push({
                    value: '',
                    label: '所有模块',
                    children: []
                });
                
                // 遍历模块数据构建树
                for (const moduleName in modulesData) {
                    const moduleInfo = modulesData[moduleName];
                    tree.push({
                        value: moduleName,
                        label: `${moduleName} (${moduleInfo.count})`,
                        children: []
                    });
                }
                
                return tree;
            },
            
            // 重置搜索
            resetSearch() {
                this.searchText = '';
                this.selectedModule = '';
                this.selectedPriority = '';
                this.currentPage = 1;
                this.loadCases();
            },
            
            // 处理选择变化
            handleSelectionChange(selection) {
                this.selectedCases = selection.map(item => item.id);
            },
            
            // 分页变化
            handlePageChange(page) {
                this.currentPage = page;
                this.loadCases();
            },
            
            // 每页条数变化
            handlePageSizeChange() {
                this.currentPage = 1;
                this.loadCases();
            },
            
            // 跳转到指定页
            jumpToPage() {
                if (this.jumpPage && this.jumpPage > 0) {
                    this.currentPage = this.jumpPage;
                    this.loadCases();
                }
            },
            
            // 获取优先级数字
            getPriorityNumber(priority) {
                if (!priority) return 2;
                const map = { 'p1': 1, 'p2': 2, 'p3': 3, 'p4': 4 };
                return map[priority.toLowerCase()] || 2;
            },
            
            // 显示用例详情
            async showCaseDetail(caseId) {
                try {
                    const data = await this.fetchApi(`/case_library/api/detail/${caseId}/`);
                    if (data.success) {
                        this.currentCase = data.data;
                        this.detailDialogVisible = true;
                    } else {
                        ElementPlus.ElMessage.error('加载失败：' + data.message);
                    }
                } catch (error) {
                    console.error('加载用例详情失败:', error);
                    ElementPlus.ElMessage.error('加载失败');
                }
            },
            
            // 创建AI测试任务
            createAITask() {
                if (this.selectedCases.length === 0) {
                    ElementPlus.ElMessage.warning('请至少选择一个测试用例');
                    return;
                }
                this.executeDialogVisible = true;
            },
            
            // 显示历史记录
            showHistory() {
                ElementPlus.ElMessage.info('执行记录功能开发中...');
            },
            
            // 显示执行对话框
            showExecuteDialog() {
                if (this.selectedCases.length === 0) {
                    ElementPlus.ElMessage.warning('请至少选择一个测试用例');
                    return;
                }
                this.executeDialogVisible = true;
            },
            
            // 确认执行
            async confirmExecute() {
                try {
                    this.executing = true;
                    
                    const response = await fetch('/ui_automation/api/execute/', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': this.getCookie('csrftoken')
                        },
                        body: JSON.stringify({
                            case_ids: this.selectedCases,
                            browser: this.executeConfig.browser,
                            headless: this.executeConfig.headless,
                            llm_provider: this.executeConfig.llm_provider
                        })
                    });
                    
                    const data = await response.json();
                    
                    if (data.success) {
                        ElementPlus.ElMessage.success(data.message);
                        this.executeDialogVisible = false;
                        
                        // 打开监控对话框
                        this.executionMonitorVisible = true;
                        
                        // 开始轮询状态
                        setTimeout(() => {
                            this.startExecutionPolling();
                        }, 1000);
                    } else {
                        ElementPlus.ElMessage.error('执行失败: ' + data.message);
                    }
                } catch (error) {
                    console.error('执行请求失败:', error);
                    ElementPlus.ElMessage.error('执行请求失败');
                } finally {
                    this.executing = false;
                }
            },
            
            // 开始轮询执行状态
            startExecutionPolling() {
                if (this.executionPollTimer) {
                    clearInterval(this.executionPollTimer);
                }
                
                this.pollExecutionStatus();
                
                this.executionPollTimer = setInterval(() => {
                    this.pollExecutionStatus();
                }, 2000);
            },
            
            // 轮询执行状态
            async pollExecutionStatus() {
                try {
                    const response = await fetch(`/ui_automation/api/history/?page=1&page_size=1`);
                    const data = await response.json();
                    
                    if (data.success && data.data.history.length > 0) {
                        const latest = data.data.history[0];
                        
                        const statusResponse = await fetch(`/ui_automation/api/status/${latest.task_uuid}/`);
                        const statusData = await statusResponse.json();
                        
                        if (statusData.success) {
                            this.currentExecution = statusData.data;
                            this.executionProgress = statusData.data.progress || {};
                            
                            if (['passed', 'failed', 'error'].includes(statusData.data.status)) {
                                if (this.executionPollTimer) {
                                    clearInterval(this.executionPollTimer);
                                    this.executionPollTimer = null;
                                }
                                
                                if (statusData.data.status === 'passed') {
                                    ElementPlus.ElMessage.success('测试执行通过！');
                                } else if (statusData.data.status === 'failed') {
                                    ElementPlus.ElMessage.warning('测试执行失败');
                                } else {
                                    ElementPlus.ElMessage.error('测试执行出错');
                                }
                                
                                // 刷新历史记录
                                this.loadHistory();
                            }
                        }
                    }
                } catch (error) {
                    console.error('轮询状态失败:', error);
                }
            },
            
            // 获取执行状态类型
            getExecutionStatusType() {
                if (!this.currentExecution) return '';
                const status = this.currentExecution.status;
                if (status === 'passed') return 'success';
                if (status === 'failed') return 'exception';
                if (status === 'error') return 'exception';
                return undefined;
            },
            
            // 获取状态标签类型
            getStatusTagType(status) {
                const typeMap = {
                    'pending': 'info',
                    'running': 'warning',
                    'passed': 'success',
                    'failed': 'danger',
                    'error': 'danger'
                };
                return typeMap[status] || 'info';
            },
            
            // 查看报告
            viewReport(taskUuid) {
                window.open(`/ui_automation/report/${taskUuid}/index.html`, '_blank');
            },
            
            // 查看当前执行报告
            viewCurrentReport() {
                if (this.currentExecution && this.currentExecution.report_url) {
                    window.open(this.currentExecution.report_url, '_blank');
                } else {
                    ElementPlus.ElMessage.warning('报告尚未生成');
                }
            },
            
            // 加载执行历史
            async loadHistory() {
                try {
                    const response = await fetch(`/ui_automation/api/history/?page=${this.historyPage}&page_size=${this.historyPageSize}`);
                    const data = await response.json();
                    
                    if (data.success) {
                        this.historyList = data.data.history;
                        this.historyTotal = data.data.total;
                        this.historyPage = data.data.page;
                        this.historyPageSize = data.data.page_size;
                    }
                } catch (error) {
                    console.error('加载历史失败:', error);
                }
            },
            
            // 历史分页变化
            handleHistoryPageChange(page) {
                this.historyPage = page;
                this.loadHistory();
            },
            
            // 获取项目ID
            getProjectId() {
                const urlParams = new URLSearchParams(window.location.search);
                const projectId = urlParams.get('project_id');
                return projectId ? parseInt(projectId) : null;
            }
        },
        
        mounted() {
            this.loadModules();
            this.loadCases();
        }
    });
    
    app.use(ElementPlus).mount('#app');
});
