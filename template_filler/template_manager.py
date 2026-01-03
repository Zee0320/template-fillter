"""
TemplateManager: 模板库管理系统

管理模板文件和对应的 Schema 配置。
"""

import os
import json
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import yaml


class TemplateManager:
    """模板库管理器"""
    
    def __init__(self, storage_dir: Optional[str] = None):
        """
        初始化模板管理器
        
        Args:
            storage_dir: 存储目录，默认为 ~/.template_filler/templates
        """
        if storage_dir:
            self.storage_dir = Path(storage_dir)
        else:
            self.storage_dir = Path.home() / ".template_filler" / "templates"
        
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.storage_dir / "index.json"
        self._load_index()
    
    def _load_index(self):
        """加载模板索引"""
        if self.index_file.exists():
            with open(self.index_file, 'r', encoding='utf-8') as f:
                self.index = json.load(f)
        else:
            self.index = {"templates": {}}
    
    def _save_index(self):
        """保存模板索引"""
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(self.index, f, ensure_ascii=False, indent=2)
    
    def add_template(
        self,
        template_path: str,
        name: str,
        schema: Dict[str, Any],
        description: str = "",
        tags: List[str] = None
    ) -> str:
        """
        添加模板到库
        
        Args:
            template_path: 模板文件路径
            name: 模板名称
            schema: Schema 配置
            description: 模板描述
            tags: 标签列表
            
        Returns:
            模板 ID
        """
        template_id = name.lower().replace(' ', '_')
        template_dir = self.storage_dir / template_id
        template_dir.mkdir(exist_ok=True)
        
        # 复制模板文件
        src_path = Path(template_path)
        ext = src_path.suffix
        dest_path = template_dir / f"template{ext}"
        shutil.copy2(template_path, dest_path)
        
        # 保存 Schema
        schema_path = template_dir / "schema.yaml"
        with open(schema_path, 'w', encoding='utf-8') as f:
            yaml.dump(schema, f, allow_unicode=True, default_flow_style=False)
        
        # 更新索引
        self.index["templates"][template_id] = {
            "name": name,
            "description": description,
            "tags": tags or [],
            "file": str(dest_path.relative_to(self.storage_dir)),
            "schema": str(schema_path.relative_to(self.storage_dir)),
            "format": ext[1:],  # docx, xlsx
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        self._save_index()
        
        return template_id
    
    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """
        获取模板信息
        
        Args:
            template_id: 模板 ID
            
        Returns:
            模板信息字典，包含路径和 Schema
        """
        if template_id not in self.index["templates"]:
            return None
        
        info = self.index["templates"][template_id]
        template_path = self.storage_dir / info["file"]
        schema_path = self.storage_dir / info["schema"]
        
        # 加载 Schema
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema = yaml.safe_load(f)
        
        return {
            "id": template_id,
            "name": info["name"],
            "description": info["description"],
            "tags": info["tags"],
            "format": info["format"],
            "template_path": str(template_path),
            "schema": schema,
            "created_at": info["created_at"],
            "updated_at": info["updated_at"]
        }
    
    def list_templates(self, tag: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        列出所有模板
        
        Args:
            tag: 可选的标签过滤
            
        Returns:
            模板列表
        """
        templates = []
        for tid, info in self.index["templates"].items():
            if tag and tag not in info.get("tags", []):
                continue
            templates.append({
                "id": tid,
                "name": info["name"],
                "description": info["description"],
                "tags": info.get("tags", []),
                "format": info["format"],
                "created_at": info["created_at"]
            })
        return templates
    
    def update_schema(self, template_id: str, schema: Dict[str, Any]) -> bool:
        """
        更新模板的 Schema
        
        Args:
            template_id: 模板 ID
            schema: 新的 Schema 配置
            
        Returns:
            是否成功
        """
        if template_id not in self.index["templates"]:
            return False
        
        info = self.index["templates"][template_id]
        schema_path = self.storage_dir / info["schema"]
        
        with open(schema_path, 'w', encoding='utf-8') as f:
            yaml.dump(schema, f, allow_unicode=True, default_flow_style=False)
        
        info["updated_at"] = datetime.now().isoformat()
        self._save_index()
        
        return True
    
    def delete_template(self, template_id: str) -> bool:
        """
        删除模板
        
        Args:
            template_id: 模板 ID
            
        Returns:
            是否成功
        """
        if template_id not in self.index["templates"]:
            return False
        
        template_dir = self.storage_dir / template_id
        if template_dir.exists():
            shutil.rmtree(template_dir)
        
        del self.index["templates"][template_id]
        self._save_index()
        
        return True


if __name__ == '__main__':
    # 测试
    manager = TemplateManager()
    print(f"Storage dir: {manager.storage_dir}")
    print(f"Templates: {manager.list_templates()}")
