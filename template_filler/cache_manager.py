"""
CacheManager: LLM 响应缓存系统

缓存 LLM 生成的内容，避免重复调用，节省 Token 和时间。
"""

import os
import json
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta


class CacheManager:
    """LLM 响应缓存管理器"""
    
    def __init__(
        self,
        cache_dir: Optional[str] = None,
        ttl_hours: int = 24,
        enabled: bool = True
    ):
        """
        初始化缓存管理器
        
        Args:
            cache_dir: 缓存目录，默认为 ~/.template_filler/cache
            ttl_hours: 缓存有效期（小时）
            enabled: 是否启用缓存
        """
        self.enabled = enabled
        self.ttl_hours = ttl_hours
        
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = Path.home() / ".template_filler" / "cache"
        
        if self.enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _generate_key(self, prompt: str, model: str = "", system_prompt: str = "") -> str:
        """
        生成缓存键
        
        Args:
            prompt: 用户 prompt
            model: 模型名称
            system_prompt: 系统 prompt
            
        Returns:
            缓存键（MD5 哈希）
        """
        content = f"{model}|{system_prompt}|{prompt}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, prompt: str, model: str = "", system_prompt: str = "") -> Optional[str]:
        """
        获取缓存的响应
        
        Args:
            prompt: 用户 prompt
            model: 模型名称
            system_prompt: 系统 prompt
            
        Returns:
            缓存的响应，如果没有或已过期则返回 None
        """
        if not self.enabled:
            return None
        
        key = self._generate_key(prompt, model, system_prompt)
        cache_file = self.cache_dir / f"{key}.json"
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 检查是否过期
            created_at = datetime.fromisoformat(data.get('created_at', ''))
            if datetime.now() - created_at > timedelta(hours=self.ttl_hours):
                cache_file.unlink()  # 删除过期缓存
                return None
            
            return data.get('response')
        except (json.JSONDecodeError, ValueError, KeyError):
            return None
    
    def set(self, prompt: str, response: str, model: str = "", system_prompt: str = "") -> None:
        """
        存储响应到缓存
        
        Args:
            prompt: 用户 prompt
            response: LLM 响应
            model: 模型名称
            system_prompt: 系统 prompt
        """
        if not self.enabled:
            return
        
        key = self._generate_key(prompt, model, system_prompt)
        cache_file = self.cache_dir / f"{key}.json"
        
        data = {
            'prompt': prompt[:200] + '...' if len(prompt) > 200 else prompt,  # 截断长 prompt
            'response': response,
            'model': model,
            'created_at': datetime.now().isoformat()
        }
        
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def clear(self) -> int:
        """
        清除所有缓存
        
        Returns:
            删除的缓存文件数量
        """
        if not self.cache_dir.exists():
            return 0
        
        count = 0
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()
            count += 1
        
        return count
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            统计信息字典
        """
        if not self.cache_dir.exists():
            return {'count': 0, 'size_bytes': 0}
        
        files = list(self.cache_dir.glob("*.json"))
        total_size = sum(f.stat().st_size for f in files)
        
        return {
            'count': len(files),
            'size_bytes': total_size,
            'size_mb': round(total_size / 1024 / 1024, 2),
            'cache_dir': str(self.cache_dir)
        }


if __name__ == '__main__':
    # 测试
    cache = CacheManager()
    
    # 测试存储和获取
    cache.set("test prompt", "test response", "gpt-4")
    result = cache.get("test prompt", "gpt-4")
    print(f"Cached response: {result}")
    
    # 统计
    print(f"Stats: {cache.get_stats()}")
