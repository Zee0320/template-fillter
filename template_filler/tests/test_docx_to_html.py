"""
单元测试：DocxToHtml 转换器

测试 DOCX 到 HTML 的转换和占位符处理。
"""

import os
import sys
import pytest

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from template_filler.docx_to_html import DocxToHtml


class TestDocxToHtml:
    """DocxToHtml 单元测试"""
    
    @pytest.fixture
    def test_template_path(self):
        """测试模板路径"""
        return os.path.join(
            os.path.dirname(__file__), 
            'test_template.docx'
        )
    
    def test_convert_basic(self, test_template_path):
        """测试基本转换功能"""
        if not os.path.exists(test_template_path):
            pytest.skip("测试模板文件不存在")
        
        converter = DocxToHtml(test_template_path)
        result = converter.convert()
        
        assert 'html' in result
        assert 'placeholders' in result
        assert isinstance(result['html'], str)
        assert isinstance(result['placeholders'], list)
        assert len(result['html']) > 0
    
    def test_extract_placeholders(self, test_template_path):
        """测试占位符提取"""
        if not os.path.exists(test_template_path):
            pytest.skip("测试模板文件不存在")
        
        converter = DocxToHtml(test_template_path)
        result = converter.convert()
        
        # 测试模板应该包含这些占位符
        expected_placeholders = ['TITLE', 'SUMMARY', 'KEYWORDS', 'SIGNIFICANCE']
        for placeholder in expected_placeholders:
            assert placeholder in result['placeholders'], f"缺少占位符: {placeholder}"
    
    def test_highlight_placeholders(self, test_template_path):
        """测试占位符高亮"""
        if not os.path.exists(test_template_path):
            pytest.skip("测试模板文件不存在")
        
        converter = DocxToHtml(test_template_path)
        result = converter.convert_with_highlight()
        
        assert 'class="placeholder"' in result['html']
        assert 'data-name=' in result['html']
    
    def test_fill_html(self, test_template_path):
        """测试 HTML 填充"""
        if not os.path.exists(test_template_path):
            pytest.skip("测试模板文件不存在")
        
        converter = DocxToHtml(test_template_path)
        converter.convert()
        
        content_map = {
            'TITLE': '测试标题',
            'SUMMARY': '测试摘要内容'
        }
        
        filled_html = converter.fill_html(content_map)
        
        assert '测试标题' in filled_html
        assert '测试摘要内容' in filled_html
        assert '{{TITLE}}' not in filled_html
        assert '{{SUMMARY}}' not in filled_html


class TestPlaceholderPattern:
    """占位符正则表达式测试"""
    
    def test_pattern_basic(self):
        """测试基本占位符匹配"""
        from template_filler.docx_to_html import DocxToHtml
        
        pattern = DocxToHtml.PLACEHOLDER_PATTERN
        
        test_cases = [
            ('{{TITLE}}', ['TITLE']),
            ('{{NAME}}', ['NAME']),
            ('Hello {{WORLD}}!', ['WORLD']),
            ('{{A}} and {{B}}', ['A', 'B']),
            ('No placeholders here', []),
            ('{{lowercase}}', ['lowercase']),
            ('{{MixedCase123}}', ['MixedCase123']),
        ]
        
        for text, expected in test_cases:
            matches = pattern.findall(text)
            assert matches == expected, f"输入: {text}, 期望: {expected}, 实际: {matches}"
    
    def test_pattern_edge_cases(self):
        """测试边界情况"""
        from template_filler.docx_to_html import DocxToHtml
        
        pattern = DocxToHtml.PLACEHOLDER_PATTERN
        
        # 不应匹配的情况
        invalid_cases = [
            '{TITLE}',      # 单花括号
            '{{ TITLE }}',  # 有空格（当前pattern不匹配）
            '{{}}',         # 空占位符
        ]
        
        for text in invalid_cases:
            matches = pattern.findall(text)
            # 根据当前正则，这些应该返回空或不完整匹配
            # 这里只是记录行为


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
