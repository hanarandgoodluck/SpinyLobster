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
    
    // 显示通知消息的辅助函数（使用 Element Plus）
    window.showNotification = function(message, type = 'info') {
        if (typeof ElementPlus !== 'undefined' && ElementPlus.ElMessage) {
            const messageType = type === 'error' ? 'error' : (type === 'success' ? 'success' : 'info');
            ElementPlus.ElMessage({
                message: message,
                type: messageType,
                duration: 3000,
                showClose: true
            });
        } else {
            // 回退到原生 alert
            alert(message);
        }
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
        const inputText = document.getElementById('input-text');
        
        // 获取输入文本
        const inputTextValue = inputText?.value?.trim();
        
        // 从复选框获取选中的测试用例设计方法
        const designMethodsCheckboxes = document.querySelectorAll('.case-design-method:checked');
        const selectedDesignMethods = Array.from(designMethodsCheckboxes).map(cb => cb.value);
        
        // 从复选框获取选中的用例类型
        const caseCategoriesCheckboxes = document.querySelectorAll('.case-category:checked');
        const selectedCaseCategories = Array.from(caseCategoriesCheckboxes).map(cb => cb.value);
        
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
        const requestData = {
            requirements: inputTextValue,
            llm_model_name: document.getElementById('llm-model-name')?.value || 'deepseek-chat',
            case_design_methods: selectedDesignMethods,
            case_categories: selectedCaseCategories,
            case_count: document.getElementById('case_count')?.value || '10'
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
                <button id="save-button" class="btn btn-success">保存测试用例</button>
            </div>
        `;

        resultContainer.innerHTML = html;

        // 绑定保存按钮事件
        const saveButton = document.getElementById('save-button');
        if (saveButton) {
            saveButton.addEventListener('click', function() {
                const savedTestCases = JSON.parse(sessionStorage.getItem('generatedTestCases') || '[]');
                const inputTextValue = sessionStorage.getItem('inputText') || '';
                const llmModelName = document.getElementById('llm-model-name')?.value || 'deepseek-chat';
                
                // 从 URL 获取 project_id
                const urlParams = new URLSearchParams(window.location.search);
                const projectId = urlParams.get('project_id');
                
                if (!savedTestCases || savedTestCases.length === 0) {
                    showNotification('没有可保存的测试用例', 'warning');
                    return;
                }
                
                // 禁用保存按钮，防止重复点击
                saveButton.disabled = true;
                saveButton.textContent = '保存中...';
                
                console.log('开始保存测试用例...', {
                    count: savedTestCases.length,
                    projectId: projectId
                });
                
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
                .then(response => {
                    console.log('服务器响应状态:', response.status);
                    return response.json();
                })
                .then(data => {
                    console.log('保存结果:', data);
                    
                    if (data.success) {
                        showNotification(`测试用例保存成功！共保存 ${data.count} 条用例`, 'success');
                        
                        // 清除已保存的数据
                        sessionStorage.removeItem('generatedTestCases');
                        
                        // 延迟后询问用户是否跳转到评审页面
                        setTimeout(() => {
                            const shouldRedirect = confirm(
                                `✅ 已成功保存 ${data.count} 条测试用例！\n\n` +
                                `是否立即跳转到"测试用例评审"页面查看？`
                            );
                            
                            if (shouldRedirect) {
                                // 构建评审页面URL
                                let reviewUrl = '/test_case_reviewer/';
                                if (projectId) {
                                    reviewUrl += '?project_id=' + projectId;
                                }
                                console.log('跳转到评审页面:', reviewUrl);
                                window.location.href = reviewUrl;
                            } else {
                                // 重置按钮状态
                                saveButton.disabled = false;
                                saveButton.textContent = '保存测试用例';
                                
                                // 提示用户可以手动刷新评审页面
                                showNotification('您可以随时在"测试用例评审"菜单中查看已保存的用例', 'info');
                            }
                        }, 800);
                    } else {
                        showNotification('保存失败：' + data.message, 'error');
                        saveButton.disabled = false;
                        saveButton.textContent = '保存测试用例';
                    }
                })
                .catch(error => {
                    console.error('保存请求失败:', error);
                    showNotification('保存失败：' + error.message, 'error');
                    saveButton.disabled = false;
                    saveButton.textContent = '保存测试用例';
                });
            });
        }
    }
    
    console.log('测试用例生成页面初始化完成');
});
