"""
DocxToHtml: DOCX 转 HTML 转换器（增强版）

将 Word 文档转换为 HTML，尽可能保留原始格式和样式。
"""

import re
import mammoth
from typing import Dict, Any, List


class DocxToHtml:
    """DOCX 转 HTML 转换器"""
    
    PLACEHOLDER_PATTERN = re.compile(r'\{\{(\w+)\}\}')
    
    # 自定义样式映射，保留更多格式
    STYLE_MAP = """
        p[style-name='Heading 1'] => h1:fresh
        p[style-name='Heading 2'] => h2:fresh
        p[style-name='Heading 3'] => h3:fresh
        p[style-name='Title'] => h1.title:fresh
        p[style-name='Subtitle'] => p.subtitle:fresh
        r[style-name='Strong'] => strong
        r[style-name='Emphasis'] => em
        p[style-name='Quote'] => blockquote:fresh
        p[style-name='List Paragraph'] => p.list-item:fresh
        table => table.docx-table
        tr => tr
        td => td
        th => th
    """
    
    def __init__(self, file_path: str = None, file_obj=None):
        """
        初始化转换器
        
        Args:
            file_path: DOCX 文件路径
            file_obj: 文件对象（二进制模式）
        """
        self.file_path = file_path
        self.file_obj = file_obj
        self.html = ""
        self.placeholders = []
    
    def _transform_element(self, element):
        """
        自定义元素转换，保留更多样式信息
        """
        # 处理加粗
        if element.bold:
            return mammoth.transforms.bold(element)
        # 处理斜体
        if element.italic:
            return mammoth.transforms.italic(element)
        return element
    
    def convert(self) -> Dict[str, Any]:
        """
        转换 DOCX 为 HTML（增强格式保留）
        
        Returns:
            包含 html 和 placeholders 的字典
        """
        convert_options = {
            "style_map": self.STYLE_MAP,
            "include_embedded_style_map": True,
            "include_default_style_map": True,
        }
        
        if self.file_path:
            with open(self.file_path, 'rb') as f:
                result = mammoth.convert_to_html(f, **convert_options)
        elif self.file_obj:
            result = mammoth.convert_to_html(self.file_obj, **convert_options)
        else:
            raise ValueError("需要提供 file_path 或 file_obj")
        
        # 添加增强样式
        self.html = self._add_enhanced_styles(result.value)
        self.placeholders = self._extract_placeholders(self.html)
        
        return {
            'html': self.html,
            'placeholders': self.placeholders,
            'messages': [msg.message for msg in result.messages]
        }
    
    def _add_enhanced_styles(self, html: str) -> str:
        """
        添加增强 CSS 样式以更好地显示文档
        """
        style_tag = """
        <style>
            .docx-content {
                font-family: 'Segoe UI', 'Microsoft YaHei', Arial, sans-serif;
                line-height: 1.8;
                color: #333;
            }
            .docx-content h1 { font-size: 24px; font-weight: bold; margin: 20px 0 10px; color: #1a1a1a; }
            .docx-content h2 { font-size: 20px; font-weight: bold; margin: 18px 0 8px; color: #2a2a2a; }
            .docx-content h3 { font-size: 16px; font-weight: bold; margin: 16px 0 6px; color: #3a3a3a; }
            .docx-content h1.title { font-size: 28px; text-align: center; color: #000; }
            .docx-content p.subtitle { font-size: 16px; text-align: center; color: #666; font-style: italic; }
            .docx-content p { margin: 8px 0; text-indent: 0; }
            .docx-content strong, .docx-content b { font-weight: bold; color: #000; }
            .docx-content em, .docx-content i { font-style: italic; }
            .docx-content u { text-decoration: underline; }
            .docx-content blockquote { 
                border-left: 4px solid #667eea; 
                padding-left: 16px; 
                margin: 16px 0; 
                color: #555;
                background: #f8f9fa;
                padding: 12px 16px;
                border-radius: 4px;
            }
            .docx-content ul, .docx-content ol { margin: 8px 0; padding-left: 24px; }
            .docx-content li { margin: 4px 0; }
            .docx-content table.docx-table { 
                border-collapse: collapse; 
                width: 100%; 
                margin: 16px 0;
                border: 1px solid #ddd;
            }
            .docx-content table.docx-table td, 
            .docx-content table.docx-table th { 
                border: 1px solid #ddd; 
                padding: 8px 12px; 
                text-align: left;
            }
            .docx-content table.docx-table th { 
                background: #f5f5f5; 
                font-weight: bold; 
            }
            .docx-content table.docx-table tr:nth-child(even) { 
                background: #fafafa; 
            }
            .docx-content img { max-width: 100%; height: auto; }
            .docx-content a { color: #667eea; text-decoration: none; }
            .docx-content a:hover { text-decoration: underline; }
            /* 段落首行缩进（中文风格） */
            .docx-content p.indent { text-indent: 2em; }
        </style>
        """
        return f'{style_tag}<div class="docx-content">{html}</div>'
    
    def convert_with_highlight(self) -> Dict[str, Any]:
        """
        转换 DOCX 为 HTML 并高亮占位符
        
        Returns:
            包含高亮后的 html 和 placeholders 的字典
        """
        result = self.convert()
        
        # 高亮占位符
        highlighted_html = self._highlight_placeholders(result['html'])
        
        return {
            'html': highlighted_html,
            'raw_html': result['html'],
            'placeholders': result['placeholders'],
            'messages': result['messages']
        }
    
    def _extract_placeholders(self, html: str) -> List[str]:
        """提取所有占位符名称"""
        matches = self.PLACEHOLDER_PATTERN.findall(html)
        return list(set(matches))
    
    def _highlight_placeholders(self, html: str) -> str:
        """
        高亮占位符
        
        用特殊样式的 span 标签包裹占位符
        """
        def replace_placeholder(match):
            name = match.group(1)
            full_match = match.group(0)
            return (
                f'<span class="placeholder" data-name="{name}" '
                f'style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); '
                f'color: white; padding: 2px 8px; border-radius: 4px; '
                f'font-family: monospace; font-weight: bold; display: inline-block;">'
                f'{full_match}</span>'
            )
        
        return self.PLACEHOLDER_PATTERN.sub(replace_placeholder, html)
    
    def fill_html(self, content_map: Dict[str, str]) -> str:
        """
        填充 HTML 中的占位符
        
        Args:
            content_map: 占位符名称 -> 填充内容 的映射
            
        Returns:
            填充后的 HTML
        """
        filled_html = self.html
        for name, content in content_map.items():
            pattern = f'{{{{{name}}}}}'
            # 高亮填充内容
            replacement = (
                f'<span class="filled-content" data-name="{name}" '
                f'style="background: rgba(16, 185, 129, 0.15); '
                f'border-bottom: 2px solid #10b981; padding: 2px 4px; '
                f'border-radius: 2px;">'
                f'{content}</span>'
            )
            filled_html = filled_html.replace(pattern, replacement)
        return filled_html


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        converter = DocxToHtml(sys.argv[1])
        result = converter.convert_with_highlight()
        print(f"Placeholders: {result['placeholders']}")
        print(f"HTML length: {len(result['html'])}")
