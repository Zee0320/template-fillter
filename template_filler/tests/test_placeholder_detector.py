"""
单元测试：PlaceholderDetector 占位符检测器

测试占位符自动检测和 Schema 生成功能。
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from template_filler.placeholder_detector import PlaceholderDetector


class TestPlaceholderDetector:
    """PlaceholderDetector 单元测试"""
    
    @pytest.fixture
    def detector(self):
        """创建检测器实例"""
        return PlaceholderDetector()
    
    @pytest.fixture
    def test_template_path(self):
        """测试模板路径"""
        return os.path.join(
            os.path.dirname(__file__), 
            'test_template.docx'
        )
    
    def test_detect_docx(self, detector, test_template_path):
        """测试 DOCX 文件检测"""
        if not os.path.exists(test_template_path):
            pytest.skip("测试模板文件不存在")
        
        schema = detector.detect(test_template_path)
        
        assert 'placeholders' in schema
        assert len(schema['placeholders']) > 0
    
    def test_generate_schema_structure(self, detector):
        """测试生成的 Schema 结构"""
        placeholders = ['TITLE', 'SUMMARY', 'KEYWORDS']
        schema = detector._generate_schema(placeholders)
        
        assert 'placeholders' in schema
        
        for name in placeholders:
            assert name in schema['placeholders']
            config = schema['placeholders'][name]
            assert 'prompt' in config
            assert 'mode' in config
            assert config['mode'] in ['auto', 'select']
    
    def test_suggested_prompts(self, detector):
        """测试建议的提示语"""
        placeholders = ['TITLE', 'SUMMARY', 'KEYWORDS', 'CONCLUSION']
        schema = detector._generate_schema(placeholders)
        
        # TITLE 应该有相关的提示语
        title_prompt = schema['placeholders']['TITLE']['prompt']
        assert '标题' in title_prompt or 'title' in title_prompt.lower()
        
        # KEYWORDS 应该有关键词相关提示
        keywords_prompt = schema['placeholders']['KEYWORDS']['prompt']
        assert '关键词' in keywords_prompt or 'keyword' in keywords_prompt.lower()
    
    def test_select_mode_detection(self, detector):
        """测试 select 模式检测"""
        # TITLE 和 SUMMARY 应该是 select 模式
        placeholders = ['TITLE', 'SUMMARY', 'DATE', 'AUTHOR']
        schema = detector._generate_schema(placeholders)
        
        assert schema['placeholders']['TITLE']['mode'] == 'select'
        assert schema['placeholders']['SUMMARY']['mode'] == 'select'
        assert schema['placeholders']['DATE']['mode'] == 'auto'
        assert schema['placeholders']['AUTHOR']['mode'] == 'auto'
    
    def test_options_count_for_select(self, detector):
        """测试 select 模式的选项数量"""
        placeholders = ['TITLE']
        schema = detector._generate_schema(placeholders)
        
        assert 'options_count' in schema['placeholders']['TITLE']
        assert schema['placeholders']['TITLE']['options_count'] == 3
    
    def test_analyze_template(self, detector, test_template_path):
        """测试模板分析功能"""
        if not os.path.exists(test_template_path):
            pytest.skip("测试模板文件不存在")
        
        result = detector.analyze_template(test_template_path)
        
        assert 'file' in result
        assert 'format' in result
        assert 'placeholders_count' in result
        assert 'placeholders' in result
        assert 'suggested_schema' in result
        assert 'select_mode_count' in result
        assert 'auto_mode_count' in result
        
        assert result['format'] == 'docx'
        assert result['placeholders_count'] > 0


class TestCommonPrompts:
    """常见占位符提示语测试"""
    
    def test_chinese_placeholders(self):
        """测试中文占位符"""
        detector = PlaceholderDetector()
        
        placeholders = ['标题', '摘要', '关键词']
        schema = detector._generate_schema(placeholders)
        
        for name in placeholders:
            assert name in schema['placeholders']
            assert schema['placeholders'][name]['prompt']
    
    def test_unknown_placeholders(self):
        """测试未知占位符"""
        detector = PlaceholderDetector()
        
        placeholders = ['CUSTOM_FIELD', 'XYZ123']
        schema = detector._generate_schema(placeholders)
        
        # 应该生成默认提示语
        for name in placeholders:
            assert name in schema['placeholders']
            prompt = schema['placeholders'][name]['prompt']
            assert name in prompt or name.lower() in prompt.lower()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
