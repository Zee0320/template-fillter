"""
LLMClient: LLM API 封装

支持 OpenAI API，包含重试机制、错误处理和缓存支持。
"""

import os
import time
from typing import Optional, List
from openai import OpenAI

from .cache_manager import CacheManager


class LLMClient:
    """LLM API 客户端"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        cache_enabled: bool = True,
        cache_ttl_hours: int = 24
    ):
        """
        初始化 LLM 客户端
        
        Args:
            api_key: API 密钥，默认从环境变量 OPENAI_API_KEY 获取
            base_url: API 基础 URL，默认从环境变量 OPENAI_BASE_URL 获取
            model: 使用的模型名称，默认从 OPENAI_MODEL 获取，否则使用 qwen-plus
            max_retries: 最大重试次数
            retry_delay: 重试间隔（秒）
            cache_enabled: 是否启用缓存
            cache_ttl_hours: 缓存有效期（小时）
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL")
        self.model = model or os.getenv("OPENAI_MODEL", "qwen-plus")
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        if not self.api_key:
            raise ValueError("API key is required. Set OPENAI_API_KEY environment variable or pass api_key parameter.")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        
        # 初始化缓存
        self.cache = CacheManager(enabled=cache_enabled, ttl_hours=cache_ttl_hours)
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        use_cache: bool = True
    ) -> str:
        """
        生成文本
        
        Args:
            prompt: 用户 prompt
            system_prompt: 系统 prompt
            temperature: 温度参数
            max_tokens: 最大生成 token 数
            use_cache: 是否使用缓存
            
        Returns:
            生成的文本
        """
        # 尝试从缓存获取
        if use_cache:
            cached = self.cache.get(prompt, self.model, system_prompt or "")
            if cached:
                return cached
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                result = response.choices[0].message.content.strip()
                
                # 存入缓存
                if use_cache:
                    self.cache.set(prompt, result, self.model, system_prompt or "")
                
                return result
            except Exception as e:
                if attempt < self.max_retries - 1:
                    print(f"LLM API error (attempt {attempt + 1}/{self.max_retries}): {e}")
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    raise RuntimeError(f"LLM API failed after {self.max_retries} attempts: {e}")
    
    def generate_multiple(
        self,
        prompt: str,
        count: int = 3,
        system_prompt: Optional[str] = None,
        temperature: float = 0.9,
        max_tokens: int = 1000
    ) -> List[str]:
        """
        生成多个候选文本（用于 select 模式）
        
        Args:
            prompt: 用户 prompt
            count: 生成数量
            system_prompt: 系统 prompt
            temperature: 温度参数（较高以增加多样性）
            max_tokens: 最大生成 token 数
            
        Returns:
            生成的文本列表
        """
        results = []
        for i in range(count):
            # 稍微调整温度以获得不同结果
            temp = min(temperature + i * 0.05, 1.0)
            # 不使用缓存以获得不同结果
            result = self.generate(
                prompt=f"{prompt}\n\n请提供第 {i + 1} 种不同的表达方式。",
                system_prompt=system_prompt,
                temperature=temp,
                max_tokens=max_tokens,
                use_cache=False
            )
            results.append(result)
        return results
    
    def get_cache_stats(self):
        """获取缓存统计信息"""
        return self.cache.get_stats()
    
    def clear_cache(self):
        """清除缓存"""
        return self.cache.clear()


if __name__ == '__main__':
    # 简单测试
    client = LLMClient()
    result = client.generate("Say hello in one word.")
    print(f"Result: {result}")
    print(f"Cache stats: {client.get_cache_stats()}")
