"""
Script để chạy tất cả tests và generate coverage report.
Sử dụng: python run_tests.py
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd: list, description: str) -> bool:
    """
    Chạy command và in kết quả.
    
    Args:
        cmd: Command dưới dạng list
        description: Mô tả command
        
    Returns:
        True nếu thành công, False nếu thất bại
    """
    print(f"\n{'='*70}")
    print(f"🚀 {description}")
    print(f"{'='*70}\n")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print(f"\n✅ {description} - THÀNH CÔNG\n")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ {description} - THẤT BẠI\n")
        return False
    except FileNotFoundError:
        print(f"\n⚠️ Không tìm thấy pytest. Vui lòng cài đặt: pip install pytest pytest-cov\n")
        return False

def main():
    """Main function để chạy tất cả tests"""
    
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║           RAG PROJECT - TEST RUNNER                        ║
    ║           Chạy tất cả unit tests và generate report       ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    # Kiểm tra xem pytest đã được cài đặt chưa
    try:
        import pytest
        import pytest_cov
    except ImportError:
        print("⚠️ Chưa cài đặt pytest hoặc pytest-cov")
        print("Đang cài đặt...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pytest", "pytest-cov", "pytest-mock"])
    
    results = []
    
    # 1. Chạy tests với verbose output
    results.append(run_command(
        [sys.executable, "-m", "pytest", "test_gemini_client.py", "-v"],
        "Chạy Unit Tests với Verbose Output"
    ))
    
    # 2. Chạy tests với coverage
    results.append(run_command(
        [sys.executable, "-m", "pytest", "test_gemini_client.py", 
         "--cov=gemini_client", "--cov-report=term-missing", "--cov-report=html"],
        "Chạy Tests với Coverage Report"
    ))
    
    # 3. In tóm tắt
    print(f"\n{'='*70}")
    print("📊 TÓM TẮT KẾT QUẢ")
    print(f"{'='*70}\n")
    
    total = len(results)
    passed = sum(results)
    
    print(f"Tổng số bước: {total}")
    print(f"Thành công: {passed}")
    print(f"Thất bại: {total - passed}")
    
    if all(results):
        print("\n🎉 TẤT CẢ TESTS ĐỀU PASS! 🎉\n")
        
        # Kiểm tra xem coverage report đã được tạo chưa
        coverage_index = Path("htmlcov/index.html")
        if coverage_index.exists():
            print("📈 Coverage report đã được tạo tại: htmlcov/index.html")
            print("   Mở file này trong browser để xem chi tiết coverage.\n")
    else:
        print("\n⚠️ MỘT SỐ TESTS THẤT BẠI. Vui lòng kiểm tra lại.\n")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
