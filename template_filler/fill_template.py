"""
fill_template.py: CLI 入口

命令行工具，用于填充 Word 模板。
"""

import argparse
import yaml
import sys
import os

# 将 template_filler 目录添加到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from template_filler.orchestrator import Orchestrator
from template_filler.llm_client import LLMClient


def main():
    parser = argparse.ArgumentParser(
        description='Template Filler - 使用 LLM 自动填充文档模板',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python fill_template.py --template template.docx --context context.txt --schema schema.yaml --output output.docx
  python fill_template.py -t template.docx -c context.txt -s schema.yaml -o output.docx --preview
        """
    )
    
    parser.add_argument(
        '-t', '--template',
        required=True,
        help='Word 模板文件路径 (.docx)'
    )
    parser.add_argument(
        '-c', '--context',
        required=True,
        help='原始材料文本文件路径'
    )
    parser.add_argument(
        '-s', '--schema',
        required=True,
        help='Schema 配置文件路径 (.yaml)'
    )
    parser.add_argument(
        '-o', '--output',
        default='output.docx',
        help='输出文件路径 (默认: output.docx)'
    )
    parser.add_argument(
        '--preview',
        action='store_true',
        help='仅预览生成结果，不保存文件'
    )
    parser.add_argument(
        '--model',
        default='gpt-4o-mini',
        help='LLM 模型名称 (默认: gpt-4o-mini)'
    )
    parser.add_argument(
        '--api-key',
        help='OpenAI API Key (也可通过 OPENAI_API_KEY 环境变量设置)'
    )
    parser.add_argument(
        '--base-url',
        help='API Base URL (也可通过 OPENAI_BASE_URL 环境变量设置)'
    )
    
    args = parser.parse_args()
    
    # 验证文件存在
    for path, name in [(args.template, 'Template'), (args.context, 'Context'), (args.schema, 'Schema')]:
        if not os.path.exists(path):
            print(f"Error: {name} file not found: {path}")
            sys.exit(1)
    
    try:
        # 创建 LLM 客户端
        llm_client = LLMClient(
            api_key=args.api_key,
            base_url=args.base_url,
            model=args.model
        )
        
        # 创建 Orchestrator
        orchestrator = Orchestrator.from_files(
            template_path=args.template,
            context_path=args.context,
            schema_path=args.schema,
            llm_client=llm_client
        )
        
        if args.preview:
            # 预览模式
            print("=" * 50)
            print("预览模式 - 生成内容预览")
            print("=" * 50)
            
            result = orchestrator.preview()
            
            for placeholder, data in result['placeholders'].items():
                print(f"\n[{placeholder}] (mode: {data['mode']})")
                print("-" * 30)
                for i, content in enumerate(data['content']):
                    if data['mode'] == 'select':
                        print(f"  选项 {i + 1}: {content}")
                    else:
                        print(f"  {content}")
        else:
            # 执行填充
            print(f"正在处理模板: {args.template}")
            print(f"输出文件: {args.output}")
            
            result = orchestrator.run(args.output)
            
            print("\n" + "=" * 50)
            print("填充完成!")
            print("=" * 50)
            print(f"\n输出文件: {result['output_path']}")
            print("\n填充内容:")
            for placeholder, content in result['filled_placeholders'].items():
                print(f"  [{placeholder}]: {content[:50]}..." if len(content) > 50 else f"  [{placeholder}]: {content}")
            
            if result.get('options'):
                print("\n多选项 (select 模式):")
                for placeholder, options in result['options'].items():
                    print(f"  [{placeholder}]:")
                    for i, opt in enumerate(options):
                        print(f"    {i + 1}. {opt[:50]}..." if len(opt) > 50 else f"    {i + 1}. {opt}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
