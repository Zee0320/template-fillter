"""
PlaceholderDetector: 占位符自动检测

自动扫描模板文件，检测并生成 Schema 配置建议。
"""

import re
from pathlib import Path
from typing import List, Dict, Any, Optional

from .template_parser import TemplateParser
from .excel_parser import ExcelParser


class PlaceholderDetector:
    """占位符自动检测器"""
    
    # 常见占位符名称到提示语的映射
    COMMON_PROMPTS = {
        'TITLE': '根据内容生成一个简洁的标题（15字以内）',
        '标题': '根据内容生成一个简洁的标题（15字以内）',
        'SUMMARY': '根据内容生成一段100字左右的摘要',
        '摘要': '根据内容生成一段100字左右的摘要',
        'ABSTRACT': '根据内容生成一段100字左右的摘要',
        'SIGNIFICANCE': '总结内容的意义和价值（50字左右）',
        '意义': '总结内容的意义和价值（50字左右）',
        'KEYWORDS': '提取5个核心关键词，用顿号分隔',
        '关键词': '提取5个核心关键词，用顿号分隔',
        'CONCLUSION': '根据内容生成结论（100字左右）',
        '结论': '根据内容生成结论（100字左右）',
        'BACKGROUND': '根据内容描述背景信息（100字左右）',
        '背景': '根据内容描述背景信息（100字左右）',
        'AUTHOR': '从内容中提取作者信息',
        '作者': '从内容中提取作者信息',
        'DATE': '从内容中提取日期信息',
        '日期': '从内容中提取日期信息',
        'NAME': '从内容中提取名称',
        '名称': '从内容中提取名称',
    }
    
    # 需要 select 模式的占位符
    SELECT_MODE_PLACEHOLDERS = {'TITLE', '标题', 'SUMMARY', '摘要', 'ABSTRACT'}
    
    def __init__(self):
        pass
    
    def detect(self, template_path: str) -> Dict[str, Any]:
        """
        检测模板中的占位符并生成 Schema 建议
        
        Args:
            template_path: 模板文件路径
            
        Returns:
            生成的 Schema 配置
        """
        ext = Path(template_path).suffix.lower()
        
        if ext == '.docx':
            parser = TemplateParser(template_path)
        elif ext == '.xlsx':
            parser = ExcelParser(template_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}")
        
        placeholders = parser.find_placeholders()
        
        if hasattr(parser, 'close'):
            parser.close()
        
        return self._generate_schema(placeholders)
    
    def _generate_schema(self, placeholders: List[str]) -> Dict[str, Any]:
        """
        根据占位符列表生成 Schema
        
        Args:
            placeholders: 占位符名称列表
            
        Returns:
            Schema 配置
        """
        schema = {
            'placeholders': {}
        }
        
        for name in placeholders:
            # 查找匹配的提示语
            prompt = self._get_suggested_prompt(name)
            
            # 所有占位符默认使用 llm 模式，options_count 为 1
            config = {
                'prompt': prompt,
                'mode': 'llm',
                'options_count': 1
            }
            
            schema['placeholders'][name] = config
        
        return schema
    
    def _get_suggested_prompt(self, placeholder_name: str) -> str:
        """获取建议的提示语"""
        name_upper = placeholder_name.upper()
        
        # 精确匹配
        if name_upper in self.COMMON_PROMPTS:
            return self.COMMON_PROMPTS[name_upper]
        if placeholder_name in self.COMMON_PROMPTS:
            return self.COMMON_PROMPTS[placeholder_name]
        
        # 部分匹配
        for key, prompt in self.COMMON_PROMPTS.items():
            if key in name_upper or name_upper in key:
                return prompt
        
        # 默认提示语
        return f'根据内容生成 {placeholder_name} 的内容'
    
    def _get_suggested_mode(self, placeholder_name: str) -> str:
        """获取建议的填充模式"""
        name_upper = placeholder_name.upper()
        
        if name_upper in self.SELECT_MODE_PLACEHOLDERS or placeholder_name in self.SELECT_MODE_PLACEHOLDERS:
            return 'select'
        
        return 'auto'
    
    def analyze_template(self, template_path: str) -> Dict[str, Any]:
        """
        分析模板并返回详细信息
        
        Args:
            template_path: 模板文件路径
            
        Returns:
            分析结果
        """
        ext = Path(template_path).suffix.lower()
        
        if ext == '.docx':
            parser = TemplateParser(template_path)
        elif ext == '.xlsx':
            parser = ExcelParser(template_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}")
        
        placeholders = parser.find_placeholders()
        
        if hasattr(parser, 'close'):
            parser.close()
        
        schema = self._generate_schema(placeholders)
        
        return {
            'file': template_path,
            'format': ext[1:],
            'placeholders_count': len(placeholders),
            'placeholders': placeholders,
            'suggested_schema': schema,
            'select_mode_count': sum(
                1 for p in schema['placeholders'].values() 
                if p.get('mode') == 'select'
            ),
            'auto_mode_count': sum(
                1 for p in schema['placeholders'].values() 
                if p.get('mode') == 'auto'
            )
        }


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        detector = PlaceholderDetector()
        result = detector.analyze_template(sys.argv[1])
        import json
        print(json.dumps(result, ensure_ascii=False, indent=2))
