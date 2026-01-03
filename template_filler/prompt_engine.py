"""
PromptEngine: Prompt 构建引擎

将 Context（原始材料）与 Schema 中的 Prompt 组合，生成发送给 LLM 的完整 Prompt。
"""

from typing import Dict, Any, Optional


class PromptEngine:
    """Prompt 构建引擎"""
    
    DEFAULT_SYSTEM_PROMPT = """你是一个专业的文档内容生成助手。根据用户提供的原始材料，按照要求生成对应的内容。
要求：
1. 严格按照指定的格式和字数要求生成内容
2. 内容应该准确反映原始材料的核心信息
3. 语言应当正式、专业
4. 不要添加任何额外的解释或说明，只输出要求的内容本身"""
    
    def __init__(self, context: str, schema: Dict[str, Any]):
        """
        初始化 Prompt 引擎
        
        Args:
            context: 原始材料文本
            schema: Schema 配置，包含占位符定义
        """
        self.context = context
        self.schema = schema
        self.placeholders = schema.get('placeholders', {})
    
    def build_prompt(self, placeholder_name: str) -> str:
        """
        为指定占位符构建完整的 Prompt
        
        Args:
            placeholder_name: 占位符名称
            
        Returns:
            完整的 Prompt 字符串
        """
        if placeholder_name not in self.placeholders:
            raise ValueError(f"Placeholder '{placeholder_name}' not found in schema")
        
        placeholder_config = self.placeholders[placeholder_name]
        slot_prompt = placeholder_config.get('prompt', f'生成 {placeholder_name} 的内容')
        
        full_prompt = f"""## 原始材料

{self.context}

## 任务

{slot_prompt}

请直接输出结果，不要添加任何解释或前缀。"""
        
        return full_prompt
    
    def get_system_prompt(self) -> str:
        """
        获取系统 Prompt
        
        Returns:
            系统 Prompt 字符串
        """
        return self.schema.get('system_prompt', self.DEFAULT_SYSTEM_PROMPT)
    
    def get_mode(self, placeholder_name: str) -> str:
        """
        获取占位符的填充模式
        
        Args:
            placeholder_name: 占位符名称
            
        Returns:
            'llm' 或 'manual'
        """
        if placeholder_name not in self.placeholders:
            return 'llm'
        config = self.placeholders[placeholder_name]
        if isinstance(config, str):
            return 'llm'
        return config.get('mode', 'llm')
    
    def get_options_count(self, placeholder_name: str) -> int:
        """
        获取 select 模式下的选项数量
        
        Args:
            placeholder_name: 占位符名称
            
        Returns:
            选项数量，默认 1
        """
        if placeholder_name not in self.placeholders:
            return 1
        config = self.placeholders[placeholder_name]
        if isinstance(config, str):
            return 1
        return config.get('options_count', 1)
    
    def get_manual_value(self, placeholder_name: str) -> str:
        """
        获取手动模式下的值
        
        Args:
            placeholder_name: 占位符名称
            
        Returns:
            手动输入的值
        """
        if placeholder_name not in self.placeholders:
            return ""
        config = self.placeholders[placeholder_name]
        if isinstance(config, str):
            return ""
        return config.get('manualValue', "")
    
    def get_placeholder_names(self) -> list:
        """
        获取所有占位符名称
        
        Returns:
            占位符名称列表
        """
        return list(self.placeholders.keys())


if __name__ == '__main__':
    # 简单测试
    context = "这是一个关于人工智能在医疗领域应用的研究项目..."
    schema = {
        'placeholders': {
            'TITLE': {'prompt': '生成一个简洁的标题（10字以内）', 'mode': 'select', 'options_count': 3},
            'SUMMARY': {'prompt': '生成100字左右的摘要', 'mode': 'auto'}
        }
    }
    engine = PromptEngine(context, schema)
    print(engine.build_prompt('TITLE'))
