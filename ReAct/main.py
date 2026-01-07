from llm import DeepSeekClient
from tools import ToolExecutor
from ReActAgent import ReActAgent

def main():

    try :
        #1. 初始化DeepSeek客户端和工具执行器
        deepseek_client=DeepSeekClient()
        tool_executor=ToolExecutor()

        #2. 注册Tavily网页搜索工具
        tool_executor.register_tool(
            name="web_search",
            description="使用Tavily进行网页搜索以获取最新信息。",
            func=tool_executor.search_web
        )

        print("\n--- 可用工具列表 ---")
        print(tool_executor.getAvaliableTools())

        #3. 初始化ReAct代理
        react_agent=ReActAgent(
            deepseek_client=deepseek_client,
            tool_executor=tool_executor,
            max_steps=5
        )

        #4. 处理用户问题
        question="请告诉我2025年最新的人工智能发展趋势？"
        print(f"\n用户问题: {question}")
        final_answer=react_agent.run(question)
        if final_answer :
            print(f"\n最终答案: {final_answer}")
        else :
            print("代理未能给出最终答案。")


    except Exception as e :
        print(f"程序运行出错: {e}")

if __name__ == "__main__":
    main()

    