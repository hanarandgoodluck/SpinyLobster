// 测试用例生成页面专用脚本

document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM 加载完成，初始化测试用例生成页面');
    
    // 获取必要的 DOM 元素
    const generateForm = document.getElementById('generate-form');
    const generateButton = document.getElementById('generate-button');
    const loadingIndicator = document.getElementById('loading-indicator');
    
    if (!generateForm) {
        console.error('找不到表单元素 #generate-form');
        return;
    }
    
    // 显示通知消息的辅助函数
    window.showNotification = function(message, type = 'info') {
        let notificationContainer = document.getElementById('notification-container');
        if (!notificationContainer) {
            notificationContainer = document.createElement('div');
            notificationContainer.id = 'notification-container';
            notificationContainer.style.position = 'fixed';
            notificationContainer.style.top = '20px';
            notificationContainer.style.right = '20px';
            notificationContainer.style.zIndex = '9999';
            document.body.appendChild(notificationContainer);
        }
        
        const notification = document.createElement('div');
        notification.className = `alert alert-${type === 'error' ? 'danger' : type}`;
        notification.style.minWidth = '300px';
        notification.style.marginBottom = '10px';
        notification.style.boxShadow = '0 4px 6px rgba(0,0,0,0.1)';
        notification.textContent = message;
        
        const closeButton = document.createElement('button');
        closeButton.type = 'button';
        closeButton.className = 'close';
        closeButton.style.float = 'right';
        closeButton.style.marginLeft = '10px';
        closeButton.innerHTML = '&times;';
        closeButton.onclick = function() {
            notification.remove();
        };
        notification.appendChild(closeButton);
        
        notificationContainer.appendChild(notification);
        
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 5000);
    };
    
    // 全选/取消全选复选框的辅助函数
    window.toggleAllCheckboxes = function(selector, selectAll) {
        const checkboxes = document.querySelectorAll(selector);
        checkboxes.forEach(checkbox => {
            checkbox.checked = selectAll;
        });
    };
    
    // CSRF Token 获取函数
    function getCookie(name) {
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
    
    // 表单提交处理
    generateForm.addEventListener('submit', function(e) {
        e.preventDefault();
        console.log('表单提交事件触发');
        
        // 获取必要的 DOM 元素
        const loadingIndicator = document.getElementById('loading-indicator');
        const generateButton = document.getElementById('generate-button');
        const resultContainer = document.getElementById('result-container');
        
        // 尝试从Vue实例获取requirements
        let inputTextValue = '';
        const app = document.querySelector('#app')?._vnode?.component?.proxy;
        if (app && app.requirements) {
            inputTextValue = app.requirements.trim();
        } else if (document.getElementById('input-text')) {
            // 回退方案：尝试从DOM元素获取
            inputTextValue = document.getElementById('input-text').value?.trim() || '';
        }
        
        // 尝试从 Vue 实例获取选中的测试用例设计方法和用例类型
        let selectedDesignMethods = [];
        let selectedCaseCategories = [];
        let caseCountValue = 'auto';
        const vueApp = document.querySelector('#app')?._vnode?.component?.proxy;
                
        if (vueApp) {
            selectedDesignMethods = vueApp.caseDesignMethods || [];
            selectedCaseCategories = vueApp.caseCategories || [];
            caseCountValue = vueApp.caseCount || 'auto';
        } else {
            // 回退方案：尝试从 DOM 元素获取
            const designMethodsCheckboxes = document.querySelectorAll('.case-design-method:checked');
            selectedDesignMethods = Array.from(designMethodsCheckboxes).map(cb => cb.value);
                    
            const caseCategoriesCheckboxes = document.querySelectorAll('.case-category:checked');
            selectedCaseCategories = Array.from(caseCategoriesCheckboxes).map(cb => cb.value);
                    
            caseCountValue = document.getElementById('case_count')?.value || 'auto';
        }
        
        if (!inputTextValue) {
            showNotification('请输入需求描述', 'error');
            return;
        }
        
        // 如果没有选择任何方法或类型，给出提示
        if (selectedDesignMethods.length === 0) {
            if (!confirm('您没有选择任何测试用例设计方法，是否继续？')) {
                if (loadingIndicator) loadingIndicator.style.display = 'none';
                if (generateButton) generateButton.disabled = false;
                return;
            }
        }
        
        if (selectedCaseCategories.length === 0) {
            if (!confirm('您没有选择任何用例类型，是否继续？')) {
                if (loadingIndicator) loadingIndicator.style.display = 'none';
                if (generateButton) generateButton.disabled = false;
                return;
            }
        }
        
        // 如果选择了 AUTO，给出提示
        if (caseCountValue === 'auto') {
            console.log('已选择 AUTO 模式，AI 将根据需求复杂度自动决定生成用例数量');
        }
        
        // 显示加载指示器和清空结果容器
        if (loadingIndicator) {
            loadingIndicator.style.display = 'block';
        }
        if (resultContainer) {
            resultContainer.innerHTML = '';
        }
        if (generateButton) {
            generateButton.disabled = true;
        }
        
        // 构造请求数据
        // 尝试从Vue实例获取llmModelName
        let llmModelName = 'deepseek-chat';
        const vueApp2 = document.querySelector('#app')?._vnode?.component?.proxy;
        if (vueApp2 && vueApp2.llmModelName) {
            llmModelName = vueApp2.llmModelName;
        } else if (document.getElementById('llm-model-name')) {
            // 回退方案：尝试从DOM元素获取
            llmModelName = document.getElementById('llm-model-name').value || 'deepseek-chat';
        }
        
        const requestData = {
            requirements: inputTextValue,
            llm_model_name: llmModelName,
            case_design_methods: selectedDesignMethods,
            case_categories: selectedCaseCategories,
            case_count: caseCountValue
        };
        
        console.log('发送的数据:', requestData);
        
        // 发送请求
        fetch('/test_case_generator/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify(requestData)
        })
        .then(response => {
            console.log('收到服务器响应:', response.status);
            return response.json();
        })
        .then(data => {
            console.log('解析后的响应数据:', data);
            
            // 隐藏加载指示器
            if (loadingIndicator) {
                loadingIndicator.style.display = 'none';
            }
            if (generateButton) {
                generateButton.disabled = false;
            }
            
            if (data.success) {
                // 创建或获取 result-container
                let resultContainer = document.getElementById('result-container');
                if (!resultContainer) {
                    resultContainer = document.createElement('div');
                    resultContainer.id = 'result-container';
                    resultContainer.className = 'mt-4';
                    generateForm.parentNode.insertBefore(resultContainer, generateForm.nextSibling);
                }
                
                // 使用 displayTestCases 函数显示测试用例
                displayTestCases(data.test_cases);
                
                // 保存生成的测试用例到会话存储
                sessionStorage.setItem('generatedTestCases', JSON.stringify(data.test_cases));
                sessionStorage.setItem('inputText', inputTextValue);
                
                // 重新绑定保存按钮事件
                const saveButton = document.getElementById('save-button');
                if (saveButton) {
                    saveButton.disabled = false;
                }
            } else {
                console.error('服务器返回错误:', data.message);
                if (resultContainer) {
                    resultContainer.innerHTML = `<div class="alert alert-danger">${data.message || '生成测试用例时出错'}</div>`;
                }
            }
        })
        .catch(error => {
            console.error('请求发生错误:', error);
            if (loadingIndicator) {
                loadingIndicator.style.display = 'none';
            }
            if (resultContainer) {
                resultContainer.innerHTML = `<div class="alert alert-danger">请求失败：${error.message}</div>`;
            }
        });
    });
    
    // 显示测试用例函数
    function displayTestCases(testCases) {
        let resultContainer = document.getElementById('result-container');
        if (!resultContainer) {
            resultContainer = document.createElement('div');
            resultContainer.id = 'result-container';
            resultContainer.className = 'mt-4';
            const generateForm = document.getElementById('generate-form');
            if (generateForm) {
                generateForm.parentNode.insertBefore(resultContainer, generateForm.nextSibling);
            } else {
                document.body.appendChild(resultContainer);
            }
        }

        if (!testCases || !testCases.length) {
            resultContainer.innerHTML = '<div class="alert alert-info">没有生成测试用例</div>';
            return;
        }
        
        let html = `
            <div class="card">
                <div class="card-header">
                    <h5 class="mb-0">生成的测试用例</h5>
                </div>
                <div class="card-body">
                    <div class="table-responsive">
                        <table class="table table-bordered table-hover">
                            <thead class="thead-light">
                                <tr>
                                    <th width="5%">编号</th>
                                    <th width="25%">测试用例描述</th>
                                    <th width="35%">测试步骤</th>
                                    <th width="35%">预期结果</th>
                                </tr>
                            </thead>
                            <tbody>
        `;

        testCases.forEach((testCase, index) => {
            const testSteps = Array.isArray(testCase.test_steps) 
                ? testCase.test_steps 
                : testCase.test_steps.split('\n').filter(step => step.trim());
            
            const expectedResults = Array.isArray(testCase.expected_results)
                ? testCase.expected_results
                : testCase.expected_results.split('\n').filter(result => result.trim());

            html += `
                <tr>
                    <td>${index + 1}</td>
                    <td>${testCase.description || ''}</td>
                    <td>
                        ${testSteps.map(step => `<div class="mb-2">${step}</div>`).join('')}
                    </td>
                    <td>
                        ${expectedResults.map(result => `<div class="mb-2">${result}</div>`).join('')}
                    </td>
                </tr>
            `;
        });

        html += `
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            <div class="text-right mt-3">
                <button id="save-button" class="btn btn-success">
                    <i class="fas fa-save" style="margin-right: 8px;"></i>
                    保存测试用例
                </button>
            </div>
        `;

        resultContainer.innerHTML = html;

        // 绑定保存按钮事件
        const saveButton = document.getElementById('save-button');
        if (saveButton) {
            saveButton.addEventListener('click', function() {
                const savedTestCases = JSON.parse(sessionStorage.getItem('generatedTestCases') || '[]');
                const inputTextValue = sessionStorage.getItem('inputText') || '';
                
                // 尝试从Vue实例获取llmModelName
                let llmModelName = 'deepseek-chat';
                const vueApp3 = document.querySelector('#app')?._vnode?.component?.proxy;
                if (vueApp3 && vueApp3.llmModelName) {
                    llmModelName = vueApp3.llmModelName;
                } else if (document.getElementById('llm-model-name')) {
                    // 回退方案：尝试从DOM元素获取
                    llmModelName = document.getElementById('llm-model-name').value || 'deepseek-chat';
                }
                
                // 从 URL 获取 project_id
                const urlParams = new URLSearchParams(window.location.search);
                const projectId = urlParams.get('project_id');
                
                fetch('/test_case_generator/save-test-case/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: JSON.stringify({
                        test_cases: savedTestCases,
                        requirement: inputTextValue,
                        llm_model_name: llmModelName,
                        project_id: projectId
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showNotification('测试用例保存成功', 'success');
                    } else {
                        showNotification('保存失败：' + data.message, 'error');
                    }
                })
                .catch(error => {
                    showNotification('保存失败：' + error.message, 'error');
                });
            });
        }
    }
    
    console.log('测试用例生成页面初始化完成');
});
