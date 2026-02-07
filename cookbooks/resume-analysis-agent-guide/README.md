# AI Resume Analyzer + Step 3.5 Flash

A multi-agent resume analysis system powered by **Step 3.5 Flash** and **HelloAgents**, providing professional evaluation and actionable improvement suggestions.

## Features

- **Multi-Agent Architecture:** PDF Parser → Analyzer (with Reflection) → Reviewer → Advisor
- **Self-Reflection Mechanism:** AI validates its own analysis for accuracy
- **5-Dimension Scoring:** Structure, Content, Expression, Format, Skill Matching
- **Actionable Suggestions:** Before/after examples for each improvement
- **Dual Interface:** Web UI (Gradio) + CLI
- **History Tracking:** Auto-save analysis results for version comparison

## Prerequisites

- **Python:** 3.10+
- **API Key:** Step-3.5-Flash ([Get it here](https://platform.stepfun.com/))

## Installation

### Step 1: Setup Environment

```bash
# Create virtual environment (recommended)
conda create -n resume_assistant python=3.10 -y
conda activate resume_assistant

# Install dependencies
pip install -r requirements.txt
```



## Quick Start

### Method 1: Web UI (Recommended)

```bash
python app.py
```

Open `http://127.0.0.1:7860` in your browser:
1. Upload PDF resume
2. Enter API Key
3. Specify target position
4. Click "Start Analysis"

### Method 2: Command Line

```bash
python test_resume.py
```

**Note:** Requires `.env` configuration and a `test.pdf` file in the project directory.

### Method 3: Python API

```python
from resume_assistant import ResumeAssistant

# Initialize assistant
assistant = ResumeAssistant(api_key="your_api_key")

# Analyze resume
report = assistant.analyze_resume(
    pdf_path="your_resume.pdf",
    target_position="Software Engineer"
)

# Print formatted report
assistant.print_report(report)

# Or get raw JSON
import json
print(json.dumps(report, ensure_ascii=False, indent=2))
```

## Project Structure

```
case/
├── app.py                  # Gradio Web UI entry
├── test_resume.py           # CLI test entry
├── resume_assistant.py     # Main controller (orchestrates agents)
├── resume_parser.py        # PDF Parser Agent
├── resume_analyzer.py      # Analyzer Agent (with Reflection)
├── resume_reviewer.py      # Reviewer Agent
├── resume_advisor.py       # Advisor Agent
├── requirements.txt        # Dependencies
└── analysis_history/       # Auto-generated analysis logs
```

## Scoring Dimensions

| Dimension | Weight | Evaluation Criteria |
| :--- | :--- | :--- |
| **Structure** | 20 pts | Personal info, education, experience, projects, skills |
| **Content** | 30 pts | Quantified data, personal contribution, concrete results |
| **Expression** | 20 pts | Concise language, accurate terminology, no grammar errors |
| **Format** | 15 pts | Clean layout, consistent fonts, no formatting issues |
| **Skill Match** | 15 pts | Alignment with target position, modern tech stack |

## Output Example

<details>
<summary>📊 View Sample Analysis Report</summary>

```
📊 简历分析报告
==================
总体评分: 78/100
✅ 审核状态: 通过

各维度得分:
  结构完整性: 18/20 ████████████████████
  内容质量:   22/30 ███████████░░░░░░░░░
  表达专业性: 16/20 ████████████████░░░░
  格式规范性: 12/15 ████████████░░░░
  技能匹配度: 10/15 ██████████░░░░░

💡 改进建议
==================
[1] 内容量化 - 缺少具体数据支撑
    修改前: 负责用户系统开发
    修改后: 主导用户系统重构,支撑日均100万请求,响应时间优化50%

[2] 技术栈描述 - 缺少深度说明
    修改前: 熟悉Python、Django
    修改后: 精通Python(3年),深度使用Django REST Framework构建高并发API(QPS 5000+)
```
</details>
