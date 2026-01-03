"""
API 集成测试

测试 FastAPI 后端 API 端点。
"""

import os
import sys
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from template_filler.server import app


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


@pytest.fixture
def test_template_path():
    """测试模板路径"""
    return os.path.join(
        os.path.dirname(__file__), 
        'test_template.docx'
    )


class TestUploadAPI:
    """上传 API 测试"""
    
    def test_upload_template_success(self, client, test_template_path):
        """测试成功上传模板"""
        if not os.path.exists(test_template_path):
            pytest.skip("测试模板文件不存在")
        
        with open(test_template_path, 'rb') as f:
            response = client.post(
                '/api/upload-template',
                files={'file': ('test.docx', f, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert 'session_id' in data
        assert 'filename' in data
    
    def test_upload_invalid_format(self, client):
        """测试上传无效格式"""
        response = client.post(
            '/api/upload-template',
            files={'file': ('test.txt', b'hello', 'text/plain')}
        )
        
        assert response.status_code == 400


class TestParseTemplateAPI:
    """模板解析 API 测试"""
    
    def test_parse_template(self, client, test_template_path):
        """测试模板解析"""
        if not os.path.exists(test_template_path):
            pytest.skip("测试模板文件不存在")
        
        # 先上传
        with open(test_template_path, 'rb') as f:
            upload_response = client.post(
                '/api/upload-template',
                files={'file': ('test.docx', f, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}
            )
        
        session_id = upload_response.json()['session_id']
        
        # 解析模板
        response = client.get(f'/api/parse-template/{session_id}')
        
        assert response.status_code == 200
        data = response.json()
        assert 'html' in data
        assert 'placeholders' in data
        assert 'suggested_schema' in data
    
    def test_parse_invalid_session(self, client):
        """测试无效会话"""
        response = client.get('/api/parse-template/invalid-session-id')
        assert response.status_code == 404


class TestContextAPI:
    """上下文设置 API 测试"""
    
    def test_set_context(self, client, test_template_path):
        """测试设置上下文"""
        if not os.path.exists(test_template_path):
            pytest.skip("测试模板文件不存在")
        
        # 先上传
        with open(test_template_path, 'rb') as f:
            upload_response = client.post(
                '/api/upload-template',
                files={'file': ('test.docx', f, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}
            )
        
        session_id = upload_response.json()['session_id']
        
        # 设置上下文
        response = client.post(
            f'/api/set-context/{session_id}',
            data={'context': '这是测试上下文内容'}
        )
        
        assert response.status_code == 200
        assert response.json()['success'] is True


class TestSchemaAPI:
    """Schema 设置 API 测试"""
    
    def test_set_schema(self, client, test_template_path):
        """测试设置 Schema"""
        if not os.path.exists(test_template_path):
            pytest.skip("测试模板文件不存在")
        
        # 先上传
        with open(test_template_path, 'rb') as f:
            upload_response = client.post(
                '/api/upload-template',
                files={'file': ('test.docx', f, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}
            )
        
        session_id = upload_response.json()['session_id']
        
        # 设置 Schema
        schema = {
            'placeholders': {
                'TITLE': {
                    'prompt': '生成标题',
                    'mode': 'auto'
                }
            }
        }
        
        response = client.post(
            f'/api/set-schema/{session_id}',
            json=schema
        )
        
        assert response.status_code == 200
        assert response.json()['success'] is True


class TestPreviewFilledAPI:
    """填充预览 API 测试"""
    
    def test_preview_filled(self, client, test_template_path):
        """测试填充预览"""
        if not os.path.exists(test_template_path):
            pytest.skip("测试模板文件不存在")
        
        # 上传并解析
        with open(test_template_path, 'rb') as f:
            upload_response = client.post(
                '/api/upload-template',
                files={'file': ('test.docx', f, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}
            )
        
        session_id = upload_response.json()['session_id']
        
        # 解析模板（初始化 template_html）
        client.get(f'/api/parse-template/{session_id}')
        
        # 预览填充
        response = client.post(
            '/api/preview-filled',
            json={
                'session_id': session_id,
                'content_map': {
                    'TITLE': '测试标题',
                    'SUMMARY': '测试摘要'
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert 'html' in data
        assert '测试标题' in data['html']


class TestSessionAPI:
    """会话管理 API 测试"""
    
    def test_delete_session(self, client, test_template_path):
        """测试删除会话"""
        if not os.path.exists(test_template_path):
            pytest.skip("测试模板文件不存在")
        
        # 先上传
        with open(test_template_path, 'rb') as f:
            upload_response = client.post(
                '/api/upload-template',
                files={'file': ('test.docx', f, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}
            )
        
        session_id = upload_response.json()['session_id']
        
        # 删除会话
        response = client.delete(f'/api/session/{session_id}')
        
        assert response.status_code == 200
        assert response.json()['success'] is True
        
        # 验证已删除
        response = client.get(f'/api/parse-template/{session_id}')
        assert response.status_code == 404


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
