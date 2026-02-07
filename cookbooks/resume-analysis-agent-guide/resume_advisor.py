from hello_agents.core.llm import HelloAgentsLLM
from hello_agents.agents import SimpleAgent
import json

class ResumeAdvisor:
    """简历建议生成器 - 负责生成改进建议"""
    
    def __init__(self, api_key: str):
        """初始化建议生成器
        
        Args:
            api_key: Step-3.5-Flash API密钥
        """
        print("🔧 初始化建议生成器...")
        
        self.llm = HelloAgentsLLM(
            model="step-3.5-flash",
            base_url="https://api.stepfun.com/v1",
            api_key=api_key
        )
        
        self.agent = SimpleAgent(
            name="简历优化顾问",
            system_prompt=self._get_system_prompt(),
            llm=self.llm
        )
        
        print("✅ 建议生成器初始化完成")
    
    def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        return """你是一位资深的简历优化顾问，擅长将简历问题转化为具体的改进建议。

你的任务是根据简历分析结果，针对每个不足点给出具体的改进建议。建议要可落地，最好包含"修改前"和"修改后"的对比示例。优先解决影响最大的问题，比如缺少量化数据、描述不具体、技术栈过时等。

建议格式要求：每条建议包含问题描述、改进方向、具体示例。示例要真实可信，符合简历场景。语言简洁专业，避免空洞的建议。

请以JSON格式返回建议列表：
{
    "suggestions": [
        {
            "category": "内容质量",
            "problem": "工作经历缺少量化数据",
            "solution": "在描述中加入具体的数据和成果",
            "example_before": "负责后端服务开发，参与多个项目",
            "example_after": "主导3个核心后端服务开发，优化接口响应时间50%，支撑日均100万次请求"
        }
    ],
    "priority_order": ["内容质量", "表达专业性", "结构完整性"]
}
"""
    
    def generate_suggestions(self, resume_content: str, analysis_result: dict) -> dict:
        """生成改进建议
        
        Args:
            resume_content: 简历文本内容
            analysis_result: 分析结果
            
        Returns:
            建议列表（字典）
        """
        print("💡 正在生成改进建议...")
        
        prompt = f"""请根据以下简历和分析结果，生成具体的改进建议。

# 简历内容：
{resume_content}

# 分析结果：
总分：{analysis_result.get('total_score', 0)}/100
各维度得分：{json.dumps(analysis_result.get('scores', {}), ensure_ascii=False)}
不足之处：{json.dumps(analysis_result.get('weaknesses', []), ensure_ascii=False)}

请针对不足之处，生成3-5条具体的改进建议，按照系统提示词中的格式返回JSON。
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
            print("✅ 建议生成完成")
            return result
        
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON解析失败: {e}")
            return {
                "suggestions": [],
                "priority_order": [],
                "raw_response": response
            }

