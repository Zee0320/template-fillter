"""
单元测试：CacheManager 缓存管理器

测试 LLM 响应缓存功能。
"""

import os
import sys
import pytest
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from template_filler.cache_manager import CacheManager


class TestCacheManager:
    """CacheManager 单元测试"""
    
    @pytest.fixture
    def temp_cache_dir(self):
        """创建临时缓存目录"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        # 清理
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_init_creates_directory(self, temp_cache_dir):
        """测试初始化创建目录"""
        cache_path = os.path.join(temp_cache_dir, 'cache')
        cache = CacheManager(cache_dir=cache_path)
        assert os.path.exists(cache_path)
    
    def test_set_and_get(self, temp_cache_dir):
        """测试存储和获取"""
        cache = CacheManager(cache_dir=temp_cache_dir)
        
        prompt = "测试提示语"
        response = "测试响应"
        model = "gpt-4"
        
        cache.set(prompt, response, model)
        result = cache.get(prompt, model)
        
        assert result == response
    
    def test_get_miss(self, temp_cache_dir):
        """测试缓存未命中"""
        cache = CacheManager(cache_dir=temp_cache_dir)
        
        result = cache.get("不存在的提示语", "gpt-4")
        assert result is None
    
    def test_different_models(self, temp_cache_dir):
        """测试不同模型的缓存隔离"""
        cache = CacheManager(cache_dir=temp_cache_dir)
        
        prompt = "同一个提示语"
        
        cache.set(prompt, "GPT-4响应", "gpt-4")
        cache.set(prompt, "GPT-3.5响应", "gpt-3.5-turbo")
        
        assert cache.get(prompt, "gpt-4") == "GPT-4响应"
        assert cache.get(prompt, "gpt-3.5-turbo") == "GPT-3.5响应"
    
    def test_clear(self, temp_cache_dir):
        """测试清除缓存"""
        cache = CacheManager(cache_dir=temp_cache_dir)
        
        cache.set("prompt1", "response1", "gpt-4")
        cache.set("prompt2", "response2", "gpt-4")
        
        count = cache.clear()
        assert count == 2
        
        assert cache.get("prompt1", "gpt-4") is None
        assert cache.get("prompt2", "gpt-4") is None
    
    def test_disabled_cache(self, temp_cache_dir):
        """测试禁用缓存"""
        cache = CacheManager(cache_dir=temp_cache_dir, enabled=False)
        
        cache.set("prompt", "response", "gpt-4")
        result = cache.get("prompt", "gpt-4")
        
        assert result is None
    
    def test_get_stats(self, temp_cache_dir):
        """测试统计信息"""
        cache = CacheManager(cache_dir=temp_cache_dir)
        
        cache.set("prompt1", "response1", "gpt-4")
        cache.set("prompt2", "response2", "gpt-4")
        
        stats = cache.get_stats()
        
        assert stats['count'] == 2
        assert stats['size_bytes'] > 0
        assert 'cache_dir' in stats


class TestCacheKeyGeneration:
    """缓存键生成测试"""
    
    def test_same_inputs_same_key(self):
        """相同输入应生成相同的键"""
        cache = CacheManager(enabled=False)  # 不需要实际存储
        
        key1 = cache._generate_key("prompt", "model", "system")
        key2 = cache._generate_key("prompt", "model", "system")
        
        assert key1 == key2
    
    def test_different_inputs_different_keys(self):
        """不同输入应生成不同的键"""
        cache = CacheManager(enabled=False)
        
        key1 = cache._generate_key("prompt1", "model", "system")
        key2 = cache._generate_key("prompt2", "model", "system")
        
        assert key1 != key2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
