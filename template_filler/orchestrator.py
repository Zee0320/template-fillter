"""
Orchestrator: 流程协调器

协调 TemplateParser、PromptEngine、LLMClient 完成整个模板填充流程。
"""

import yaml
from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor, as_completed

from .template_parser import TemplateParser
from .prompt_engine import PromptEngine
from .llm_client import LLMClient


class Orchestrator:
    """流程协调器"""
    
    def __init__(
        self,
        template_path: str,
        context: str,
        schema: Dict[str, Any],
        llm_client: Optional[LLMClient] = None,
        max_workers: int = 5
    ):
        """
        初始化协调器
        
        Args:
            template_path: Word 模板文件路径
            context: 原始材料文本
            schema: Schema 配置
            llm_client: LLM 客户端实例，如果为 None 则创建默认客户端
            max_workers: 并发 worker 数量
        """
        self.template_path = template_path
        self.context = context
        self.schema = schema
        self.max_workers = max_workers
        
        self.template_parser = TemplateParser(template_path)
        self.prompt_engine = PromptEngine(context, schema)
        self.llm_client = llm_client or LLMClient()
    
    @classmethod
    def from_files(
        cls,
        template_path: str,
        context_path: str,
        schema_path: str,
        llm_client: Optional[LLMClient] = None
    ) -> 'Orchestrator':
        """
        从文件路径创建 Orchestrator
        
        Args:
            template_path: Word 模板路径
            context_path: Context 文本文件路径
            schema_path: Schema YAML 文件路径
            llm_client: LLM 客户端实例
            
        Returns:
            Orchestrator 实例
        """
        with open(context_path, 'r', encoding='utf-8') as f:
            context = f.read()
        
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema = yaml.safe_load(f)
        
        return cls(template_path, context, schema, llm_client)
    
    def run(self, output_path: str, selections: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
        """
        执行模板填充流程
        
        Args:
            output_path: 输出文件路径
            selections: select 模式下的选择（占位符 -> 选项索引），如果为 None 则使用第一个选项
            
        Returns:
            执行结果，包含生成的内容和元信息
        """
        # 1. 获取模板中的占位符
        template_placeholders = self.template_parser.find_placeholders()
        schema_placeholders = self.prompt_engine.get_placeholder_names()
        
        # 合并占位符列表（模板中的 + Schema 中定义的）
        all_placeholders = list(set(template_placeholders) & set(schema_placeholders))
        
        if not all_placeholders:
            print("Warning: No matching placeholders found between template and schema")
            all_placeholders = template_placeholders
        
        # 2. 并发生成内容
        results = {}
        generated_options = {}  # 存储 select 模式的所有选项
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}
            for placeholder in all_placeholders:
                mode = self.prompt_engine.get_mode(placeholder)
                prompt = self.prompt_engine.build_prompt(placeholder)
                system_prompt = self.prompt_engine.get_system_prompt()
                
                if mode == 'select':
                    count = self.prompt_engine.get_options_count(placeholder)
                    future = executor.submit(
                        self._generate_multiple,
                        placeholder, prompt, system_prompt, count
                    )
                else:
                    future = executor.submit(
                        self._generate_single,
                        placeholder, prompt, system_prompt
                    )
                futures[future] = (placeholder, mode)
            
            for future in as_completed(futures):
                placeholder, mode = futures[future]
                try:
                    content = future.result()
                    if mode == 'select':
                        generated_options[placeholder] = content
                        # 使用选择或默认第一个
                        selected_idx = (selections or {}).get(placeholder, 0)
                        results[placeholder] = content[selected_idx]
                    else:
                        results[placeholder] = content
                except Exception as e:
                    print(f"Error generating content for {placeholder}: {e}")
                    results[placeholder] = f"[生成失败: {placeholder}]"
        
        # 3. 填充模板
        self.template_parser.fill_placeholders(results)
        
        # 4. 保存文件
        self.template_parser.save(output_path)
        
        return {
            'output_path': output_path,
            'filled_placeholders': results,
            'options': generated_options
        }
    
    def preview(self) -> Dict[str, Any]:
        """
        预览生成结果（不保存文件）
        
        Returns:
            预览结果，包含所有生成的内容和选项
        """
        template_placeholders = self.template_parser.find_placeholders()
        schema_placeholders = self.prompt_engine.get_placeholder_names()
        all_placeholders = list(set(template_placeholders) & set(schema_placeholders))
        
        results = {}
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}
            for placeholder in all_placeholders:
                mode = self.prompt_engine.get_mode(placeholder)
                count = self.prompt_engine.get_options_count(placeholder)
                
                # 手动模式直接使用配置的值，不调用 LLM
                if mode == 'manual':
                    manual_value = self.prompt_engine.get_manual_value(placeholder)
                    results[placeholder] = {
                        'mode': 'manual',
                        'content': [manual_value],
                        'selected': 0
                    }
                    continue
                
                prompt = self.prompt_engine.build_prompt(placeholder)
                system_prompt = self.prompt_engine.get_system_prompt()
                
                # 使用 options_count 判断是否生成多个
                if count > 1:
                    future = executor.submit(
                        self._generate_multiple,
                        placeholder, prompt, system_prompt, count
                    )
                else:
                    future = executor.submit(
                        self._generate_single,
                        placeholder, prompt, system_prompt
                    )
                futures[future] = (placeholder, mode, count)
            
            for future in as_completed(futures):
                placeholder, mode, count = futures[future]
                try:
                    content = future.result()
                    results[placeholder] = {
                        'mode': mode,
                        'content': content if count > 1 else [content],
                        'selected': 0
                    }
                except Exception as e:
                    results[placeholder] = {
                        'mode': mode,
                        'content': [f"[生成失败: {e}]"],
                        'selected': 0
                    }
        
        return {'placeholders': results}
    
    def _generate_single(self, placeholder: str, prompt: str, system_prompt: str) -> str:
        """生成单个内容"""
        return self.llm_client.generate(prompt, system_prompt)
    
    def _generate_multiple(self, placeholder: str, prompt: str, system_prompt: str, count: int) -> List[str]:
        """生成多个候选内容"""
        return self.llm_client.generate_multiple(prompt, count, system_prompt)


if __name__ == '__main__':
    # 简单测试
    import sys
    if len(sys.argv) >= 4:
        orchestrator = Orchestrator.from_files(sys.argv[1], sys.argv[2], sys.argv[3])
        result = orchestrator.run(sys.argv[4] if len(sys.argv) > 4 else 'output.docx')
        print(f"Result: {result}")
