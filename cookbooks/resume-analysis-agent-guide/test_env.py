from hello_agents import HelloAgentsLLM

# 连接Step-3.5-Flash模型
llm = HelloAgentsLLM(
    model="step-3.5-flash",
    base_url="https://api.stepfun.com/v1",
    api_key="替换成你的真实密钥"  # 替换成你的真实密钥
)

# 测试连接
messages = [{"role": "user", "content": "你好，请介绍一下你自己。"}]

response_text = ""
for chunk in llm.think(messages):
    response_text += chunk

print("✅ 环境配置成功！")