"""
AuditLogger: 操作日志记录系统

记录所有模板填充操作，包括输入、输出和元数据，便于追溯和审计。
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid


class AuditLogger:
    """操作日志记录器"""
    
    def __init__(
        self,
        log_dir: Optional[str] = None,
        enabled: bool = True,
        console_output: bool = False
    ):
        """
        初始化日志记录器
        
        Args:
            log_dir: 日志目录，默认为 ~/.template_filler/logs
            enabled: 是否启用日志
            console_output: 是否同时输出到控制台
        """
        self.enabled = enabled
        self.console_output = console_output
        
        if log_dir:
            self.log_dir = Path(log_dir)
        else:
            self.log_dir = Path.home() / ".template_filler" / "logs"
        
        if self.enabled:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            self._setup_logger()
    
    def _setup_logger(self):
        """设置 Python 日志器"""
        self.logger = logging.getLogger('template_filler.audit')
        self.logger.setLevel(logging.INFO)
        
        # 文件处理器
        log_file = self.log_dir / f"audit_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        self.logger.addHandler(file_handler)
        
        # 控制台处理器
        if self.console_output:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            ))
            self.logger.addHandler(console_handler)
    
    def log_operation(
        self,
        operation: str,
        template_name: str,
        placeholders: List[str],
        context_preview: str = "",
        result: Optional[Dict[str, str]] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        记录一次操作
        
        Args:
            operation: 操作类型 (fill, preview, generate)
            template_name: 模板文件名
            placeholders: 填充的占位符列表
            context_preview: 原始材料预览（前200字）
            result: 填充结果
            error: 错误信息（如有）
            metadata: 其他元数据
            
        Returns:
            操作 ID
        """
        if not self.enabled:
            return ""
        
        operation_id = str(uuid.uuid4())[:8]
        
        log_entry = {
            'id': operation_id,
            'timestamp': datetime.now().isoformat(),
            'operation': operation,
            'template': template_name,
            'placeholders': placeholders,
            'context_preview': context_preview[:200] + '...' if len(context_preview) > 200 else context_preview,
            'status': 'error' if error else 'success',
            'error': error,
            'metadata': metadata or {}
        }
        
        # 记录结果（截断过长内容）
        if result:
            log_entry['result_preview'] = {
                k: v[:100] + '...' if len(v) > 100 else v
                for k, v in result.items()
            }
        
        # 写入 JSON 日志文件
        detail_file = self.log_dir / f"operation_{operation_id}.json"
        with open(detail_file, 'w', encoding='utf-8') as f:
            json.dump(log_entry, f, ensure_ascii=False, indent=2)
        
        # 写入文本日志
        status = 'ERROR' if error else 'SUCCESS'
        self.logger.info(
            f"[{operation_id}] {operation.upper()} | {template_name} | "
            f"{len(placeholders)} placeholders | {status}"
        )
        
        if error:
            self.logger.error(f"[{operation_id}] Error: {error}")
        
        return operation_id
    
    def get_recent_operations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取最近的操作记录
        
        Args:
            limit: 返回的记录数量
            
        Returns:
            操作记录列表
        """
        if not self.log_dir.exists():
            return []
        
        operation_files = sorted(
            self.log_dir.glob("operation_*.json"),
            key=lambda f: f.stat().st_mtime,
            reverse=True
        )[:limit]
        
        operations = []
        for f in operation_files:
            try:
                with open(f, 'r', encoding='utf-8') as file:
                    operations.append(json.load(file))
            except (json.JSONDecodeError, IOError):
                pass
        
        return operations
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取日志统计信息
        
        Returns:
            统计信息字典
        """
        if not self.log_dir.exists():
            return {'total_operations': 0, 'log_dir': str(self.log_dir)}
        
        operation_files = list(self.log_dir.glob("operation_*.json"))
        log_files = list(self.log_dir.glob("audit_*.log"))
        
        total_size = sum(f.stat().st_size for f in operation_files + log_files)
        
        return {
            'total_operations': len(operation_files),
            'log_files': len(log_files),
            'size_bytes': total_size,
            'size_mb': round(total_size / 1024 / 1024, 2),
            'log_dir': str(self.log_dir)
        }
    
    def clear_old_logs(self, days: int = 30) -> int:
        """
        清理旧日志
        
        Args:
            days: 保留最近多少天的日志
            
        Returns:
            删除的文件数量
        """
        if not self.log_dir.exists():
            return 0
        
        cutoff = datetime.now().timestamp() - (days * 24 * 3600)
        count = 0
        
        for f in self.log_dir.glob("*"):
            if f.stat().st_mtime < cutoff:
                f.unlink()
                count += 1
        
        return count


if __name__ == '__main__':
    # 测试
    logger = AuditLogger(console_output=True)
    
    op_id = logger.log_operation(
        operation='fill',
        template_name='test_template.docx',
        placeholders=['TITLE', 'SUMMARY'],
        context_preview='这是测试内容...',
        result={'TITLE': '测试标题', 'SUMMARY': '测试摘要'}
    )
    
    print(f"Operation ID: {op_id}")
    print(f"Stats: {logger.get_stats()}")
    print(f"Recent: {logger.get_recent_operations(5)}")
