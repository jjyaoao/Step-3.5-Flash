from hello_agents.core.llm import HelloAgentsLLM
from hello_agents.agents import SimpleAgent
import json

class ResumeReviewer:
    """简历分析审核器 - 负责审核分析结果的质量"""
    
    def __init__(self, api_key: str):
        """初始化审核器
        
        Args:
            api_key: Step-3.5-Flash API密钥
        """
        print("🔧 初始化分析审核器...")
        
        self.llm = HelloAgentsLLM(
            model="step-3.5-flash",
            base_url="https://api.stepfun.com/v1",
            api_key=api_key
        )
        
        self.agent = SimpleAgent(
            name="简历分析审核专家",
            system_prompt=self._get_system_prompt(),
            llm=self.llm
        )
        
        print("✅ 分析审核器初始化完成")
    
    def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        return """你是一位资深的简历分析质检专家，负责审核其他AI给出的简历分析结果。

你的任务是检查分析结果是否合理，重点关注：

评分合理性：各维度得分是否符合简历实际情况。比如一份缺少量化数据的简历，内容质量不应超过20分；一份排版混乱的简历，格式规范性不应超过10分。

具体性：优点和不足是否具体。避免"内容丰富"、"表达清晰"这种空洞的评价，要指出具体哪里好、哪里不好。

完整性：是否遗漏重要问题。比如工作经历时间线是否连贯，项目描述是否与岗位匹配，技术栈是否过时。

请以JSON格式返回审核结果：
{
    "pass": true/false,
    "review_score": 85,
    "issues": ["评分过于宽松", "缺少对时间线的检查"],
    "suggestions": ["建议将内容质量分降至18分", "补充时间线连贯性分析"],
    "comment": "整体分析较好，但评分标准需要更严格。"
}
"""
    
    def review(self, resume_content: str, analysis_result: dict) -> dict:
        """审核分析结果
        
        Args:
            resume_content: 简历文本内容
            analysis_result: 分析结果
            
        Returns:
            审核结果（字典）
        """
        print("🔍 正在审核分析结果...")
        
        prompt = f"""请审核以下简历分析结果的质量。

# 简历内容：
{resume_content[:1000]}...

# 分析结果：
总分：{analysis_result.get('total_score', 0)}/100
各维度得分：{json.dumps(analysis_result.get('scores', {}), ensure_ascii=False)}
优点：{json.dumps(analysis_result.get('strengths', []), ensure_ascii=False)}
不足：{json.dumps(analysis_result.get('weaknesses', []), ensure_ascii=False)}
总结：{analysis_result.get('summary', '')}

请按照要求返回JSON格式的审核结果。
"""
        
        response = self.agent.run(prompt)
        
        try:
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response.strip()
            
            result = json.loads(json_str)
            
            if result.get('pass', False):
                print("✅ 分析结果通过审核")
            else:
                print("⚠️ 分析结果需要改进")
                print(f"   发现问题：{', '.join(result.get('issues', []))}")
            
            return result
        
        except json.JSONDecodeError as e:
            print(f"⚠️ 审核结果解析失败: {e}")
            return {
                "pass": True,
                "review_score": 0,
                "issues": [],
                "suggestions": [],
                "comment": "审核失败",
                "raw_response": response
            }

