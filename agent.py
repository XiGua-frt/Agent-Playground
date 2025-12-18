import re
from config import AGENT_SYSTEM_PROMPT
from tools import available_tools

class Agent:
    def __init__(self, llm_client):
        self.llm = llm_client
        self.history_prompt = []

    def run(self, user_prompt: str, max_steps: int = 5):
        # 初始化，保存用户最原始的需求
        # 保存历史对话，驱动多轮推理
        self.history_prompt = [f"用户输入：{user_prompt}\n" + "=" * 40]

        # 运行主循环
        for i in range(max_steps):
            print(f"------循环{i+1}------\n")

            # 将对话、思考、行动、观察的prompt完整拼接起来，交给LLM继续推理
            full_prompt = "\n".join(self.history_prompt)
            llm_output = self.llm.generate(full_prompt, system_prompt=AGENT_SYSTEM_PROMPT)

            # 精准地截取“第一个 Thought + Action”
            match = re.search(r'(Thought:.*?Action:.*?)(?=\n\s*(?:Thought:|Action:|Observation:)|\Z)', llm_output, re.DOTALL)

            if match:
                truncated = match.group(1).strip()
                if truncated != llm_output:
                    llm_output = truncated
                    print("已截断多余的Thought-Action对")

                print(f"模型输出：{llm_output}")
                self.history_prompt.append(llm_output)

            # 从 LLM 输出中，可靠地提取 Action: 后面的可执行指令字符串
            action_match = re.search(r"Action:(.*)", llm_output, re.DOTALL)
            if not action_match:
                print("解析错误！模型输出中未找到匹配的Action")
                break

            action_str = action_match.group(1).strip()

            # 识别 Agent 的“终止指令”
            if action_str.startswith("finish"):
                final_answer = re.search(r'finish\(answer="(.*)"\)', action_str).group(1)
                print(f"任务完成！最终答案：{final_answer}")
                break

            # 解析函数名和参数
            try:
                tool_name = re.search(r"(\w+)\(", action_str).group(1)
                args_str = re.search(r"\((.*)\)", action_str).group(1)
                kwargs = dict(re.findall(r'(\w+)="([^"]*)"', args_str))
            except Exception as e:
                print(f"参数解析失败: {e}")
                break

            # 执行工具
            if tool_name in available_tools:
                observation = available_tools[tool_name](**kwargs)
            else:
                observation = f"错误:未定义的工具 '{tool_name}'"

            # 记录观察结果
            observation_str = f"Observation: {observation}"
            print(f"{observation_str}\n" + "=" * 40)
            self.history_prompt.append(observation_str)