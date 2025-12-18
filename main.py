from config import DEEPSEEK_API_KEY, MODEL_ID, BASE_URL
from llm import OpenAICompatibleClient
from agent import Agent

def main():
    # 1. 初始化 LLM
    llm = OpenAICompatibleClient(
        api_key=DEEPSEEK_API_KEY,
        model=MODEL_ID,
        base_url=BASE_URL
    )

    # 2. 初始化 Agent
    agent = Agent(llm_client=llm)

    # 3. 定义用户输入
    user_prompt = "你好，请帮我查询一下今天北京的天气，然后根据天气推荐一个合适的旅游景点。"

    # 4. 启动 Agent Loop
    agent.run(user_prompt)

if __name__ == "__main__":
    main()