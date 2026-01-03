# Template Filler

## 中文描述

**Template Filler** 是一个智能文档模板填充工具，利用大语言模型（LLM）自动生成内容并填充到 Word 模板的占位符中。

### 核心功能

- **模板解析**：上传 DOCX 模板，自动检测 `{{PLACEHOLDER}}` 格式的占位符
- **智能生成**：基于原始材料，使用 LLM（如通义千问）生成适配各占位符的内容
- **多选项支持**：可为每个占位符生成多个候选内容供选择
- **手动模式**：支持直接输入固定内容，跳过 LLM 生成
- **选择性重新生成**：单独刷新某个占位符的内容，保留其他结果
- **配置管理**：保存和加载占位符配置，方便复用
- **格式保留**：填充后的文档保留原始模板的样式和格式

### 技术栈

- **后端**：Python + FastAPI
- **前端**：原生 HTML/CSS/JavaScript
- **LLM**：支持 OpenAI 兼容 API（通义千问、DeepSeek 等）
- **文档处理**：python-docx

---

## English Description

**Template Filler** is an intelligent document template filling tool that uses Large Language Models (LLM) to automatically generate content and fill placeholders in Word templates.

### Core Features

- **Template Parsing**: Upload DOCX templates, auto-detect `{{PLACEHOLDER}}` style placeholders
- **Smart Generation**: Generate placeholder-specific content using LLM based on source materials
- **Multiple Options**: Generate multiple candidates for each placeholder for selection
- **Manual Mode**: Directly input fixed content, bypassing LLM generation
- **Selective Regeneration**: Refresh individual placeholders while keeping others intact
- **Config Management**: Save and load placeholder configurations for reuse
- **Format Preservation**: Filled documents retain original template styles and formatting

### Tech Stack

- **Backend**: Python + FastAPI
- **Frontend**: Vanilla HTML/CSS/JavaScript
- **LLM**: Supports OpenAI-compatible APIs (Qwen, DeepSeek, etc.)
- **Document Processing**: python-docx

---

## Quick Start

```bash
# Install dependencies
pip install fastapi uvicorn python-docx openai pyyaml python-dotenv

# Configure API
cp .env.example .env
# Edit .env with your API key

# Run server
python template_filler/server.py

# Open http://localhost:8000
```
