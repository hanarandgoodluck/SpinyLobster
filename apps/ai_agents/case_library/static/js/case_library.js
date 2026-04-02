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
        return { expanded: false };
    },
    template: `
        <div class="module-tree-node">
            <div class="module-item" :class="{ active: selectedModule === module.value }" @click="$emit('select', module.value)">
                <div class="module-item-info">
                    <i v-if="module.children?.length" class="fas" :class="expanded ? 'fa-chevron-down' : 'fa-chevron-right'"
                       @click.stop="expanded = !expanded" style="cursor: pointer; width: 16px;"></i>
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
            <div v-if="expanded && module.children?.length" class="module-children">
                <module-tree-item v-for="child in module.children" :key="child.id" :module="child"
                    :selected-module="selectedModule" @select="$emit('select', $event)"
                    @create-sub="$emit('create-sub', $event)" @edit="$emit('edit', $event)" @delete="$emit('delete', $event)" />
            </div>
        </div>
    `
};

document.addEventListener('DOMContentLoaded', () => {
    if (typeof Vue === 'undefined' || typeof ElementPlus === 'undefined') return;

    const { createApp } = Vue;
    const PRIORITY_MAP = { p0: 'P0', p1: 'P1', p2: 'P2', p3: 'P3' };

    const app = createApp({
        data() {
            return {
                cases: [],
                total: 0,
                currentPage: 1,
                pageSize: 20,
                searchText: '',
                selectedModule: 'all',
                moduleStats: [],
                totalCases: 0,
                noModuleCount: 0,
                selectedCases: [],
                dialogVisible: false,
                editDialogVisible: false,
                createModuleDialogVisible: false,
                editModuleDialogVisible: false,
                detailDialogVisible: false,
                currentCase: null,
                editCaseData: {},
                newModule: { name: '' },
                editModule: { id: null, name: '' },
                newCase: this.getDefaultCase(),
                moduleCascaderOptions: [],
                formItemObserver: null,
                caseRules: {
                    title: [{ required: true, message: '请输入用例名称', trigger: 'blur' }],
                    module_value: [{ required: true, message: '请选择所属模块', trigger: 'change' }]
                }
            };
        },

        methods: {
            getDefaultCase() {
                return {
                    title: '',
                    module_value: '',
                    project_name: '',
                    priority: 'p2',
                    case_type: 'functional',
                    preconditions: '',
                    test_steps_list: [{ step_desc: '', expected_result: '' }],
                    remark: '',
                    continue_create: false
                };
            },

            getProjectId() {
                const urlParams = new URLSearchParams(window.location.search);
                const projectId = urlParams.get('project_id');
                return projectId ? parseInt(projectId) : null;
            },

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

            async loadCases() {
                try {
                    const params = new URLSearchParams({
                        page: this.currentPage,
                        page_size: this.pageSize,
                        search: this.searchText,
                        module: this.selectedModule !== 'all' && this.selectedModule !== 'no_module' ? this.selectedModule : '',
                    });

                    const projectId = this.getProjectId();
                    if (projectId) params.append('project_id', projectId);

                    const data = await this.fetchApi(`/case_library/api/list/?${params}`);

                    if (data.success) {
                        this.cases = (data.data.cases || []).map(caseItem => ({
                            ...caseItem,
                            priority_display: caseItem.priority_display || PRIORITY_MAP[caseItem.priority] || 'P2'
                        }));
                        this.total = data.data.total;
                        this.currentPage = data.data.page;
                        this.pageSize = data.data.page_size;

                        await this.loadModules();
                        this.updateModuleCounts();
                    } else {
                        this.$message.error('加载失败：' + data.message);
                    }
                } catch (error) {
                    console.error('加载用例列表失败:', error);
                    this.$message.error('加载失败');
                }
            },

            updateModuleCounts() {
                const updateCount = (modules) => {
                    modules.forEach(module => {
                        module.count = this.cases.filter(c => c.module === module.value).length;
                        if (module.children?.length) updateCount(module.children);
                    });
                };
                updateCount(this.moduleStats);
                this.noModuleCount = this.cases.filter(c => !c.module).length;
                this.totalCases = this.total;
            },

            async loadModules() {
                try {
                    const projectId = this.getProjectId();
                    const params = projectId ? new URLSearchParams({ project_id: projectId }) : '';
                    const data = await this.fetchApi(`/case_library/api/modules/?${params}`);

                    if (data.success) {
                        this.moduleStats = data.data;
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

            selectModule(module) {
                this.selectedModule = module;
                this.currentPage = 1;
                this.loadCases();
            },

            async selectCase(caseItem) {
                await this.showCaseDetail(caseItem.id);
            },

            async showCaseDetail(caseId) {
                try {
                    const data = await this.fetchApi(`/case_library/api/detail/${caseId}/`);
                    if (data.success) {
                        this.currentCase = data.data;
                        this.detailDialogVisible = true;
                    } else {
                        this.$message.error('加载失败：' + data.message);
                    }
                } catch (error) {
                    console.error('加载用例详情失败:', error);
                    this.$message.error('加载失败');
                }
            },

            async showEditDialog(caseId) {
                try {
                    const data = await this.fetchApi(`/case_library/api/detail/${caseId}/`);
                    if (data.success) {
                        this.editCaseData = {
                            id: data.data.id,
                            title: data.data.title,
                            module_value: data.data.module || '',
                            project_name: data.data.project_name || '',
                            priority: data.data.priority || 'p2',
                            case_type: data.data.case_type || 'functional',
                            preconditions: data.data.preconditions || '',
                            test_steps_list: data.data.test_steps_list || [{ step_desc: '', expected_result: '' }],
                            remark: data.data.remark || '',
                            project_id: data.data.project_id
                        };
                        this.editDialogVisible = true;
                    } else {
                        this.$message.error('加载失败：' + data.message);
                    }
                } catch (error) {
                    console.error('加载用例详情失败:', error);
                    this.$message.error('加载失败');
                }
            },

            async showEditDialogFromTable(caseId) {
                await this.showEditDialog(caseId);
            },

            async updateCase() {
                if (!this.editCaseData.title) {
                    this.$message.error('请输入用例名称');
                    return;
                }
                if (!this.editCaseData.module_value) {
                    this.$message.error('请选择所属模块');
                    return;
                }

                try {
                    const data = await this.fetchApi(`/case_library/api/update/${this.editCaseData.id}/`, {
                        method: 'PUT',
                        body: JSON.stringify({
                            title: this.editCaseData.title,
                            module: this.editCaseData.module_value,
                            priority: this.editCaseData.priority,
                            case_type: this.editCaseData.case_type,
                            preconditions: this.editCaseData.preconditions,
                            test_steps: JSON.stringify(this.editCaseData.test_steps_list),
                            expected_results: this.editCaseData.test_steps_list.map(s => s.expected_result).join('\n'),
                            remark: this.editCaseData.remark,
                            project_id: this.editCaseData.project_id
                        })
                    });

                    if (data.success) {
                        this.$message.success('用例更新成功');
                        this.editDialogVisible = false;
                        await this.loadCases();
                    } else {
                        this.$message.error('更新失败：' + data.message);
                    }
                } catch (error) {
                    console.error('更新用例失败:', error);
                    this.$message.error('更新失败');
                }
            },

            async deleteCase(caseId, caseTitle, dialogToClose = null) {
                if (!caseId) {
                    this.$message.warning('用例信息不存在');
                    return;
                }

                try {
                    await this.$confirm(`确定要删除用例"${caseTitle}"吗？`, '警告', {
                        confirmButtonText: '确定',
                        cancelButtonText: '取消',
                        type: 'warning'
                    });

                    const data = await this.fetchApi('/case_library/api/delete/', {
                        method: 'DELETE',
                        body: JSON.stringify({ id: caseId })
                    });

                    if (data.success) {
                        this.$message.success('用例删除成功');
                        if (dialogToClose) this[dialogToClose] = false;
                        await this.loadCases();
                    } else {
                        this.$message.error('删除失败：' + data.message);
                    }
                } catch (error) {
                    if (error !== 'cancel') {
                        console.error('删除用例失败:', error);
                        this.$message.error('删除失败');
                    }
                }
            },

            deleteCurrentCase() {
                this.deleteCase(this.currentCase?.id, this.currentCase?.title, 'detailDialogVisible');
            },

            deleteCurrentEditCase() {
                this.deleteCase(this.editCaseData?.id, this.editCaseData?.title, 'editDialogVisible');
            },

            deleteCaseFromTable(caseId, caseTitle) {
                this.deleteCase(caseId, caseTitle);
            },

            toggleSelectAll(event) {
                event.stopPropagation();
                this.selectedCases = event.target.checked ? this.cases.map(c => c.id) : [];
            },

            handlePageChange(page) {
                this.currentPage = page;
                this.loadCases();
            },

            showCreateModuleDialog() {
                this.newModule = { name: '' };
                this.createModuleDialogVisible = true;
            },

            async createModule() {
                if (!this.newModule.name) {
                    this.$message.error('请输入模块名称');
                    return;
                }

                try {
                    const data = await this.fetchApi('/case_library/api/modules/create/', {
                        method: 'POST',
                        body: JSON.stringify({
                            name: this.newModule.name,
                            project_id: this.getProjectId(),
                            parent_id: this.newModule.parent_id || null
                        })
                    });

                    if (data.success) {
                        this.$message.success('模块创建成功');
                        this.createModuleDialogVisible = false;
                        this.newModule = { name: '' };
                        await this.loadModules();
                        this.selectModule(data.data.value);
                    } else {
                        this.$message.error('创建失败：' + data.message);
                    }
                } catch (error) {
                    console.error('创建模块失败:', error);
                    this.$message.error('创建失败');
                }
            },

            showCreateSubModule(parentModule) {
                this.newModule = { name: '', parent_id: parentModule.id };
                this.createModuleDialogVisible = true;
            },

            showEditModuleDialog(module) {
                this.editModule = { id: module.id, name: module.label };
                this.editModuleDialogVisible = true;
            },

            async updateModule() {
                if (!this.editModule.name) {
                    this.$message.error('请输入模块名称');
                    return;
                }

                try {
                    const data = await this.fetchApi(`/case_library/api/modules/${this.editModule.id}/update/`, {
                        method: 'POST',
                        body: JSON.stringify({ name: this.editModule.name })
                    });

                    if (data.success) {
                        this.$message.success('模块更新成功');
                        this.editModuleDialogVisible = false;
                        await this.loadModules();
                    } else {
                        this.$message.error('更新失败：' + data.message);
                    }
                } catch (error) {
                    console.error('更新模块失败:', error);
                    this.$message.error('更新失败');
                }
            },

            async deleteModule(module) {
                try {
                    await this.$confirm(`确定要删除模块"${module.label}"吗？`, '提示', {
                        confirmButtonText: '确定',
                        cancelButtonText: '取消',
                        type: 'warning'
                    });

                    const data = await this.fetchApi(`/case_library/api/modules/${module.id}/delete/`, {
                        method: 'POST'
                    });

                    if (data.success) {
                        this.$message.success('模块删除成功');
                        await this.loadModules();
                        if (this.selectedModule === module.value) {
                            this.selectModule('all');
                        }
                    } else {
                        this.$message.error('删除失败：' + data.message);
                    }
                } catch (error) {
                    if (error !== 'cancel') {
                        console.error('删除模块失败:', error);
                        this.$message.error('删除失败');
                    }
                }
            },

            async showCreateDialog() {
                this.newCase = this.getDefaultCase();
                const projectId = this.getProjectId();
                if (projectId) this.newCase.project_name = '项目' + projectId;

                await this.loadModuleCascaderOptions();
                this.dialogVisible = true;
                this.setupFormItemSpacing();
            },

            async loadModuleCascaderOptions() {
                try {
                    const projectId = this.getProjectId();
                    const params = projectId ? new URLSearchParams({ project_id: projectId }) : '';
                    const data = await this.fetchApi(`/case_library/api/modules/?${params}`);
                    if (data.success) this.moduleCascaderOptions = data.data;
                } catch (error) {
                    console.error('加载模块级联选项失败:', error);
                }
            },

            setupFormItemSpacing() {
                this.$nextTick(() => {
                    setTimeout(() => {
                        const setSpacing = () => {
                            const dialog = document.querySelector('.el-dialog');
                            if (!dialog) return;
                            dialog.querySelectorAll('.el-form-item__label').forEach(label => {
                                if (['所属用例库', '所属模块', '用例类型', '优先级'].includes(label.textContent.trim())) {
                                    const formItem = label.closest('.el-form-item');
                                    if (formItem) formItem.style.marginBottom = '80px';
                                }
                            });
                        };

                        setSpacing();

                        const dialog = document.querySelector('.el-dialog');
                        if (dialog) {
                            this.formItemObserver = new MutationObserver(setSpacing);
                            this.formItemObserver.observe(dialog, { childList: true, subtree: true, attributes: true, attributeFilter: ['class', 'style'] });
                        }
                    }, 200);
                });
            },

            addStep(isEdit = false) {
                const target = isEdit ? this.editCaseData : this.newCase;
                target.test_steps_list.push({ step_desc: '', expected_result: '' });
            },

            removeStep(index, isEdit = false) {
                const target = isEdit ? this.editCaseData : this.newCase;
                if (target.test_steps_list.length <= 1) {
                    this.$message.warning('至少保留一个步骤');
                    return;
                }
                target.test_steps_list.splice(index, 1);
            },

            handleCloseDialog() {
                this.formItemObserver?.disconnect();
                this.formItemObserver = null;
                this.dialogVisible = false;
            },

            async createCase() {
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
                    const data = await this.fetchApi('/case_library/api/create/', {
                        method: 'POST',
                        body: JSON.stringify({
                            title: this.newCase.title,
                            module: this.newCase.module_value,
                            priority: this.newCase.priority,
                            case_type: this.newCase.case_type,
                            preconditions: this.newCase.preconditions,
                            test_steps: JSON.stringify(this.newCase.test_steps_list),
                            expected_results: this.newCase.test_steps_list.map(s => s.expected_result).join('\n'),
                            remark: this.newCase.remark,
                            project_id: this.getProjectId()
                        })
                    });

                    if (data.success) {
                        this.$message.success('用例创建成功');

                        if (this.newCase.continue_create) {
                            this.newCase = {
                                ...this.getDefaultCase(),
                                module_value: this.newCase.module_value,
                                project_name: this.newCase.project_name,
                                continue_create: true
                            };
                            await this.loadCases();
                        } else {
                            this.dialogVisible = false;
                            await this.loadCases();
                        }
                    } else {
                        this.$message.error('创建失败：' + data.message);
                    }
                } catch (error) {
                    console.error('创建用例失败:', error);
                    this.$message.error('创建失败');
                }
            },

            exportCases() {
                this.$message.info('导出功能开发中');
            }
        },

        mounted() {
            this.loadCases();
        }
    });

    app.component('module-tree-item', ModuleTreeItem);
    window.caseLibraryApp = app.use(ElementPlus).mount('#app');
});
