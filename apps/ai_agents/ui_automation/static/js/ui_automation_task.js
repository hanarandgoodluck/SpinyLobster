const { createApp, ref, reactive, onMounted, computed } = Vue;

document.addEventListener('DOMContentLoaded', function() {
    const app = createApp({
        data() {
            return {
                // 任务列表
                tasks: [],
                loading: false,
                
                // 对话框
                dialogVisible: false,
                isEdit: false,
                submitting: false,
                
                // 表单
                form: {
                    id: null,
                    name: '',
                    description: '',
                    task_type: 'web',
                    config: {
                        url: '',
                        username: '',
                        password: '',
                        manual_captcha: false,
                        base_url: '',
                        token: ''
                    },
                    case_ids: [],
                    use_multimodal: false,
                    llm_provider: 'deepseek',
                    project_id: null
                },
                
                // 表单验证规则
                rules: {
                    name: [
                        { required: true, message: '请输入任务名称', trigger: 'blur' }
                    ],
                    task_type: [
                        { required: true, message: '请选择测试类型', trigger: 'change' }
                    ]
                },
                
                // 模块树和用例
                moduleTree: [],
                allCases: [],
                filteredCases: [],
                selectedModule: '',
                
                // 执行历史
                historyDialogVisible: false,
                historyList: [],
                historyPage: 1,
                historyPageSize: 10,
                historyTotal: 0,
                currentTaskId: null,
                
                // 下拉菜单
                activeDropdown: null
            };
        },
        
        methods: {
            // 获取Cookie
            getCookie(name) {
                const cookies = document.cookie.split(';');
                for (const cookie of cookies) {
                    const [key, value] = cookie.trim().split('=');
                    if (key === name) {
                        return decodeURIComponent(value);
                    }
                }
                return '';
            },
            
            // API请求封装
            async fetchApi(url, options = {}) {
                const defaultOptions = {
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCookie('csrftoken')
                    }
                };
                
                const response = await fetch(url, { ...defaultOptions, ...options });
                return await response.json();
            },
            
            // 加载任务列表
            async loadTasks() {
                this.loading = true;
                try {
                    const projectId = new URLSearchParams(window.location.search).get('project_id');
                    const params = new URLSearchParams({
                        page: 1,
                        page_size: 100
                    });
                    
                    if (projectId) {
                        params.append('project_id', projectId);
                    }
                    
                    const data = await this.fetchApi(`/ui_automation/api/tasks/?${params}`);
                    
                    if (data.success) {
                        this.tasks = data.data.tasks;
                    } else {
                        ElementPlus.ElMessage.error('加载任务列表失败：' + data.message);
                    }
                } catch (error) {
                    console.error('加载任务列表失败:', error);
                    ElementPlus.ElMessage.error('加载失败');
                } finally {
                    this.loading = false;
                }
            },
            
            // 显示创建对话框
            async showCreateDialog() {
                this.isEdit = false;
                this.resetForm();
                // 从URL获取project_id并设置到form中
                const projectId = new URLSearchParams(window.location.search).get('project_id');
                if (projectId) {
                    this.form.project_id = projectId;
                }
                await this.loadModuleTree();
                await this.loadAllCases();
                this.dialogVisible = true;
            },
            
            // 编辑任务
            async editTask(task) {
                this.closeAllDropdowns();
                this.isEdit = true;
                
                try {
                    const data = await this.fetchApi(`/ui_automation/api/tasks/${task.id}/`);
                    
                    if (data.success) {
                        const taskData = data.data;
                        this.form = {
                            id: taskData.id,
                            name: taskData.name,
                            description: taskData.description,
                            task_type: taskData.task_type,
                            config: taskData.config || {},
                            case_ids: taskData.cases.map(c => c.id),
                            use_multimodal: taskData.use_multimodal,
                            llm_provider: taskData.llm_provider
                        };
                        
                        await this.loadModuleTree();
                        await this.loadAllCases();
                        this.dialogVisible = true;
                    }
                } catch (error) {
                    console.error('加载任务详情失败:', error);
                    ElementPlus.ElMessage.error('加载任务详情失败');
                }
            },
            
            // 提交表单
            async submitForm() {
                try {
                    this.submitting = true;
                    
                    const url = this.isEdit 
                        ? `/ui_automation/api/tasks/${this.form.id}/update/`
                        : '/ui_automation/api/tasks/create/';
                    
                    const method = this.isEdit ? 'PUT' : 'POST';
                    
                    const data = await this.fetchApi(url, {
                        method: method,
                        body: JSON.stringify(this.form)
                    });
                    
                    if (data.success) {
                        ElementPlus.ElMessage.success(this.isEdit ? '更新成功' : '创建成功');
                        this.dialogVisible = false;
                        await this.loadTasks();
                    } else {
                        ElementPlus.ElMessage.error(data.message);
                    }
                } catch (error) {
                    console.error('提交失败:', error);
                    ElementPlus.ElMessage.error('操作失败');
                } finally {
                    this.submitting = false;
                }
            },
            
            // 删除任务
            async deleteTask(task) {
                this.closeAllDropdowns();
                
                try {
                    await ElementPlus.ElMessageBox.confirm(
                        `确定要删除任务 "${task.name}" 吗？`,
                        '警告',
                        {
                            confirmButtonText: '确定',
                            cancelButtonText: '取消',
                            type: 'warning'
                        }
                    );
                    
                    const data = await this.fetchApi(`/ui_automation/api/tasks/${task.id}/delete/`, {
                        method: 'DELETE'
                    });
                    
                    if (data.success) {
                        ElementPlus.ElMessage.success('删除成功');
                        await this.loadTasks();
                    } else {
                        ElementPlus.ElMessage.error(data.message);
                    }
                } catch (error) {
                    if (error !== 'cancel') {
                        console.error('删除失败:', error);
                        ElementPlus.ElMessage.error('删除失败');
                    }
                }
            },
            
            // 执行任务
            async executeTask(task) {
                try {
                    const data = await this.fetchApi(`/ui_automation/api/tasks/${task.id}/execute/`, {
                        method: 'POST'
                    });
                    
                    if (data.success) {
                        ElementPlus.ElMessage.success(`任务 "${task.name}" 已开始执行，共 ${data.case_count} 个用例`);
                        // 3秒后刷新任务列表以更新状态
                        setTimeout(() => this.loadTasks(), 3000);
                    } else {
                        ElementPlus.ElMessage.error(data.message);
                    }
                } catch (error) {
                    console.error('执行任务失败:', error);
                    ElementPlus.ElMessage.error('执行失败');
                }
            },
            
            // 查看报告
            async viewReport(task) {
                if (!task.last_run_time) {
                    ElementPlus.ElMessage.warning('该任务尚未执行过');
                    return;
                }
                
                try {
                    // 获取任务的最新执行记录
                    const data = await this.fetchApi(
                        `/ui_automation/api/tasks/${task.id}/history/?page=1&page_size=1`
                    );
                    
                    if (data.success && data.data.history && data.data.history.length > 0) {
                        const latestLog = data.data.history[0];
                        if (latestLog.report_url) {
                            // 打开报告
                            window.open(latestLog.report_url, '_blank');
                        } else {
                            ElementPlus.ElMessage.warning('报告尚未生成，请稍后再试');
                        }
                    } else {
                        ElementPlus.ElMessage.warning('暂无执行记录');
                    }
                } catch (error) {
                    console.error('获取报告链接失败:', error);
                    ElementPlus.ElMessage.error('获取报告失败');
                }
            },
            
            // 查看执行历史
            async viewHistory(task) {
                this.closeAllDropdowns();
                this.currentTaskId = task.id;
                this.historyPage = 1;
                this.historyDialogVisible = true;
                await this.loadHistory();
            },
            
            // 加载执行历史
            async loadHistory() {
                try {
                    const data = await this.fetchApi(
                        `/ui_automation/api/tasks/${this.currentTaskId}/history/?page=${this.historyPage}&page_size=${this.historyPageSize}`
                    );
                    
                    if (data.success) {
                        this.historyList = data.data.history;
                        this.historyTotal = data.data.total;
                    }
                } catch (error) {
                    console.error('加载执行历史失败:', error);
                }
            },
            
            // 打开报告
            openReport(reportUrl) {
                if (reportUrl) {
                    window.open(reportUrl, '_blank');
                }
            },
            
            // 加载模块树
            async loadModuleTree() {
                try {
                    const projectId = new URLSearchParams(window.location.search).get('project_id');
                    const params = projectId ? `?project_id=${projectId}` : '';
                    const data = await this.fetchApi(`/case_library/api/modules/${params}`);
                    
                    if (data.success) {
                        // 后端已经返回了完整的树形结构，直接使用
                        this.moduleTree = data.data;
                    }
                } catch (error) {
                    console.error('加载模块树失败:', error);
                }
            },
            

            
            // 加载所有用例
            async loadAllCases() {
                try {
                    const projectId = new URLSearchParams(window.location.search).get('project_id');
                    const params = new URLSearchParams({
                        page: 1,
                        page_size: 1000
                    });
                    
                    if (projectId) {
                        params.append('project_id', projectId);
                    }
                    
                    const data = await this.fetchApi(`/case_library/api/list/?${params}`);
                    
                    if (data.success) {
                        this.allCases = data.data.cases;
                        this.filteredCases = []; // 默认不展示用例
                    }
                } catch (error) {
                    console.error('加载用例失败:', error);
                }
            },
            
            // 按模块筛选用例
            filterCasesByModule(moduleValue) {
                if (!moduleValue) {
                    this.filteredCases = [];
                    return;
                }
                
                // 递归查找目标模块及其所有子模块的 value
                const collectValues = (modules) => {
                    for (const mod of modules) {
                        if (mod.value === moduleValue) {
                            // 找到目标模块，收集它和所有子模块的 value
                            let values = [];
                            const traverse = (m) => {
                                values.push(m.value);
                                if (m.children && m.children.length > 0) {
                                    m.children.forEach(traverse);
                                }
                            };
                            traverse(mod);
                            return values;
                        }
                        if (mod.children && mod.children.length > 0) {
                            const result = collectValues(mod.children);
                            if (result.length > 0) return result;
                        }
                    }
                    return [];
                };
                
                const targetModuleValues = collectValues(this.moduleTree);
                if (targetModuleValues.length > 0) {
                    this.filteredCases = this.allCases.filter(c => targetModuleValues.includes(c.module));
                } else {
                    this.filteredCases = [];
                }
            },
            
            // 重置表单
            resetForm() {
                this.form = {
                    id: null,
                    name: '',
                    description: '',
                    task_type: 'web',
                    config: {
                        url: '',
                        username: '',
                        password: '',
                        manual_captcha: false,
                        base_url: '',
                        token: ''
                    },
                    case_ids: [],
                    use_multimodal: false,
                    llm_provider: 'deepseek',
                    project_id: null
                };
                this.selectedModule = '';
                this.filteredCases = [];
            },
            
            // 切换下拉菜单
            toggleDropdown(taskId) {
                if (this.activeDropdown === taskId) {
                    this.activeDropdown = null;
                } else {
                    this.activeDropdown = taskId;
                }
            },
            
            // 关闭所有下拉菜单
            closeAllDropdowns() {
                this.activeDropdown = null;
            },
            
            // 获取状态标签类型
            getStatusType(status) {
                const typeMap = {
                    'passed': 'success',
                    'failed': 'danger',
                    'pending': 'warning',
                    'running': 'info',
                    'error': 'danger'
                };
                return typeMap[status] || 'info';
            }
        },
        
        mounted() {
            // 配置 Element Plus 中文语言包
            if (ElementPlus && ElementPlus.lang && ElementPlus.lang.zhCn) {
                ElementPlus.lang.zhCn.el.pagination.total = '条数';
            }
            
            this.loadTasks();
            
            // 点击外部关闭下拉菜单
            document.addEventListener('click', () => {
                this.closeAllDropdowns();
            });
        }
    });
    
    app.use(ElementPlus);
    app.mount('#app');
});
