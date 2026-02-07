import gradio as gr
from resume_assistant import ResumeAssistant
import os
import json
from datetime import datetime
import sys
from io import StringIO

def analyze_resume_ui(pdf_file, api_key, target_position):
    """UI分析函数"""
    if not pdf_file:
        return "❌ 请上传PDF文件", "", ""

    if not api_key or len(api_key.strip()) < 10:
        return "❌ 请输入有效的API Key", "", ""

    if not target_position or len(target_position.strip()) == 0:
        return "❌ 请输入目标岗位", "", ""

    old_stdout = sys.stdout
    try:
        # 捕获控制台输出
        sys.stdout = StringIO()

        assistant = ResumeAssistant(api_key=api_key.strip())

        # 获取上传文件的路径
        pdf_path = pdf_file.name if hasattr(pdf_file, 'name') else str(pdf_file)

        # 分析简历
        report = assistant.analyze_resume(pdf_path, target_position.strip())

        # 恢复控制台输出
        sys.stdout = old_stdout

        if "error" in report:
            return f"❌ 分析失败: {report['error']}", "", ""

        # 格式化输出
        analysis_text = format_analysis(report)
        suggestions_text = format_suggestions(report)
        json_text = json.dumps(report, ensure_ascii=False, indent=2)

        return analysis_text, suggestions_text, json_text

    except Exception as e:
        sys.stdout = old_stdout
        import traceback
        return f"❌ 发生错误: {str(e)}\n\n{traceback.format_exc()}", "", ""

def format_analysis(report):
    """格式化分析结果"""
    analysis = report['analysis']
    meta = report['metadata']



    # 处理 analysis 为字符串的情况
    if isinstance(analysis, str):
        return f"""# 📊 简历分析报告

## 基本信息
- 📄 **简历文件**: {os.path.basename(meta['pdf_path'])}
- 🎯 **目标岗位**: {meta['target_position']}
- ⏰ **分析时间**: {meta['analysis_time']}

## ❌ 分析失败

{analysis}

请检查简历格式或重试。
"""

    # 兼容多种总分字段（中英文）
    total_score = (analysis.get('total_score') or
                   analysis.get('overall_score') or
                   analysis.get('总分') or
                   analysis.get('简历总分', 0))

    output = f"""# 📊 简历分析报告

## 基本信息
- 📄 **简历文件**: {os.path.basename(meta['pdf_path'])}
- 🎯 **目标岗位**: {meta['target_position']}
- ⏰ **分析时间**: {meta['analysis_time']}

## 总体评分
### 📈 总分: {total_score}/100

"""

    # 审核状态
    if analysis.get('review_passed'):
        output += f"✅ **审核状态**: 通过 (审核分: {analysis.get('review_score', 0)})\n\n"
    else:
        output += f"⚠️ **审核状态**: 需改进 (审核分: {analysis.get('review_score', 0)})\n\n"

    # 各维度得分 - 兼容多种数据结构
    output += "## 各维度得分\n\n"

    # 结构1: 简单的 scores 字典
    if 'scores' in analysis:
        for dim, score in analysis['scores'].items():
            bar = "█" * (score // 5) + "░" * (20 - score // 5)
            output += f"**{dim}**: {score}分 `{bar}`\n\n"

    # 结构2: breakdown 嵌套对象
    elif 'breakdown' in analysis:
        for dim, data in analysis['breakdown'].items():
            score = data.get('score', 0)
            max_score = data.get('max_score', 100)
            percentage = int(score * 100 / max_score) if max_score > 0 else 0
            bar = "█" * (percentage // 5) + "░" * (20 - percentage // 5)
            output += f"**{dim}**: {score}/{max_score}分 `{bar}`\n"
            if 'reason' in data:
                output += f"> {data['reason'][:200]}...\n\n"

    # 结构3: analysis 嵌套对象（新格式）
    elif 'analysis' in analysis and isinstance(analysis['analysis'], dict):
        for dim, data in analysis['analysis'].items():
            if isinstance(data, dict) and 'score' in data:
                score = data.get('score', 0)
                # 翻译维度名称
                dim_name_map = {
                    'format_structure': '结构完整性',
                    'content_quantification': '内容质量',
                    'skill_relevance': '技能匹配度',
                    'experience_narrative': '表达专业性',
                    'position_match': '岗位匹配度'
                }
                dim_display = dim_name_map.get(dim, dim)
                bar = "█" * (score // 5) + "░" * (20 - score // 5)
                output += f"**{dim_display}**: {score}分 `{bar}`\n\n"

    # 结构4: 中文字段 各模块得分
    elif '各模块得分' in analysis:
        scores_data = analysis['各模块得分']
        if isinstance(scores_data, dict):
            for dim, score in scores_data.items():
                if isinstance(score, (int, float)):
                    bar = "█" * (int(score) // 5) + "░" * (20 - int(score) // 5)
                    output += f"**{dim}**: {score}分 `{bar}`\n\n"
    
    # 优点 - 兼容多种数据结构
    output += "\n## 💪 优点\n\n"
    strengths = []

    # 从嵌套的 analysis.analysis 中提取
    if 'analysis' in analysis and isinstance(analysis['analysis'], dict):
        for dim, data in analysis['analysis'].items():
            if isinstance(data, dict) and 'strengths' in data:
                strengths.extend(data['strengths'])

    # 从顶层 strengths 提取
    if not strengths and 'strengths' in analysis:
        strengths = analysis.get('strengths', [])

    # 从中文字段 优点 提取
    if not strengths and '优点' in analysis:
        strengths = analysis.get('优点', [])

    if strengths:
        for strength in strengths:
            if isinstance(strength, dict):
                output += f"- **{strength.get('aspect', '未知')}**: {strength.get('detail', '')}\n"
            else:
                output += f"- {strength}\n"
    else:
        output += "（无）\n"

    # 不足 - 兼容多种数据结构
    output += "\n## ⚠️ 不足\n\n"
    weaknesses = []

    # 从嵌套的 analysis.analysis 中提取
    if 'analysis' in analysis and isinstance(analysis['analysis'], dict):
        for dim, data in analysis['analysis'].items():
            if isinstance(data, dict) and 'weaknesses' in data:
                weaknesses.extend(data['weaknesses'])

    # 从顶层 weaknesses 提取
    if not weaknesses and 'weaknesses' in analysis:
        weaknesses = analysis.get('weaknesses', [])

    # 从中文字段 缺点 提取
    if not weaknesses and '缺点' in analysis:
        weaknesses = analysis.get('缺点', [])

    if weaknesses:
        for weakness in weaknesses:
            if isinstance(weakness, dict):
                output += f"- **{weakness.get('aspect', '未知')}**: {weakness.get('detail', '')}\n"
            else:
                output += f"- {weakness}\n"
    else:
        output += "（无）\n"
    
    # 关键问题
    if 'critical_issues' in analysis:
        output += "\n## 🚨 关键问题\n\n"
        for issue in analysis['critical_issues']:
            output += f"- {issue}\n"
    
    return output

def format_suggestions(report):
    """格式化改进建议"""
    suggestions = report.get('suggestions', {})
    
    output = "# 💡 改进建议\n\n"
    
    if suggestions.get('suggestions'):
        for i, sug in enumerate(suggestions['suggestions'], 1):
            output += f"## {i}. {sug.get('category', '未分类')}\n\n"
            output += f"**问题**: {sug.get('problem', '')}\n\n"
            output += f"**解决方案**: {sug.get('solution', '')}\n\n"
            
            if 'example_before' in sug and 'example_after' in sug:
                output += f"**修改前**:\n```\n{sug['example_before']}\n```\n\n"
                output += f"**修改后**:\n```\n{sug['example_after']}\n```\n\n"
            
            output += "---\n\n"
    else:
        output += "暂无改进建议\n"
    
    return output

# 创建Gradio界面
with gr.Blocks(theme=gr.themes.Soft(), title="AI简历分析助手") as demo:
    gr.Markdown("""
    # 🎯 AI简历分析助手
    
    基于 **Step-3.5-Flash** 大模型的智能简历分析系统，提供专业的简历评估和改进建议。
    
    ### 功能特点
    - 📊 多维度评分（结构、内容、表达、格式、匹配度）
    - 🤖 AI自我反思机制，确保分析质量
    - 💡 具体可执行的改进建议
    - 📝 完整的分析报告导出
    """)
    
    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("## 📤 上传信息")
            pdf_input = gr.File(
                label="上传简历PDF",
                file_types=[".pdf"]
            )
            api_key_input = gr.Textbox(
                label="Step-3.5-Flash API Key",
                placeholder="请输入您的API密钥",
                type="password",
                lines=1
            )
            position_input = gr.Textbox(
                label="目标岗位",
                placeholder="例如：Python开发工程师、产品经理",
                value="软件工程师",
                lines=1
            )
            
            analyze_btn = gr.Button("🚀 开始分析", variant="primary", size="lg")
            
            gr.Markdown("""
            ---
            ### 💡 使用提示
            1. 上传PDF格式的简历文件
            2. 输入您的API密钥
            3. 填写目标求职岗位
            4. 点击"开始分析"按钮
            """)
        
        with gr.Column(scale=2):
            gr.Markdown("## 📊 分析结果")
            
            with gr.Tabs():
                with gr.Tab("📈 分析报告"):
                    analysis_output = gr.Markdown(label="分析结果")
                
                with gr.Tab("💡 改进建议"):
                    suggestions_output = gr.Markdown(label="改进建议")
                
                with gr.Tab("📄 完整JSON"):
                    json_output = gr.Code(label="完整报告（JSON格式）", language="json")
    
    # 绑定事件
    analyze_btn.click(
        fn=analyze_resume_ui,
        inputs=[pdf_input, api_key_input, position_input],
        outputs=[analysis_output, suggestions_output, json_output]
    )
    
    gr.Markdown("""
    ---
    <div style="text-align: center; color: #666;">
        <p>Powered by <strong>Step-3.5-Flash</strong> | 多Agent协作系统</p>
    </div>
    """)

if __name__ == "__main__":
    demo.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=True,
        show_error=True
    )

