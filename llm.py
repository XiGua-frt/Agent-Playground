from openai import OpenAI

class OpenAICompatibleClient:
    # 初始化
    def __init__(self, model: str, api_key: str, base_url: str):
        self.model = model
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def generate(self, prompt: str, system_prompt: str) -> str:
        # 调用大语言模型
        print("正在调用大语言模型......")

        try:
            message = [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': prompt},
            ]

            # 通过已经创建好的 OpenAI 客户端发送请求
            response = self.client.chat.completions.create(
                model=self.model,
                messages=message,
                stream=False
            )

            answer = response.choices[0].message.content
            print("大语言模型响应成功！")
            return answer

        except Exception as e:
            print(f"调用LLM API时发生错误: {e}")
            return "错误:调用语言模型服务时出错。"