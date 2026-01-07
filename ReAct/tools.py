from typing import Dict, List
import os # 新增
from dotenv import load_dotenv # 新增
from tavily import TavilyClient # 新增

# 加载环境变量
load_dotenv() 

class ToolExecutor :
    def __init__(self):
        """
        初始化工具执行器
        """
        self.tools: Dict[str,Dict[str,str]]={}
        
        # 🟢 修正：在此处初始化 Tavily，而不是在 llm.py 中
        self.tavily_api_key = os.getenv("TAVILY_API_KEY")
        if not self.tavily_api_key:
            print("警告: TAVILY_API_KEY 未设置，搜索功能将不可用。")
            self.tavily = None
        else:
            self.tavily = TavilyClient(api_key=self.tavily_api_key)

    def register_tool(self,name:str,description:str,func:callable) :
        """
        向工具执行器注册一个工具
        """
        if name in self.tools :
            print(f"警告！工具 {name} 已存在，即将覆盖。")
        self.tools[name]={"description":description,"function":func}
        print(f"工具 {name} 注册成功。")


    def get_tool(self,name:str)->callable :
        """
        根据名称获取工具函数
        """
        return self.tools.get(name,{}).get("function")
    

    def getAvaliableTools(self)->str :
        """
        获取所有可用工具的格式化描述字符串
        """
        return "\n".join([
            f"- {name}: {info['description']}" 
            for name, info in self.tools.items()
        ])
    
    #===================调用Tavily进行网页搜索=========================

    def search_web(self, query: str) -> str:
            """
            使用Tavily进行网页搜索（已优化：防卡死版本）
            """
            # 1. 安全检查
            if not self.tavily:
                return "错误：搜索工具未正确配置 API Key。"

            print(f"🔎 使用Tavily搜索: {query}")
            
            try:
                # 2. 调用 API (限制结果数量为 3，减少数据量)
                # search_depth="basic" 速度快，费用低
                response = self.tavily.search(query=query, max_results=3, search_depth="basic")
                
                # 3. 解析结果 (关键修正：不要直接返回 response)
                # 提取 results 列表，忽略其他元数据
                if not response or 'results' not in response:
                    return "未找到相关搜索结果。"

                results_list = response['results']
                formatted_outputs = []

                # 4. 格式化提取核心字段
                for item in results_list:
                    title = item.get('title', '无标题')
                    url = item.get('url', '#')
                    # content 通常是网页摘要
                    content = item.get('content', '无摘要')
                    
                    entry = f"【标题】{title}\n【链接】{url}\n【摘要】{content}\n"
                    formatted_outputs.append(entry)

                # 5. 合并成字符串
                final_result = "\n---\n".join(formatted_outputs)

                # 6. 🛑 强制截断 (防止下一次 LLM 调用卡死)
                # 限制在 2000 字符以内，这对 LLM 已经足够了
                if len(final_result) > 2000:
                    final_result = final_result[:2000] + "\n...(内容过长已截断)"

                return final_result
                
            except Exception as e:
                print(f"调用Tavily时出错: {e}")
                return f"搜索出错: {e}"