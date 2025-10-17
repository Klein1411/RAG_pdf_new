# coding: utf-8
"""
Export Tool - Tool xuất PDF ra file markdown
Sử dụng lại code từ src/export_md.py
"""

import sys
from pathlib import Path
from typing import Optional, Dict, Any
import os

project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from agent.pdf_manager import get_pdf_manager
from src.export_md import convert_to_markdown
from src.logging_config import get_logger

logger = get_logger(__name__)


class ExportTool:
    """
    Tool xuất PDF sang markdown format
    """
    
    def __init__(self):
        """Khởi tạo ExportTool"""
        self.name = "export_tool"
        self.description = "Export PDF to markdown file"
        self.pdf_manager = get_pdf_manager()
    
    def export_pdf_to_md(
        self,
        pdf_name: str,
        output_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Xuất PDF ra file markdown sử dụng convert_to_markdown từ src
        
        Args:
            pdf_name: Tên file PDF
            output_dir: Thư mục output (nếu None sẽ dùng './exports')
            
        Returns:
            Dict với keys: 'success', 'message', 'output_path'
        """
        try:
            # Lấy đường dẫn PDF
            pdf_files = self.pdf_manager.list_pdfs()
            
            if pdf_name not in pdf_files:
                return {
                    'success': False,
                    'message': f"PDF '{pdf_name}' không tồn tại trong danh sách",
                    'output_path': None
                }
            
            pdf_path = os.path.join(self.pdf_manager.pdf_dir, pdf_name)
            
            # Setup output directory
            if output_dir is None:
                output_dir = "exports"
            
            os.makedirs(output_dir, exist_ok=True)
            
            # Sử dụng convert_to_markdown từ src
            logger.info(f"Converting {pdf_name} to markdown...")
            markdown_content = convert_to_markdown(pdf_path)
            
            # Create output filename
            base_name = Path(pdf_name).stem
            output_path = os.path.join(output_dir, f"{base_name}.md")
            
            # Write markdown file
            logger.info(f"Writing to {output_path}...")
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            logger.info(f"Export completed: {output_path}")
            
            return {
                'success': True,
                'message': f"✅ Đã xuất sang {output_path}",
                'output_path': output_path
            }
            
        except Exception as e:
            logger.error(f"Error exporting PDF: {e}")
            return {
                'success': False,
                'message': f"Lỗi khi export: {str(e)}",
                'output_path': None
            }
    
    def export_multiple_pdfs(
        self,
        pdf_names: list,
        output_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Xuất nhiều PDF cùng lúc
        
        Args:
            pdf_names: List tên PDF
            output_dir: Thư mục output
            
        Returns:
            Dict với keys: 'total', 'success', 'failed', 'results'
        """
        results = {
            'total': len(pdf_names),
            'success': 0,
            'failed': 0,
            'results': []
        }
        
        for pdf_name in pdf_names:
            result = self.export_pdf_to_md(pdf_name, output_dir)
            
            if result['success']:
                results['success'] += 1
            else:
                results['failed'] += 1
            
            results['results'].append({
                'pdf_name': pdf_name,
                'status': result['success'],
                'message': result['message'],
                'output_path': result['output_path']
            })
        
        return results
    
    def get_export_summary(self, results: Dict) -> str:
        """
        Tạo summary từ kết quả export
        
        Args:
            results: Results từ export_multiple_pdfs
            
        Returns:
            Formatted summary string
        """
        summary = f"📤 **Export Summary:**\n\n"
        summary += f"Total: {results['total']} | "
        summary += f"Success: {results['success']} | "
        summary += f"Failed: {results['failed']}\n\n"
        
        if results['results']:
            summary += "**Details:**\n"
            for r in results['results']:
                status_icon = "✅" if r['status'] else "❌"
                summary += f"{status_icon} {r['pdf_name']}: {r['message']}\n"
        
        return summary


# Singleton instance (optional)
_export_tool_instance = None

def get_export_tool() -> ExportTool:
    """
    Lấy instance của ExportTool (singleton pattern)
    """
    global _export_tool_instance
    if _export_tool_instance is None:
        _export_tool_instance = ExportTool()
        logger.info("ExportTool instance created")
    return _export_tool_instance


# Test function
def test_export_tool():
    """Test ExportTool"""
    tool = ExportTool()
    
    print("\n" + "="*70)
    print("TEST EXPORT TOOL")
    print("="*70)
    
    # List available PDFs
    pdf_manager = get_pdf_manager()
    pdfs = pdf_manager.list_pdfs()
    
    if not pdfs:
        print("\nNo PDFs found. Please add some PDFs first.")
        return
    
    print(f"\nAvailable PDFs: {pdfs}")
    
    # Test export first PDF
    pdf_name = pdfs[0]
    print(f"\nExporting {pdf_name}...")
    
    result = tool.export_pdf_to_md(pdf_name, output_dir="test_exports")
    
    print(f"\n{result['message']}")
    if result['success']:
        print(f"Output: {result['output_path']}")
    
    # Test multiple export
    if len(pdfs) > 1:
        print(f"\n\nTesting multiple export...")
        results = tool.export_multiple_pdfs(pdfs[:2], output_dir="test_exports")
        print(f"\n{tool.get_export_summary(results)}")


if __name__ == "__main__":
    test_export_tool()
