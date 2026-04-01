// 用例库管理页面脚本

// 定义递归模块树组件
const ModuleTreeItem = {
    name: 'ModuleTreeItem',
    props: {
        module: Object,
        selectedModule: String
    },
    emits: ['select', 'create-sub', 'edit', 'delete'],
    data() {
        return {
            expanded: false
        };
    },
    template: `
        <div class="module-tree-node">
            <div class="module-item" 
                 :class="{ active: selectedModule === module.value }" 
                 @click="$emit('select', module.value)">
                <div class="module-item-info">
                    <i v-if="module.children && module.children.length > 0" 
                       class="fas" 
                       :class="expanded ? 'fa-chevron-down' : 'fa-chevron-right'"
                       @click.stop="expanded = !expanded"
                       style="cursor: pointer; width: 16px;"></i>
                    <i v-else class="fas fa-folder" style="width: 16px;"></i>
                    <span v-text="module.name"></span>
                </div>
                <div class="module-item-actions">
                    <el-button type="text" size="small" @click.stop="$emit('create-sub', module)" title="新建子模块">
                        <i class="fas fa-plus"></i>
                    </el-button>
                    <el-button type="text" size="small" @click.stop="$emit('edit', module)" title="编辑">
                        <i class="fas fa-edit"></i>
                    </el-button>
                    <el-button type="text" size="small" @click.stop="$emit('delete', module)" title="删除">
                        <i class="fas fa-trash"></i>
                    </el-button>
                </div>
                <span class="module-item-count">({{ module.count }})</span>
            </div>
            <!-- 递归渲染子模块 -->
            <div v-if="expanded && module.children && module.children.length > 0" class="module-children">
                <module-tree-item 
                    v-for="child in module.children" 
                    :key="child.id" 
                    :module="child"
                    :selected-module="selectedModule"
                    @select="$emit('select', $event)"
                    @create-sub="$emit('create-sub', $event)"
                    @edit="$emit('edit', $event)"
                    @delete="$emit('delete', $event)"
                </module-tree-item>
            </div>
        </div>
    `
};

document.addEventListener('DOMContentLoaded', function() {
    console.log('用例库管理页面初始化');
    
    // 初始化 Vue 应用
    if (typeof Vue !== 'undefined' && typeof ElementPlus !== 'undefined') {
        const { createApp } = Vue;
        
        const app = createApp({
            data() {
                return {
                    // 数据列表
                    cases: [],
                    total: 0,
                    currentPage: 1,
                    pageSize: 20,
                    
                    // 搜索和筛选
                    searchText: '',
                    selectedModule: 'all',
                    filterMaintainer: '',
                    filterPriority: '',
                    filterType: '',
                    
                    // 模块统计
                    moduleStats: [],
                    totalCases: 0,
                    noModuleCount: 0,
                    
                    // 选中项
                    selectedCases: [],
                    
                    // 对话框
                    dialogVisible: false,
                    createModuleDialogVisible: false,
                    editModuleDialogVisible: false,
                    
                    // 新建模块表单
                    newModule: {
                        name: ''
                    },
                    
                    // 编辑模块表单
                    editModule: {
                        id: null,
                        name: ''
                    },
                    
                    // 新建用例表单
                    newCase: {
                        title: '',
                        module_value: '',
                        project_name: '',
                        priority: 'p2',
                        case_type: 'functional',
                        preconditions: '',
                        test_steps_list: [
                            { step_desc: '', expected_result: '' }
                        ],
                        remark: '',
                        continue_create: false
                    },
                    
                    // 模块级联选择器选项
                    moduleCascaderOptions: [],
                    
                    // 表单验证规则
                    caseRules: {
                        title: [
                            { required: true, message: '请输入用例名称', trigger: 'blur' }
                        ],
                        module_value: [
                            { required: true, message: '请选择所属模块', trigger: 'change' }
                        ]
                    }
                };
            },
            
            methods: {
                // 加载用例列表
                async loadCases() {
                    console.log('开始加载用例列表...');
                    try {
                        const params = new URLSearchParams({
                            page: this.currentPage,
                            page_size: this.pageSize,
                            search: this.searchText,
                            module: this.selectedModule !== 'all' && this.selectedModule !== 'no_module' ? this.selectedModule : '',
                            priority: this.filterPriority,
                            type: this.filterType,
                        });
                        
                        // 添加 project_id 参数
                        const urlParams = new URLSearchParams(window.location.search);
                        const projectId = urlParams.get('project_id');
                        if (projectId) {
                            params.append('project_id', projectId);
                            console.log('添加 project_id 参数:', projectId);
                        }
                        
                        console.log('请求参数:', params.toString());
                        const response = await fetch(`/case_library/api/list/?${params}`);
                        console.log('API 响应状态:', response.status);
                        
                        const data = await response.json();
                        console.log('API 响应数据:', data);
                        
                        if (data.success) {
                            // 更新用例列表
                            const cases = data.data.cases || [];
                            
                            // 确保每个用例都有 priority_display 字段
                            cases.forEach(caseItem => {
                                if (!caseItem.priority_display && caseItem.priority) {
                                    // 根据 priority 值生成 priority_display
                                    const priorityMap = {
                                        'p0': 'P0',
                                        'p1': 'P1',
                                        'p2': 'P2',
                                        'p3': 'P3'
                                    };
                                    caseItem.priority_display = priorityMap[caseItem.priority] || 'P2';
                                } else if (!caseItem.priority_display) {
                                    // 如果 priority 也没有，设置为默认值
                                    caseItem.priority_display = 'P2';
                                }
                            });
                            
                            // 更新 Vue 响应式数据
                            this.cases = cases;
                            this.total = data.data.total;
                            this.currentPage = data.data.page;
                            this.pageSize = data.data.page_size;
                            
                            // 加载模块列表
                            try {
                                await this.loadModules();
                                // 更新模块统计数量
                                this.updateModuleCounts();
                            } catch (moduleError) {
                                console.error('加载模块列表失败:', moduleError);
                            }
                        } else {
                            console.error('API 返回失败:', data.message);
                            this.$message.error('加载失败：' + data.message);
                        }
                    } catch (error) {
                        console.error('加载用例列表失败:', error);
                        this.$message.error('加载失败');
                    }
                },
                
                // 更新模块统计数量
                updateModuleCounts() {
                    // 递归更新模块计数
                    const updateCount = (modules) => {
                        modules.forEach(module => {
                            // 统计当前模块的用例数量
                            module.count = this.cases.filter(c => c.module === module.value).length;
                            
                            // 递归更新子模块
                            if (module.children && module.children.length > 0) {
                                updateCount(module.children);
                            }
                        });
                    };
                    
                    updateCount(this.moduleStats);
                    
                    // 更新无所属模块的数量
                    this.noModuleCount = this.cases.filter(c => !c.module).length;
                    // 更新总数
                    this.totalCases = this.total;
                },
                
                // 加载模块列表
                async loadModules() {
                    try {
                        const urlParams = new URLSearchParams(window.location.search);
                        const projectId = urlParams.get('project_id');
                        
                        const params = new URLSearchParams();
                        if (projectId) {
                            params.append('project_id', projectId);
                        }
                        
                        const response = await fetch(`/case_library/api/modules/?${params}`);
                        const data = await response.json();
                        
                        if (data.success) {
                            // 直接使用后端返回的数据结构
                            this.moduleStats = data.data;
                            
                            // 更新总数
                            this.totalCases = this.total;
                            this.noModuleCount = this.cases.filter(c => !c.module).length;
                        } else {
                            this.$message.error('加载失败：' + data.message);
                        }
                    } catch (error) {
                        console.error('加载模块列表失败:', error);
                        this.$message.error('加载失败');
                    }
                },
                

                
                // 选择模块
                selectModule(module) {
                    this.selectedModule = module;
                    this.currentPage = 1;
                    this.loadCases();
                },
                
                // 选择用例
                selectCase(caseItem) {
                    console.log('选择用例:', caseItem);
                    // 可以在这里打开详情对话框
                },
                
                // 全选/取消全选
                toggleSelectAll(event) {
                    if (event.target.checked) {
                        this.selectedCases = this.cases.map(c => c.id);
                    } else {
                        this.selectedCases = [];
                    }
                },
                
                // 分页变化
                handlePageChange(page) {
                    this.currentPage = page;
                    this.loadCases();
                },
                
                // 显示创建模块对话框
                showCreateModuleDialog() {
                    this.newModule = {
                        name: ''
                    };
                    this.createModuleDialogVisible = true;
                },
                
                // 创建模块
                async createModule() {
                    if (!this.newModule.name) {
                        this.$message.error('请输入模块名称');
                        return;
                    }
                    
                    try {
                        // 获取 project_id
                        const urlParams = new URLSearchParams(window.location.search);
                        const projectId = urlParams.get('project_id');
                        
                        const response = await fetch('/case_library/api/modules/create/', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'X-CSRFToken': this.getCookie('csrftoken')
                            },
                            body: JSON.stringify({
                                name: this.newModule.name,
                                project_id: projectId ? parseInt(projectId) : null,
                                parent_id: this.newModule.parent_id || null
                            })
                        });
                        
                        const data = await response.json();
                        
                        if (data.success) {
                            this.$message.success('模块创建成功');
                            this.createModuleDialogVisible = false;
                            // 先重置表单
                            this.newModule = { name: '' };
                            // 重新加载模块列表
                            await this.loadModules();
                            // 选中新创建的模块
                            this.selectModule(data.data.value);
                        } else {
                            this.$message.error('创建失败：' + data.message);
                        }
                    } catch (error) {
                        console.error('创建模块失败:', error);
                        this.$message.error('创建失败');
                    }
                },
                
                // 显示创建子模块对话框
                showCreateSubModule(parentModule) {
                    this.newModule = {
                        name: '',
                        parent_id: parentModule.id
                    };
                    this.createModuleDialogVisible = true;
                },
                
                // 显示编辑模块对话框
                showEditModuleDialog(module) {
                    this.editModule = {
                        id: module.id,
                        name: module.label
                    };
                    this.editModuleDialogVisible = true;
                },
                
                // 更新模块
                async updateModule() {
                    if (!this.editModule.name) {
                        this.$message.error('请输入模块名称');
                        return;
                    }
                    
                    try {
                        const response = await fetch(`/case_library/api/modules/${this.editModule.id}/update/`, {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'X-CSRFToken': this.getCookie('csrftoken')
                            },
                            body: JSON.stringify({
                                name: this.editModule.name
                            })
                        });
                        
                        const data = await response.json();
                        
                        if (data.success) {
                            this.$message.success('模块更新成功');
                            this.editModuleDialogVisible = false;
                            // 重新加载模块列表
                            await this.loadModules();
                        } else {
                            this.$message.error('更新失败：' + data.message);
                        }
                    } catch (error) {
                        console.error('更新模块失败:', error);
                        this.$message.error('更新失败');
                    }
                },
                
                // 删除模块
                async deleteModule(module) {
                    // 确认删除
                    const confirmed = await this.$confirm(`确定要删除模块"${module.label}"吗？`, '提示', {
                        confirmButtonText: '确定',
                        cancelButtonText: '取消',
                        type: 'warning'
                    }).catch(() => false);
                    
                    if (!confirmed) {
                        return;
                    }
                    
                    try {
                        const response = await fetch(`/case_library/api/modules/${module.id}/delete/`, {
                            method: 'POST',
                            headers: {
                                'X-CSRFToken': this.getCookie('csrftoken')
                            }
                        });
                        
                        const data = await response.json();
                        
                        if (data.success) {
                            this.$message.success('模块删除成功');
                            // 重新加载模块列表
                            await this.loadModules();
                            // 如果删除的是当前选中的模块，切换到“所有用例”
                            if (this.selectedModule === module.value) {
                                this.selectModule('all');
                            }
                        } else {
                            this.$message.error('删除失败：' + data.message);
                        }
                    } catch (error) {
                        console.error('删除模块失败:', error);
                        this.$message.error('删除失败');
                    }
                },
                
                // 显示创建用例对话框
                async showCreateDialog() {
                    // 重置表单
                    this.newCase = {
                        title: '',
                        module_value: '',
                        project_name: '',
                        priority: 'p2',
                        case_type: 'functional',
                        preconditions: '',
                        test_steps_list: [
                            { step_desc: '', expected_result: '' }
                        ],
                        remark: '',
                        continue_create: false
                    };
                    
                    // 获取项目名称
                    const urlParams = new URLSearchParams(window.location.search);
                    const projectId = urlParams.get('project_id');
                    if (projectId) {
                        // 从项目列表获取项目名称（这里简化处理，实际应该查询项目信息）
                        this.newCase.project_name = '项目' + projectId;
                    }
                    
                    // 加载模块级联选项
                    await this.loadModuleCascaderOptions();
                    
                    this.dialogVisible = true;
                    
                    // 对话框打开后，只增大右侧字段的间距
                    this.$nextTick(() => {
                        setTimeout(() => {
                            // 设置间距的函数
                            const setFormItemSpacing = () => {
                                const dialog = document.querySelector('.el-dialog');
                                if (dialog) {
                                    const labels = dialog.querySelectorAll('.el-form-item__label');
                                    labels.forEach(label => {
                                        const labelText = label.textContent.trim();
                                        if (['所属用例库', '所属模块', '用例类型', '优先级'].includes(labelText)) {
                                            const formItem = label.closest('.el-form-item');
                                            if (formItem) {
                                                formItem.style.marginBottom = '80px';
                                            }
                                        }
                                    });
                                }
                            };
                            
                            // 首次设置
                            setFormItemSpacing();
                            
                            // 使用 MutationObserver 监听 DOM 变化，自动重新应用间距
                            const dialog = document.querySelector('.el-dialog');
                            if (dialog) {
                                const observer = new MutationObserver(() => {
                                    setFormItemSpacing();
                                });
                                
                                observer.observe(dialog, {
                                    childList: true,
                                    subtree: true,
                                    attributes: true,
                                    attributeFilter: ['class', 'style']
                                });
                                
                                // 保存 observer 以便后续清理
                                this.formItemObserver = observer;
                            }
                        }, 200);
                    });
                },
                
                // 加载模块级联选择器选项
                async loadModuleCascaderOptions() {
                    try {
                        const urlParams = new URLSearchParams(window.location.search);
                        const projectId = urlParams.get('project_id');
                        
                        const params = new URLSearchParams();
                        if (projectId) {
                            params.append('project_id', projectId);
                        }
                        
                        const response = await fetch(`/case_library/api/modules/?${params}`);
                        const data = await response.json();
                        
                        if (data.success) {
                            this.moduleCascaderOptions = data.data;
                        }
                    } catch (error) {
                        console.error('加载模块级联选项失败:', error);
                    }
                },
                
                // 添加步骤
                addStep() {
                    this.newCase.test_steps_list.push({
                        step_desc: '',
                        expected_result: ''
                    });
                },
                
                // 删除步骤
                removeStep(index) {
                    if (this.newCase.test_steps_list.length <= 1) {
                        this.$message.warning('至少保留一个步骤');
                        return;
                    }
                    this.newCase.test_steps_list.splice(index, 1);
                },
                
                // 关闭对话框时清理 Observer
                handleCloseDialog() {
                    if (this.formItemObserver) {
                        this.formItemObserver.disconnect();
                        this.formItemObserver = null;
                    }
                    this.dialogVisible = false;
                },
                
                // 格式化文本（简单实现）
                formatText(command) {
                    document.execCommand(command, false, null);
                },
                
                // 创建用例
                async createCase() {
                    // 验证表单
                    if (!this.newCase.title) {
                        this.$message.error('请输入用例名称');
                        return;
                    }
                    if (!this.newCase.module_value) {
                        this.$message.error('请选择所属模块');
                        return;
                    }
                    if (this.newCase.test_steps_list.length === 0) {
                        this.$message.error('请至少添加一个步骤');
                        return;
                    }
                    
                    try {
                        // 准备提交数据
                        const submitData = {
                            title: this.newCase.title,
                            module: this.newCase.module_value,
                            priority: this.newCase.priority,
                            case_type: this.newCase.case_type,
                            preconditions: this.newCase.preconditions,
                            test_steps: JSON.stringify(this.newCase.test_steps_list),
                            expected_results: this.newCase.test_steps_list.map(s => s.expected_result).join('\n'),
                            remark: this.newCase.remark,
                            project_id: this.getProjectId()
                        };
                        
                        const response = await fetch('/case_library/api/create/', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'X-CSRFToken': this.getCookie('csrftoken')
                            },
                            body: JSON.stringify(submitData)
                        });
                        
                        const data = await response.json();
                        
                        if (data.success) {
                            this.$message.success('用例创建成功');
                            
                            if (this.newCase.continue_create) {
                                // 继续新建下一个：重置表单但不关闭对话框
                                this.newCase = {
                                    title: '',
                                    module_value: this.newCase.module_value,
                                    project_name: this.newCase.project_name,
                                    priority: 'p2',
                                    case_type: 'functional',
                                    preconditions: '',
                                    test_steps_list: [
                                        { step_desc: '', expected_result: '' }
                                    ],
                                    remark: '',
                                    continue_create: true
                                };
                                // 重新加载用例列表，确保新创建的用例能够显示
                                this.loadCases();
                            } else {
                                this.dialogVisible = false;
                                this.loadCases();
                            }
                        } else {
                            this.$message.error('创建失败：' + data.message);
                        }
                    } catch (error) {
                        console.error('创建用例失败:', error);
                        this.$message.error('创建失败');
                    }
                },
                
                // 获取项目 ID
                getProjectId() {
                    const urlParams = new URLSearchParams(window.location.search);
                    const projectId = urlParams.get('project_id');
                    return projectId ? parseInt(projectId) : null;
                },
                
                // 导出用例
                exportCases() {
                    this.$message.info('导出功能开发中');
                },
                
                // 获取 Cookie
                getCookie(name) {
                    let cookieValue = null;
                    if (document.cookie && document.cookie !== '') {
                        const cookies = document.cookie.split(';');
                        for (let i = 0; i < cookies.length; i++) {
                            const cookie = cookies[i].trim();
                            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                                break;
                            }
                        }
                    }
                    return cookieValue;
                }
            },
            
            mounted() {
                this.loadCases();
            }
        });
        
        // 注册递归组件
        app.component('module-tree-item', ModuleTreeItem);
        
        // 挂载应用
        const vm = app.use(ElementPlus).mount('#app');
        
        // 暴露 Vue 应用实例给全局使用
        window.caseLibraryApp = vm;
    }
});
