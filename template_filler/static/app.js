// Template Filler - Phase 1: docx-preview.js Integration

// State
let sessionId = null;
let templateFile = null;
let placeholders = [];
let suggestedSchema = null;
let generatedContent = {};
let selections = {};

// DOM Elements
const fileInput = document.getElementById('template-file');
const templatePreview = document.getElementById('template-preview');
const placeholderConfig = document.getElementById('placeholder-config');
const contextInput = document.getElementById('context-input');
const contentPreview = document.getElementById('content-preview');
const generateBtn = document.getElementById('generate-btn');
const previewBtn = document.getElementById('preview-btn');
const downloadBtn = document.getElementById('download-btn');
const saveConfigBtn = document.getElementById('save-config-btn');
const loadingOverlay = document.getElementById('loading-overlay');
const loadingText = document.getElementById('loading-text');
const toastContainer = document.getElementById('toast-container');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    fileInput.addEventListener('change', handleTemplateUpload);
    contextInput.addEventListener('input', checkGenerateReady);
});

// ========== Phase 1: DOCX Preview ==========

async function handleTemplateUpload(e) {
    if (!e.target.files.length) return;

    const file = e.target.files[0];
    if (!file.name.endsWith('.docx')) {
        showToast('只支持 .docx 格式', 'error');
        return;
    }

    templateFile = file;
    showLoading('加载预览...');

    try {
        // 1. 使用 docx-preview.js 渲染预览（带错误处理）
        templatePreview.innerHTML = '';

        if (typeof docx !== 'undefined' && docx.renderAsync) {
            try {
                await docx.renderAsync(file, templatePreview, null, {
                    className: 'docx-wrapper',
                    inWrapper: true,
                    ignoreWidth: false,
                    ignoreHeight: true,
                    ignoreFonts: false,
                    breakPages: false,
                    renderHeaders: true,
                    renderFooters: true,
                    renderFootnotes: true,
                    renderEndnotes: true
                });
            } catch (docxErr) {
                console.warn('docx-preview.js 渲染失败，使用备用方案:', docxErr);
                templatePreview.innerHTML = '<div class="empty-state" style="color: #666;">DOCX 预览不可用（将在服务器端渲染）</div>';
            }
        } else {
            console.warn('docx-preview.js 未加载');
            templatePreview.innerHTML = '<div class="empty-state" style="color: #666;">正在加载...</div>';
        }

        // 2. 上传到服务器获取占位符
        const formData = new FormData();
        formData.append('file', file);

        const uploadRes = await fetch('/api/upload-template', {
            method: 'POST',
            body: formData
        });

        if (!uploadRes.ok) {
            const errData = await uploadRes.json().catch(() => ({}));
            throw new Error(errData.detail || '上传失败');
        }

        const uploadData = await uploadRes.json();
        sessionId = uploadData.session_id;

        // 3. 解析占位符
        const parseRes = await fetch(`/api/parse-template/${sessionId}`);
        if (!parseRes.ok) {
            const errData = await parseRes.json().catch(() => ({}));
            throw new Error(errData.detail || '解析失败');
        }

        const parseData = await parseRes.json();
        placeholders = parseData.placeholders || [];
        suggestedSchema = parseData.suggested_schema || { placeholders: {} };

        // 4. 如果 docx-preview 失败，使用服务器端 HTML
        if (parseData.html && templatePreview.querySelector('.empty-state')) {
            templatePreview.innerHTML = parseData.html;
        }

        // 5. 渲染占位符配置
        renderPlaceholderConfig();

        // 6. 高亮预览中的占位符
        highlightPlaceholdersInPreview();

        saveConfigBtn.disabled = false;
        checkGenerateReady();
        showToast('模板加载成功', 'success');
    } catch (error) {
        console.error('上传错误:', error);
        showToast(error.message || '上传失败', 'error');
    } finally {
        hideLoading();
    }
}

// 高亮预览中的占位符
function highlightPlaceholdersInPreview() {
    const walker = document.createTreeWalker(
        templatePreview,
        NodeFilter.SHOW_TEXT,
        null,
        false
    );

    const textNodes = [];
    while (walker.nextNode()) {
        textNodes.push(walker.currentNode);
    }

    textNodes.forEach(node => {
        const text = node.textContent;
        if (text.includes('{{')) {
            const span = document.createElement('span');
            span.innerHTML = text.replace(
                /\{\{(\w+)\}\}/g,
                '<mark style="background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 1px 4px; border-radius: 3px; font-weight: 500;">{{$1}}</mark>'
            );
            node.parentNode.replaceChild(span, node);
        }
    });
}

// 渲染占位符配置
function renderPlaceholderConfig() {
    if (!placeholders.length) {
        placeholderConfig.innerHTML = '<div class="empty-state">未检测到占位符</div>';
        return;
    }

    let html = '';
    for (const name of placeholders) {
        const config = suggestedSchema?.placeholders?.[name] || {};
        const mode = config.mode === 'manual' ? 'manual' : 'llm';
        const prompt = config.prompt || '';
        const optionsCount = config.options_count || 1;
        const manualValue = config.manualValue || '';

        html += `
            <div class="placeholder-card" data-name="${name}">
                <div class="placeholder-header">
                    <span class="placeholder-name">{{${name}}}</span>
                    <select class="mode-select" onchange="updateMode('${name}', this.value)" title="选择填充方式">
                        <option value="llm" ${mode === 'llm' ? 'selected' : ''}>🤖 LLM生成</option>
                        <option value="manual" ${mode === 'manual' ? 'selected' : ''}>✏️ 手动输入</option>
                    </select>
                </div>
                <div class="placeholder-body" id="body-${name}">
                    ${mode === 'manual'
                ? `<input type="text" placeholder="输入固定内容..." value="${manualValue}" onchange="updateManualValue('${name}', this.value)">`
                : `<div class="prompt-row">
                       <span class="prompt-label">Prompt (指导 LLM 如何生成):</span>
                       <span class="options-label">生成 <input type="number" min="1" max="5" value="${optionsCount}" onchange="updateOptionsCount('${name}', this.value)" class="options-input"> 个选项</span>
                   </div>
                   <textarea placeholder="例如：根据材料提取一个简洁有力的标题..." onchange="updatePrompt('${name}', this.value)">${prompt}</textarea>`
            }
                </div>
            </div>
        `;
    }

    placeholderConfig.innerHTML = html;
}

// 更新模式
function updateMode(name, mode) {
    if (!suggestedSchema.placeholders[name]) {
        suggestedSchema.placeholders[name] = {};
    }
    suggestedSchema.placeholders[name].mode = mode;

    const body = document.getElementById(`body-${name}`);
    const config = suggestedSchema.placeholders[name];
    const optionsCount = config.options_count || 1;

    if (mode === 'manual') {
        body.innerHTML = `<input type="text" placeholder="输入固定内容..." onchange="updateManualValue('${name}', this.value)">`;
    } else {
        const prompt = config.prompt || '';
        body.innerHTML = `
            <div class="prompt-row">
                <span class="prompt-label">Prompt (指导 LLM 如何生成):</span>
                <span class="options-label">生成 <input type="number" min="1" max="5" value="${optionsCount}" onchange="updateOptionsCount('${name}', this.value)" class="options-input"> 个选项</span>
            </div>
            <textarea placeholder="例如：根据材料提取一个简洁有力的标题..." onchange="updatePrompt('${name}', this.value)">${prompt}</textarea>
        `;
    }

    checkGenerateReady();
}

// 更新选项数量
function updateOptionsCount(name, count) {
    if (!suggestedSchema.placeholders[name]) {
        suggestedSchema.placeholders[name] = {};
    }
    suggestedSchema.placeholders[name].options_count = parseInt(count) || 1;
}

// 更新 Prompt
function updatePrompt(name, prompt) {
    if (!suggestedSchema.placeholders[name]) {
        suggestedSchema.placeholders[name] = {};
    }
    suggestedSchema.placeholders[name].prompt = prompt;
}

// 更新手动值
function updateManualValue(name, value) {
    if (!suggestedSchema.placeholders[name]) {
        suggestedSchema.placeholders[name] = {};
    }
    suggestedSchema.placeholders[name].manualValue = value;
}

// ========== Generation ==========

function checkGenerateReady() {
    const hasContext = contextInput.value.trim().length > 0;
    const hasPlaceholders = placeholders.length > 0;
    generateBtn.disabled = !(sessionId && hasPlaceholders && hasContext);
}

async function generateContent() {
    if (!sessionId) return;

    showLoading('生成内容...');

    try {
        // 设置 context
        const formData = new FormData();
        formData.append('context', contextInput.value.trim());
        await fetch(`/api/set-context/${sessionId}`, { method: 'POST', body: formData });

        // 设置 schema
        await fetch(`/api/set-schema/${sessionId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(suggestedSchema)
        });

        // 生成预览
        const res = await fetch('/api/preview', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId })
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || '生成失败');
        }

        const data = await res.json();
        generatedContent = data.placeholders;

        renderContentPreview(data);

        previewBtn.disabled = false;
        downloadBtn.disabled = false;
        showToast('生成成功', 'success');
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        hideLoading();
    }
}

function renderContentPreview(data) {
    let html = '';
    selections = {};

    for (const [name, info] of Object.entries(data.placeholders)) {
        selections[name] = info.selected || 0;

        // 根据内容数量判断是否显示多选
        if (info.content.length > 1) {
            let options = info.content.map((text, i) => `
                <label class="result-option ${i === 0 ? 'selected' : ''}" onclick="selectOption('${name}', ${i})">
                    <input type="radio" name="opt-${name}" ${i === 0 ? 'checked' : ''}>
                    <span class="result-option-text">${escapeHtml(text)}</span>
                </label>
            `).join('');

            html += `
                <div class="result-card" data-name="${name}">
                    <div class="result-header">
                        <span class="result-name">{{${name}}}</span>
                        <button class="btn-icon btn-regenerate" onclick="regenerate('${name}')" title="重新生成">🔄</button>
                    </div>
                    <div class="result-options">${options}</div>
                </div>
            `;
        } else {
            html += `
                <div class="result-card" data-name="${name}">
                    <div class="result-header">
                        <span class="result-name">{{${name}}}</span>
                        <button class="btn-icon btn-regenerate" onclick="regenerate('${name}')" title="重新生成">🔄</button>
                    </div>
                    <div class="result-content">${escapeHtml(info.content[0])}</div>
                </div>
            `;
        }
    }

    contentPreview.innerHTML = html || '<div class="empty-state">无内容</div>';
}

function selectOption(name, index) {
    selections[name] = index;
    document.querySelectorAll(`input[name="opt-${name}"]`).forEach((opt, i) => {
        opt.closest('.result-option').classList.toggle('selected', i === index);
        opt.checked = (i === index);
    });
}

// Phase 3: 单独重新生成
async function regenerate(name) {
    showLoading(`重新生成 ${name}...`);

    try {
        // 获取当前占位符配置
        const config = suggestedSchema?.placeholders?.[name] || {};

        // 如果是手动模式，从输入框读取最新值
        let manualValue = config.manualValue || '';
        const inputField = document.querySelector(`.placeholder-card[data-name="${name}"] input[type="text"]`);
        if (inputField) {
            manualValue = inputField.value;
            // 同步更新 schema
            if (suggestedSchema?.placeholders?.[name]) {
                suggestedSchema.placeholders[name].manualValue = manualValue;
            }
        }

        // 先更新 schema 到服务器
        await fetch(`/api/set-schema/${sessionId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(suggestedSchema)
        });

        const res = await fetch('/api/regenerate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId, placeholder: name })
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || '重新生成失败');
        }

        const data = await res.json();

        // 更新 generatedContent
        generatedContent[name] = {
            mode: data.mode,
            content: data.content,
            selected: 0
        };
        selections[name] = 0;

        // 更新 UI 中该占位符的卡片
        const card = document.querySelector(`.result-card[data-name="${name}"]`);
        if (card) {
            if (data.content.length > 1) {
                let options = data.content.map((text, i) => `
                    <label class="result-option ${i === 0 ? 'selected' : ''}" onclick="selectOption('${name}', ${i})">
                        <input type="radio" name="opt-${name}" ${i === 0 ? 'checked' : ''}>
                        <span class="result-option-text">${escapeHtml(text)}</span>
                    </label>
                `).join('');

                card.innerHTML = `
                    <div class="result-header">
                        <span class="result-name">{{${name}}}</span>
                        <button class="btn-icon btn-regenerate" onclick="regenerate('${name}')" title="重新生成">🔄</button>
                    </div>
                    <div class="result-options">${options}</div>
                `;
            } else {
                card.innerHTML = `
                    <div class="result-header">
                        <span class="result-name">{{${name}}}</span>
                        <button class="btn-icon btn-regenerate" onclick="regenerate('${name}')" title="重新生成">🔄</button>
                    </div>
                    <div class="result-content">${escapeHtml(data.content[0])}</div>
                `;
            }
        }

        showToast(`${name} 已重新生成`, 'success');
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        hideLoading();
    }
}

// ========== Preview & Download ==========

function getContentMap() {
    const map = {};
    for (const [name, info] of Object.entries(generatedContent)) {
        map[name] = info.content[selections[name] || 0];
    }
    return map;
}

async function showFilledPreview() {
    showLoading('生成预览...');
    try {
        const res = await fetch('/api/preview-filled', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId, content_map: getContentMap() })
        });
        if (!res.ok) throw new Error('预览失败');
        const data = await res.json();
        document.getElementById('filled-preview').innerHTML = data.html;
        document.getElementById('preview-modal').style.display = 'flex';
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        hideLoading();
    }
}

async function downloadDocument() {
    showLoading('生成文档...');
    try {
        await fetch('/api/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId, selections })
        });
        window.location.href = `/api/download/${sessionId}`;
        showToast('下载开始', 'success');
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        hideLoading();
    }
}

// ========== Config (Phase 4) ==========

async function saveConfig() {
    const name = prompt('请输入配置名称:');
    if (!name) return;

    showLoading('保存配置...');

    try {
        const res = await fetch('/api/configs', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: sessionId,
                name: name,
                description: ''
            })
        });

        if (!res.ok) throw new Error('保存失败');

        showToast(`配置 "${name}" 已保存`, 'success');
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        hideLoading();
    }
}

async function showConfigList() {
    showLoading('加载配置列表...');

    try {
        const res = await fetch('/api/configs');
        if (!res.ok) throw new Error('加载失败');

        const data = await res.json();
        const configs = data.configs;

        const configList = document.getElementById('config-list');

        if (configs.length === 0) {
            configList.innerHTML = '<div class="empty-state">暂无保存的配置</div>';
        } else {
            configList.innerHTML = configs.map(c => `
                <div class="config-item" onclick="loadConfig('${c.id}')">
                    <span class="config-item-name">${c.name}</span>
                    <span class="config-item-date">${c.template_name}</span>
                    <button class="btn-icon" onclick="event.stopPropagation(); deleteConfig('${c.id}')" title="删除">🗑️</button>
                </div>
            `).join('');
        }

        document.getElementById('config-modal').style.display = 'flex';
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        hideLoading();
    }
}

async function loadConfig(configId) {
    if (!sessionId) {
        showToast('请先上传模板', 'error');
        return;
    }

    showLoading('加载配置...');

    try {
        const res = await fetch('/api/load-config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: sessionId,
                config_id: configId
            })
        });

        if (!res.ok) throw new Error('加载失败');

        const data = await res.json();

        // 更新本地 schema
        suggestedSchema = { placeholders: data.placeholders };

        // 重新渲染配置面板
        renderPlaceholderConfig();

        closeModal('config-modal');
        showToast(`配置 "${data.config_name}" 已加载`, 'success');
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        hideLoading();
    }
}

async function deleteConfig(configId) {
    if (!confirm('确定删除此配置?')) return;

    try {
        const res = await fetch(`/api/configs/${configId}`, { method: 'DELETE' });
        if (!res.ok) throw new Error('删除失败');

        // 刷新列表
        showConfigList();
        showToast('配置已删除', 'success');
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// ========== Utils ==========

function closeModal(id) {
    document.getElementById(id).style.display = 'none';
}

function showLoading(text = '处理中...') {
    loadingText.textContent = text;
    loadingOverlay.style.display = 'flex';
}

function hideLoading() {
    loadingOverlay.style.display = 'none';
}

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    toastContainer.appendChild(toast);
    setTimeout(() => toast.remove(), 2500);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
