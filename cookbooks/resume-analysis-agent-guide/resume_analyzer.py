from hello_agents.core.llm import HelloAgentsLLM
from hello_agents.agents import ReflectionAgent
import json

class ResumeAnalyzer:
    """简历分析器 - 负责分析简历质量（带反思机制）"""
    
    def __init__(self, api_key: str):
        """初始化分析器
        
        Args:
            api_key: Step-3.5-Flash API密钥
        """
        print("🔧 初始化简历分析器...")
        
        self.llm = HelloAgentsLLM(
            model="step-3.5-flash",
            base_url="https://api.stepfun.com/v1",
            api_key=api_key
        )
        
        # 使用ReflectionAgent实现自我反思
        self.agent = ReflectionAgent(
            name="简历分析专家",
            llm=self.llm,
            max_iterations=2,  # 最多反思2次
            custom_prompts={
                "initial": self._get_initial_prompt(),
                "reflect": self._get_reflect_prompt(),
                "refine": self._get_refine_prompt()
            }
        )
        
        # 创建审核器
        from resume_reviewer import ResumeReviewer
        self.reviewer = ResumeReviewer(api_key=api_key)
        
        print("✅ 简历分析器初始化完成")
    
    def _get_initial_prompt(self) -> str:
        """获取初始分析提示词"""
        return """你是一位资深HR和技术面试官，负责评估简历质量。

请从以下5个维度评估简历，每个维度给出具体分数和理由：

结构完整性（20分）：是否包含个人信息、教育背景、工作经历、项目经验、技能等核心模块。缺少任何核心模块都会扣分。

内容质量（30分）：工作经历和项目描述是否具体，是否有量化数据（如"优化性能50%"、"支撑日均100万请求"），是否体现个人贡献。空洞的描述（如"负责开发"、"参与项目"）会严重扣分。

表达专业性（20分）：语言是否专业简洁，技术术语使用是否准确，是否有明显的语法错误或口语化表达。

格式规范性（15分）：排版是否整洁，字体字号是否统一，是否有明显的格式问题（如断行、乱码）。

技能匹配度（15分）：技能描述是否与目标岗位匹配，技术栈是否过时，是否有相关的项目经验支撑。

【重要】必须严格按照以下JSON格式返回，不得使用中文字段名，不得改变结构：
{{
    "scores": {{
        "结构完整性": 18,
        "内容质量": 22,
        "表达专业性": 16,
        "格式规范性": 12,
        "技能匹配度": 10
    }},
    "total_score": 78,
    "strengths": ["优点1", "优点2", "优点3"],
    "weaknesses": ["不足1", "不足2", "不足3"],
    "summary": "总体评价"
}}

注意：
1. 必须包含 total_score 字段（不是 总分 或 overall_score）
2. 必须包含 scores 字典（不是 各模块得分）
3. 必须包含 strengths 数组（不是 优点）
4. 必须包含 weaknesses 数组（不是 缺点）
5. total_score 必须等于各维度得分之和
6. 只返回JSON，不要添加其他说明文字
"""
    
    def _get_reflect_prompt(self) -> str:
        """获取反思提示词"""
        return """请反思你刚才的分析是否合理：

评分是否过于宽松或严格？比如一份缺少量化数据的简历，内容质量不应超过20分。

优缺点是否具体？避免"内容丰富"、"表达清晰"这种空洞的评价。

是否遗漏重要问题？比如工作经历时间线是否连贯，项目描述是否与岗位匹配。

请指出分析中的问题，并说明需要如何改进。
"""
    
    def _get_refine_prompt(self) -> str:
        """获取改进提示词"""
        return """根据反思结果，请重新给出更准确的分析。

注意：
- 评分标准要严格，缺少量化数据的简历内容质量不应超过20分
- 优缺点要具体，指出具体哪里好、哪里不好
- 不要遗漏重要问题

请以相同的JSON格式返回改进后的分析结果。
"""
    
    def analyze(self, resume_content: str, target_position: str = "软件工程师") -> dict:
        """分析简历（带反思机制）
        
        Args:
            resume_content: 简历文本内容
            target_position: 目标岗位
            
        Returns:
            分析结果（字典）
        """
        print(f"🔍 正在分析简历（目标岗位：{target_position}）...")
        
        prompt = f"""请分析以下简历，目标岗位是：{target_position}

# 简历内容：
{resume_content}

请按照系统提示词中的要求，给出详细的分析结果。
"""
        
        response = self.agent.run(prompt)
        
        try:
            # 提取JSON部分
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response.strip()
            
            result = json.loads(json_str)
            print("✅ 分析完成")
            return result
        
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON解析失败: {e}")
            return {
                "scores": {},
                "total_score": 0,
                "strengths": [],
                "weaknesses": [],
                "summary": "分析失败",
                "raw_response": response
            }
    
    def analyze_with_review(self, resume_content: str, target_position: str = "软件工程师") -> dict:
        """分析简历并进行审核
        
        Args:
            resume_content: 简历文本内容
            target_position: 目标岗位
            
        Returns:
            包含分析和审核结果的字典
        """
        # 第一步：分析简历（带反思）
        analysis = self.analyze(resume_content, target_position)
        
        # 第二步：审核分析结果
        review = self.reviewer.review(resume_content, analysis)
        
        # 如果审核不通过，记录问题
        if not review.get('pass', True):
            analysis['review_issues'] = review.get('issues', [])
            analysis['review_suggestions'] = review.get('suggestions', [])
            print("\n⚠️ 审核发现以下问题：")
            for issue in review.get('issues', []):
                print(f"   - {issue}")
        
        analysis['review_score'] = review.get('review_score', 0)
        analysis['review_passed'] = review.get('pass', True)
        
        return analysis

