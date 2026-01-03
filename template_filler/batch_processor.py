"""
BatchProcessor: 批量处理器

支持多份 Context 输入和多模板批量处理。
"""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from .orchestrator import Orchestrator
from .llm_client import LLMClient
from .audit_logger import AuditLogger


class BatchProcessor:
    """批量处理器"""
    
    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        max_workers: int = 3,
        output_dir: Optional[str] = None
    ):
        """
        初始化批量处理器
        
        Args:
            llm_client: LLM 客户端实例
            max_workers: 最大并发任务数
            output_dir: 输出目录
        """
        self.llm_client = llm_client or LLMClient()
        self.max_workers = max_workers
        self.output_dir = Path(output_dir) if output_dir else Path.cwd() / "batch_output"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.audit_logger = AuditLogger()
    
    def process_multiple_contexts(
        self,
        template_path: str,
        contexts: List[str],
        schema: Dict[str, Any],
        output_prefix: str = "output"
    ) -> List[Dict[str, Any]]:
        """
        使用同一模板处理多份 Context
        
        Args:
            template_path: 模板文件路径
            contexts: Context 列表
            schema: Schema 配置
            output_prefix: 输出文件前缀
            
        Returns:
            处理结果列表
        """
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}
            
            for i, context in enumerate(contexts):
                output_path = self.output_dir / f"{output_prefix}_{i + 1}.docx"
                future = executor.submit(
                    self._process_single,
                    template_path,
                    context,
                    schema,
                    str(output_path),
                    i + 1
                )
                futures[future] = i
            
            for future in as_completed(futures):
                idx = futures[future]
                try:
                    result = future.result()
                    results.append({
                        'index': idx,
                        'success': True,
                        'output_path': result['output_path'],
                        'placeholders': result['filled_placeholders']
                    })
                except Exception as e:
                    results.append({
                        'index': idx,
                        'success': False,
                        'error': str(e)
                    })
        
        # 按索引排序
        results.sort(key=lambda x: x['index'])
        return results
    
    def process_multiple_templates(
        self,
        template_paths: List[str],
        context: str,
        schemas: List[Dict[str, Any]],
        output_prefix: str = "output"
    ) -> List[Dict[str, Any]]:
        """
        使用同一 Context 处理多个模板
        
        Args:
            template_paths: 模板路径列表
            context: Context 文本
            schemas: Schema 列表（与模板对应）
            output_prefix: 输出文件前缀
            
        Returns:
            处理结果列表
        """
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}
            
            for i, (template_path, schema) in enumerate(zip(template_paths, schemas)):
                template_name = Path(template_path).stem
                output_path = self.output_dir / f"{output_prefix}_{template_name}.docx"
                future = executor.submit(
                    self._process_single,
                    template_path,
                    context,
                    schema,
                    str(output_path),
                    i + 1
                )
                futures[future] = (i, template_name)
            
            for future in as_completed(futures):
                idx, name = futures[future]
                try:
                    result = future.result()
                    results.append({
                        'index': idx,
                        'template': name,
                        'success': True,
                        'output_path': result['output_path'],
                        'placeholders': result['filled_placeholders']
                    })
                except Exception as e:
                    results.append({
                        'index': idx,
                        'template': name,
                        'success': False,
                        'error': str(e)
                    })
        
        results.sort(key=lambda x: x['index'])
        return results
    
    def _process_single(
        self,
        template_path: str,
        context: str,
        schema: Dict[str, Any],
        output_path: str,
        task_id: int
    ) -> Dict[str, Any]:
        """处理单个任务"""
        print(f"[Batch] Processing task {task_id}...")
        
        orchestrator = Orchestrator(
            template_path=template_path,
            context=context,
            schema=schema,
            llm_client=self.llm_client
        )
        
        result = orchestrator.run(output_path)
        
        # 记录日志
        self.audit_logger.log_operation(
            operation='batch_fill',
            template_name=Path(template_path).name,
            placeholders=list(result['filled_placeholders'].keys()),
            context_preview=context[:200],
            result=result['filled_placeholders'],
            metadata={'task_id': task_id, 'batch': True}
        )
        
        return result


if __name__ == '__main__':
    # 测试
    processor = BatchProcessor()
    print(f"Output dir: {processor.output_dir}")
