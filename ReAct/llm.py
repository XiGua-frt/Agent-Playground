import os
from openai import OpenAI
from dotenv import load_dotenv
from typing import List,Dict

load_dotenv()

class DeepSeekClient :
    def __init__(self,model:str=None,apikey:str=None,baseurl:str=None,
timeout:int=None) :
        """
        初始化客户端
        """
        self.model=model or os.getenv("DEEPSEEK_MODEL_ID","deepseek-chat")
        self.apikey=apikey or os.getenv("DEEPSEEK_API_KEY")
        self.baseurl=baseurl or os.getenv("DEEPSEEK_BASE_URL","https://api.deepseek.com")
        self.timeout=timeout or int(os.getenv("DEEPSEEK_TIMEOUT",300))

        if not all([self.model,self.apikey,self.baseurl]) :
            raise ValueError("模型ID、API密钥和服务地址必须被提供或在.env文件中定义。")
        
        self.client=OpenAI(api_key=self.apikey,base_url=self.baseurl,timeout=self.timeout)



#====================调用LLM进行思考===================================

    def think(self,messages:List[Dict[str,str]],temperature:float=0)->str :
        """
        调用LLM，返回其响应
        """
        print(f"调用模型 {self.model} 进行思考...")
        try :
            response=self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                stream=False,
                stop=["Observation:","Observation"]
            )

            print("大语言模型响应成功！")
            return response.choices[0].message.content
        
        except Exception as e :
            print(f"调用大语言模型时出错: {e}")
            return None