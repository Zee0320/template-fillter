"""
Web Server: FastAPI 后端

提供 Web UI 所需的 API 接口。
"""

import os
import uuid
import shutil
import tempfile
from typing import Optional, Dict, Any, List
from pathlib import Path

# 加载 .env 配置
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yaml

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from template_filler.orchestrator import Orchestrator
from template_filler.llm_client import LLMClient
from template_filler.docx_to_html import DocxToHtml
from template_filler.placeholder_detector import PlaceholderDetector
from template_filler.config_store import config_store


# 创建临时目录存储上传的文件
UPLOAD_DIR = Path(tempfile.gettempdir()) / "template_filler_uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

OUTPUT_DIR = Path(tempfile.gettempdir()) / "template_filler_outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

app = FastAPI(
    title="Template Filler",
    description="使用 LLM 自动填充文档模板",
    version="1.0.0"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 存储会话数据
sessions: Dict[str, Dict[str, Any]] = {}


class SchemaInput(BaseModel):
    """Schema 输入模型"""
    placeholders: Dict[str, Dict[str, Any]]
    system_prompt: Optional[str] = None


class PreviewRequest(BaseModel):
    """预览请求"""
    session_id: str


class GenerateRequest(BaseModel):
    """生成请求"""
    session_id: str
    selections: Dict[str, int] = {}


@app.post("/api/upload-template")
async def upload_template(file: UploadFile = File(...)):
    """上传模板文件"""
    if not file.filename.endswith('.docx'):
        raise HTTPException(400, "只支持 .docx 文件")
    
    session_id = str(uuid.uuid4())
    file_path = UPLOAD_DIR / f"{session_id}_template.docx"
    
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    sessions[session_id] = {
        "template_path": str(file_path),
        "template_name": file.filename
    }
    
    return {"session_id": session_id, "filename": file.filename}


@app.post("/api/set-context/{session_id}")
async def set_context(session_id: str, context: str = Form(...)):
    """设置原始材料"""
    if session_id not in sessions:
        raise HTTPException(404, "Session not found")
    
    sessions[session_id]["context"] = context
    return {"success": True}


@app.post("/api/set-schema/{session_id}")
async def set_schema(session_id: str, schema: SchemaInput):
    """设置 Schema 配置"""
    if session_id not in sessions:
        raise HTTPException(404, "Session not found")
    
    sessions[session_id]["schema"] = schema.dict()
    return {"success": True}


@app.post("/api/preview")
async def preview(request: PreviewRequest):
    """预览生成结果"""
    session_id = request.session_id
    if session_id not in sessions:
        raise HTTPException(404, "Session not found")
    
    session = sessions[session_id]
    
    if "template_path" not in session:
        raise HTTPException(400, "请先上传模板")
    if "context" not in session:
        raise HTTPException(400, "请先设置原始材料")
    if "schema" not in session:
        raise HTTPException(400, "请先配置 Schema")
    
    try:
        llm_client = LLMClient()
        orchestrator = Orchestrator(
            template_path=session["template_path"],
            context=session["context"],
            schema=session["schema"],
            llm_client=llm_client
        )
        
        result = orchestrator.preview()
        sessions[session_id]["preview"] = result
        
        return result
    except Exception as e:
        raise HTTPException(500, f"预览生成失败: {str(e)}")


class RegenerateRequest(BaseModel):
    """单独重新生成请求"""
    session_id: str
    placeholder: str


@app.post("/api/regenerate")
async def regenerate_placeholder(request: RegenerateRequest):
    """单独重新生成某个占位符的内容"""
    session_id = request.session_id
    placeholder = request.placeholder
    
    if session_id not in sessions:
        raise HTTPException(404, "Session not found")
    
    session = sessions[session_id]
    
    if "context" not in session:
        raise HTTPException(400, "请先设置原始材料")
    if "schema" not in session:
        raise HTTPException(400, "请先配置 Schema")
    
    schema = session["schema"]
    if placeholder not in schema.get("placeholders", {}):
        raise HTTPException(400, f"占位符 {placeholder} 不存在")
    
    try:
        llm_client = LLMClient()
        
        # 获取该占位符的配置
        placeholder_config = schema["placeholders"][placeholder]
        
        # 确保 placeholder_config 是字典
        if isinstance(placeholder_config, str):
            placeholder_config = {"prompt": placeholder_config, "mode": "llm"}
        
        mode = placeholder_config.get("mode", "llm")
        prompt = placeholder_config.get("prompt", f"根据内容生成 {placeholder}")
        options_count = placeholder_config.get("options_count", 1)
        
        if mode == "manual":
            # 手动模式直接返回配置的值
            content = [placeholder_config.get("manualValue", "")]
        else:
            # LLM 生成
            from template_filler.prompt_engine import PromptEngine
            
            # 构建单独的 schema
            single_schema = {
                "placeholders": {placeholder: placeholder_config}
            }
            
            engine = PromptEngine(single_schema, session["context"])
            full_prompt = engine.build_prompt(placeholder)
            
            # llm 模式根据 options_count 生成
            if options_count > 1:
                content = llm_client.generate_multiple(full_prompt, n=options_count)
            else:
                content = [llm_client.generate(full_prompt)]
        
        # 更新 preview 结果
        if "preview" in session and "placeholders" in session["preview"]:
            session["preview"]["placeholders"][placeholder] = {
                "mode": mode,
                "content": content,
                "selected": 0
            }
        
        return {
            "placeholder": placeholder,
            "mode": mode,
            "content": content,
            "selected": 0
        }
    except Exception as e:
        raise HTTPException(500, f"重新生成失败: {str(e)}")


@app.post("/api/generate")
async def generate(request: GenerateRequest):
    """生成最终文档"""
    session_id = request.session_id
    if session_id not in sessions:
        raise HTTPException(404, "Session not found")
    
    session = sessions[session_id]
    
    if "template_path" not in session:
        raise HTTPException(400, "请先上传模板")
    if "context" not in session:
        raise HTTPException(400, "请先设置原始材料")
    if "schema" not in session:
        raise HTTPException(400, "请先配置 Schema")
    
    try:
        output_filename = f"{session_id}_output.docx"
        output_path = OUTPUT_DIR / output_filename
        
        llm_client = LLMClient()
        orchestrator = Orchestrator(
            template_path=session["template_path"],
            context=session["context"],
            schema=session["schema"],
            llm_client=llm_client
        )
        
        result = orchestrator.run(str(output_path), request.selections)
        sessions[session_id]["output_path"] = str(output_path)
        
        return {
            "success": True,
            "download_url": f"/api/download/{session_id}",
            "filled_placeholders": result["filled_placeholders"]
        }
    except Exception as e:
        raise HTTPException(500, f"文档生成失败: {str(e)}")


@app.get("/api/download/{session_id}")
async def download(session_id: str):
    """下载生成的文档"""
    if session_id not in sessions:
        raise HTTPException(404, "Session not found")
    
    session = sessions[session_id]
    if "output_path" not in session:
        raise HTTPException(400, "请先生成文档")
    
    output_path = session["output_path"]
    if not os.path.exists(output_path):
        raise HTTPException(404, "文件不存在")
    
    original_name = session.get("template_name", "output.docx")
    download_name = f"filled_{original_name}"
    
    return FileResponse(
        output_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=download_name
    )


@app.delete("/api/session/{session_id}")
async def delete_session(session_id: str):
    """删除会话及相关文件"""
    if session_id in sessions:
        session = sessions[session_id]
        # 清理文件
        for key in ["template_path", "output_path"]:
            if key in session and os.path.exists(session[key]):
                os.remove(session[key])
        del sessions[session_id]
    return {"success": True}


@app.get("/api/parse-template/{session_id}")
async def parse_template(session_id: str):
    """解析模板返回 HTML 和占位符列表"""
    if session_id not in sessions:
        raise HTTPException(404, "Session not found")
    
    session = sessions[session_id]
    if "template_path" not in session:
        raise HTTPException(400, "请先上传模板")
    
    try:
        converter = DocxToHtml(session["template_path"])
        result = converter.convert_with_highlight()
        
        # 使用 PlaceholderDetector 生成建议的 Schema
        detector = PlaceholderDetector()
        suggested_schema = detector._generate_schema(result['placeholders'])
        
        sessions[session_id]["template_html"] = result['raw_html']
        sessions[session_id]["detected_placeholders"] = result['placeholders']
        
        return {
            "html": result['html'],
            "placeholders": result['placeholders'],
            "suggested_schema": suggested_schema,
            "messages": result['messages']
        }
    except Exception as e:
        raise HTTPException(500, f"模板解析失败: {str(e)}")


class PreviewFilledRequest(BaseModel):
    """填充预览请求"""
    session_id: str
    content_map: Dict[str, str]


@app.post("/api/preview-filled")
async def preview_filled(request: PreviewFilledRequest):
    """预览填充后的 HTML"""
    session_id = request.session_id
    if session_id not in sessions:
        raise HTTPException(404, "Session not found")
    
    session = sessions[session_id]
    if "template_html" not in session:
        raise HTTPException(400, "请先解析模板")
    
    try:
        converter = DocxToHtml(session["template_path"])
        converter.convert()
        filled_html = converter.fill_html(request.content_map)
        
        return {"html": filled_html}
    except Exception as e:
        raise HTTPException(500, f"预览生成失败: {str(e)}")


# ========== Config APIs ==========

class SaveConfigRequest(BaseModel):
    """保存配置请求"""
    session_id: str
    name: str
    description: str = ""


@app.post("/api/configs")
async def save_config(request: SaveConfigRequest):
    """保存当前配置"""
    session_id = request.session_id
    if session_id not in sessions:
        raise HTTPException(404, "Session not found")
    
    session = sessions[session_id]
    if "schema" not in session:
        raise HTTPException(400, "没有可保存的配置")
    
    template_name = session.get("template_name", "unknown")
    
    # 获取 schema，处理可能是 Pydantic 模型的情况
    schema = session["schema"]
    if hasattr(schema, 'dict'):
        schema = schema.dict()
    elif hasattr(schema, 'model_dump'):
        schema = schema.model_dump()
    
    placeholders = schema.get("placeholders", {}) if isinstance(schema, dict) else {}
    
    try:
        config_id = config_store.save(
            name=request.name,
            template_name=template_name,
            placeholders=placeholders,
            description=request.description
        )
        
        return {"id": config_id, "name": request.name}
    except Exception as e:
        raise HTTPException(500, f"保存失败: {str(e)}")


@app.get("/api/configs")
async def list_configs(template_name: Optional[str] = None):
    """列出所有配置"""
    configs = config_store.list_configs(template_name)
    return {"configs": configs}


@app.get("/api/configs/{config_id}")
async def get_config(config_id: str):
    """获取配置"""
    config = config_store.load(config_id)
    if not config:
        raise HTTPException(404, "Config not found")
    return config


@app.delete("/api/configs/{config_id}")
async def delete_config(config_id: str):
    """删除配置"""
    success = config_store.delete(config_id)
    if not success:
        raise HTTPException(404, "Config not found")
    return {"success": True}


class LoadConfigRequest(BaseModel):
    """加载配置请求"""
    session_id: str
    config_id: str


@app.post("/api/load-config")
async def load_config_to_session(request: LoadConfigRequest):
    """加载配置到当前会话"""
    session_id = request.session_id
    if session_id not in sessions:
        raise HTTPException(404, "Session not found")
    
    config = config_store.load(request.config_id)
    if not config:
        raise HTTPException(404, "Config not found")
    
    # 应用配置到会话
    sessions[session_id]["schema"] = {
        "placeholders": config["placeholders"]
    }
    
    return {
        "success": True,
        "config_name": config["name"],
        "placeholders": config["placeholders"]
    }


# 静态文件服务（Web UI）
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/", response_class=HTMLResponse)
async def index():
    """返回 Web UI 主页"""
    html_path = static_dir / "index.html"
    if html_path.exists():
        return html_path.read_text(encoding="utf-8")
    return """
    <html>
        <head><title>Template Filler</title></head>
        <body>
            <h1>Template Filler</h1>
            <p>Static files not found. Please create static/index.html</p>
        </body>
    </html>
    """


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
