from markitdown import MarkItDown
import os

class ResumeParser:
    """简历解析器 - 负责从PDF中提取文本"""
    
    def __init__(self):
        """初始化解析器"""
        print("🔧 初始化简历解析器...")
        self.md_converter = MarkItDown()
        print("✅ 简历解析器初始化完成")
    
    def parse_pdf(self, pdf_path: str) -> str:
        """解析PDF简历
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            提取的文本内容
        """
        if not os.path.exists(pdf_path):
            return f"❌ 文件不存在: {pdf_path}"
        
        print(f"📄 正在解析PDF: {pdf_path}")
        
        try:
            # 使用MarkItDown转换PDF
            result = self.md_converter.convert(pdf_path)
            content = result.text_content
            
            if not content or not content.strip():
                return "❌ PDF内容为空或无法解析"
            
            # 简单清理：移除多余空行
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            cleaned_content = '\n'.join(lines)
            
            print(f"✅ PDF解析完成，提取了 {len(cleaned_content)} 个字符")
            return cleaned_content
            
        except Exception as e:
            error_msg = f"❌ PDF解析失败: {str(e)}"
            print(error_msg)
            return error_msg

# 测试代码
if __name__ == "__main__":
    parser = ResumeParser()
    
    # 测试解析（替换成你的简历PDF路径）
    test_pdf = "test_resume.pdf"
    if os.path.exists(test_pdf):
        content = parser.parse_pdf(test_pdf)
        print("\n" + "="*60)
        print("提取的简历内容:")
        print("="*60)
        print(content[:500] + "..." if len(content) > 500 else content)
    else:
        print(f"⚠️ 测试文件不存在: {test_pdf}")

