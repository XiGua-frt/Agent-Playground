from llm import DeepSeekClient
from tools import ToolExecutor
from promt import REACT_PROMPT_TEMPLATE
import re

class ReActAgent :
    def __init__(self,deepseek_client : DeepSeekClient,tool_executor : ToolExecutor,max_steps:int=5) :
        self.deepseek_client=deepseek_client
        self.tool_executor=tool_executor
        self.max_steps=max_steps
        self.history=[]

    def run(self,question:str) -> str :
        """
        执行ReAct代理，处理用户问题
        """

        #每次运行前清空历史记录
        self.history.clear()
        cur_step=0

        while cur_step < self.max_steps :
            cur_step += 1
            print(f"\n--- ReAct 步骤 {cur_step} ---")

            #1.格式化提示词
            promt=REACT_PROMPT_TEMPLATE.format(
                tools=self.tool_executor.getAvaliableTools(),
                question=question,
                history="\n".join(self.history)
            )

            #2.调用LLM获取响应
            messages=[{"role":"user","content":promt}]
            response=self.deepseek_client.think(messages)

            print(f"\n[DEBUG LLM 回复]:\n{response}\n[DEBUG 结束]\n")

            if not response :
                print("LLM未返回响应，终止代理执行。")
                break

            #3.解析LLM响应
            thought,action=self._parse_output(response)

            if not action and "2025" in str(thought) and cur_step > 2:
                print("⚠️ 检测到模型可能已经回答但未触发 Finish，强制结束。")
                return thought  # 直接把思考过程当做答案返回


            # 关键：记录 Thought，让 LLM 保持逻辑连贯
            if thought:
                self.history.append(f"Thought: {thought}")

            if not action:
                # 给 LLM 一个反馈，尝试让它修复格式
                self.history.append("Observation: Error, format your output as Thought: ... Action: ...")
                continue

            # 4. 执行动作
            if action.startswith("Finish"):
                # 方案A：正则提取最终答案
                answer_match = re.match(r"Finish\s*\[(.*)\]", action, re.DOTALL)
                
                if answer_match:
                    final_answer = answer_match.group(1)
                else:
                    # 方案B (兜底)：正则挂了？手动暴力截取！
                    # 去掉开头的 "Finish[" 和末尾的 "]"
                    final_answer = action.replace("Finish", "", 1).strip()
                    if final_answer.startswith("["):
                        final_answer = final_answer[1:]
                    if final_answer.endswith("]"):
                        final_answer = final_answer[:-1]
                
                print(f"\n✅ 任务完成！最终答案:\n{final_answer}")
                return final_answer

            try:
                tool_name, tool_param = self._parse_action(action)
                tool_func = self.tool_executor.get_tool(tool_name)
                if tool_func:
                    observation = tool_func(tool_param)
                else:
                    observation = f"Error: Tool {tool_name} not found."
            except Exception as e:
                observation = f"Error during tool execution: {e}"

            # 5. 更新历史记录
            self.history.append(f"Action: {action}")
            self.history.append(f"Observation: {observation}")

        print("\n⚠️ 达到最大步骤数，代理执行终止。")
        return None



    #=================解析LLM响应=================================
    def _parse_output(self, text: str):
        """
        正则解析：支持多行 Thought 并精确定位 Action
        """
        # 使用 re.DOTALL 使得 . 可以匹配换行符
        # Thought: 匹配到 Action: 之前的所有内容
        thought_pattern = r"Thought:\s*(.*?)(?=\s*Action:|$)"
        # Action: 匹配到字符串末尾
        action_pattern = r"Action:\s*(.*)"

        # 提取 Thought
        thought_match = re.search(thought_pattern, text, re.DOTALL)
        # 提取 Action (Action 通常是单行指令，或者 Finish[...])
        action_match = re.search(action_pattern, text, re.DOTALL)

        thought = thought_match.group(1).strip() if thought_match else None
        action = action_match.group(1).strip() if action_match else None

        return thought, action
    

    def _parse_action(self, action_text: str):
        """
        Action 解析：支持多行参数，防止过度匹配。
        """
        if not action_text:
            return None, None

        pattern = r"^(\w+)\[(.*?)\]"
        
        match = re.search(pattern, action_text, re.DOTALL)
        
        if match:
            tool_name = match.group(1).strip()
            tool_params = match.group(2).strip()
            return tool_name, tool_params
            
        return None, None