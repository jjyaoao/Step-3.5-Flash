from resume_parser import ResumeParser
from resume_analyzer import ResumeAnalyzer
from resume_advisor import ResumeAdvisor
import json
import os
from datetime import datetime

class ResumeAssistant:
    """简历分析助手 - 多Agent协作系统"""
    
    def __init__(self, api_key: str):
        """初始化助手
        
        Args:
            api_key: Step-3.5-Flash API密钥
        """
        print("\n" + "="*60)
        print("🚀 初始化AI简历分析助手")
        print("="*60)
        
        # 初始化四个Agent
        self.parser = ResumeParser()
        self.analyzer = ResumeAnalyzer(api_key)
        self.advisor = ResumeAdvisor(api_key)
        
        # 创建历史记录目录
        self.history_dir = "./analysis_history"
        os.makedirs(self.history_dir, exist_ok=True)
        
        print("\n✅ 所有Agent初始化完成")
        print("="*60)
    
    def analyze_resume(self, pdf_path: str, target_position: str = "软件工程师") -> dict:
        """完整的简历分析流程
        
        Args:
            pdf_path: 简历PDF路径
            target_position: 目标岗位
            
        Returns:
            完整的分析报告
        """
        print(f"\n📋 开始分析简历: {os.path.basename(pdf_path)}")
        print(f"🎯 目标岗位: {target_position}")
        print("="*60)
        
        # 步骤1: 解析PDF
        print("\n[1/4] PDF解析Agent工作中...")
        resume_content = self.parser.parse_pdf(pdf_path)
        
        if resume_content.startswith("❌"):
            return {"error": resume_content}
        
        # 步骤2: 分析简历（带反思和审核）
        print("\n[2/4] 分析Agent工作中（启用自我反思机制）...")
        analysis = self.analyzer.analyze_with_review(resume_content, target_position)
        
        # 步骤3: 生成建议
        print("\n[3/4] 建议Agent工作中...")
        suggestions = self.advisor.generate_suggestions(resume_content, analysis)
        
        # 步骤4: 整合报告
        print("\n[4/4] 生成完整报告...")
        report = {
            "metadata": {
                "pdf_path": pdf_path,
                "target_position": target_position,
                "analysis_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            },
            "resume_content": resume_content[:500] + "..." if len(resume_content) > 500 else resume_content,
            "analysis": analysis,
            "suggestions": suggestions
        }
        
        # 保存历史记录
        self._save_history(report)
        
        print("\n✅ 分析完成！")
        print("="*60)
        
        return report
    
    def _save_history(self, report: dict):
        """保存分析历史"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"analysis_{timestamp}.json"
        filepath = os.path.join(self.history_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"💾 分析历史已保存: {filepath}")
    
    def print_report(self, report: dict):
        """打印分析报告（格式化输出）"""
        if "error" in report:
            print(f"\n❌ 错误: {report['error']}")
            return
        
        print("\n" + "="*60)
        print("📊 简历分析报告")
        print("="*60)
        
        # 基本信息
        meta = report['metadata']
        print(f"\n📄 简历文件: {os.path.basename(meta['pdf_path'])}")
        print(f"🎯 目标岗位: {meta['target_position']}")
        print(f"⏰ 分析时间: {meta['analysis_time']}")
        
        # 分析结果
        analysis = report['analysis']

        # 兼容多种总分字段名
        total_score = analysis.get('total_score') or analysis.get('简历总分', 0)
        print(f"\n📈 总体评分: {total_score}/100")

        if analysis.get('review_passed'):
            print(f"✅ 审核状态: 通过 (审核分: {analysis.get('review_score', 0)})")
        else:
            print(f"⚠️ 审核状态: 需改进")
        
        print("\n各维度得分:")
        # 兼容两种数据结构：scores（简单字典）和 breakdown（嵌套对象）
        if 'scores' in analysis:
            for dim, score in analysis['scores'].items():
                bar = "█" * (score // 2) + "░" * (10 - score // 2)
                print(f"  {dim}: {score:2d}分 {bar}")
        elif 'breakdown' in analysis:
            for dim, data in analysis['breakdown'].items():
                score = data.get('score', 0)
                max_score = data.get('max_score', 100)
                bar = "█" * (score * 10 // max_score) + "░" * (10 - score * 10 // max_score)
                print(f"  {dim}: {score}/{max_score}分 {bar}")
                if 'reason' in data:
                    print(f"    理由: {data['reason'][:100]}...")

        print(f"\n💪 优点:")
        strengths = analysis.get('strengths', [])
        if strengths:
            for strength in strengths:
                if isinstance(strength, dict):
                    print(f"  • {strength.get('aspect', '未知')}: {strength.get('detail', '')}")
                else:
                    print(f"  • {strength}")
        else:
            print("  （无）")

        print(f"\n⚠️ 不足:")
        weaknesses = analysis.get('weaknesses', [])
        if weaknesses:
            for weakness in weaknesses:
                if isinstance(weakness, dict):
                    print(f"  • {weakness.get('aspect', '未知')}: {weakness.get('detail', '')}")
                else:
                    print(f"  • {weakness}")
        else:
            print("  （无）")

        # 显示关键问题
        if 'critical_issues' in analysis:
            print(f"\n🚨 关键问题:")
            for issue in analysis['critical_issues']:
                print(f"  • {issue}")

        # 显示改进建议（来自分析结果）
        if 'improvement_suggestions' in analysis:
            print(f"\n💡 快速改进建议:")
            for i, sug in enumerate(analysis['improvement_suggestions'][:3], 1):
                print(f"  {i}. {sug}")
        
        print(f"\n📝 总结: {analysis.get('summary', '')}")
        
        # 改进建议
        suggestions = report['suggestions']
        if suggestions.get('suggestions'):
            print(f"\n💡 改进建议 (按优先级排序):")
            for i, sug in enumerate(suggestions['suggestions'], 1):
                print(f"\n  [{i}] {sug.get('category', '未分类')} - {sug.get('problem', '')}")
                print(f"      改进方向: {sug.get('solution', '')}")
                if 'example_before' in sug and 'example_after' in sug:
                    print(f"      修改前: {sug['example_before']}")
                    print(f"      修改后: {sug['example_after']}")
        
        print("\n" + "="*60)

