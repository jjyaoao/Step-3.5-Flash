from resume_assistant import ResumeAssistant

# 初始化（使用你的API密钥）
API_KEY = "替换成你的真实密钥"
assistant = ResumeAssistant(api_key=API_KEY)

# 分析简历
report = assistant.analyze_resume("test.pdf", "Python开发工程师")

# 打印报告
assistant.print_report(report)