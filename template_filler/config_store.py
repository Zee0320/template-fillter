"""
ConfigStore: 配置存储

保存和加载模板的占位符配置。
"""

import os
import json
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime


class ConfigStore:
    """配置存储管理器"""
    
    def __init__(self, storage_dir: Optional[str] = None):
        """
        初始化配置存储
        
        Args:
            storage_dir: 存储目录，默认为 ~/.template_filler/configs
        """
        if storage_dir:
            self.storage_dir = Path(storage_dir)
        else:
            self.storage_dir = Path.home() / ".template_filler" / "configs"
        
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.storage_dir / "index.json"
        self._load_index()
    
    def _load_index(self):
        """加载配置索引"""
        if self.index_file.exists():
            with open(self.index_file, 'r', encoding='utf-8') as f:
                self.index = json.load(f)
        else:
            self.index = {"configs": {}}
    
    def _save_index(self):
        """保存配置索引"""
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(self.index, f, ensure_ascii=False, indent=2)
    
    def _generate_id(self, name: str) -> str:
        """生成配置 ID"""
        base_id = name.lower().replace(' ', '_').replace('/', '_')
        # 确保唯一性
        if base_id in self.index["configs"]:
            base_id = f"{base_id}_{len(self.index['configs'])}"
        return base_id
    
    def save(
        self,
        name: str,
        template_name: str,
        placeholders: Dict[str, Any],
        description: str = ""
    ) -> str:
        """
        保存配置
        
        Args:
            name: 配置名称
            template_name: 关联的模板名称
            placeholders: 占位符配置
            description: 描述
            
        Returns:
            配置 ID
        """
        config_id = self._generate_id(name)
        
        config_data = {
            "name": name,
            "template_name": template_name,
            "description": description,
            "placeholders": placeholders,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # 保存到文件
        config_file = self.storage_dir / f"{config_id}.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
        
        # 更新索引
        self.index["configs"][config_id] = {
            "name": name,
            "template_name": template_name,
            "description": description,
            "created_at": config_data["created_at"]
        }
        self._save_index()
        
        return config_id
    
    def load(self, config_id: str) -> Optional[Dict[str, Any]]:
        """
        加载配置
        
        Args:
            config_id: 配置 ID
            
        Returns:
            配置数据
        """
        if config_id not in self.index["configs"]:
            return None
        
        config_file = self.storage_dir / f"{config_id}.json"
        if not config_file.exists():
            return None
        
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def list_configs(self, template_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        列出所有配置
        
        Args:
            template_name: 可选，按模板名过滤
            
        Returns:
            配置列表
        """
        configs = []
        for config_id, info in self.index["configs"].items():
            if template_name and info.get("template_name") != template_name:
                continue
            configs.append({
                "id": config_id,
                **info
            })
        return sorted(configs, key=lambda x: x.get("created_at", ""), reverse=True)
    
    def delete(self, config_id: str) -> bool:
        """
        删除配置
        
        Args:
            config_id: 配置 ID
            
        Returns:
            是否成功
        """
        if config_id not in self.index["configs"]:
            return False
        
        config_file = self.storage_dir / f"{config_id}.json"
        if config_file.exists():
            config_file.unlink()
        
        del self.index["configs"][config_id]
        self._save_index()
        
        return True


# 全局实例
config_store = ConfigStore()


if __name__ == '__main__':
    # 测试
    store = ConfigStore()
    print(f"Storage dir: {store.storage_dir}")
    print(f"Configs: {store.list_configs()}")
