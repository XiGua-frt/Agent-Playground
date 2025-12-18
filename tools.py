import requests
import os
from tavily import TavilyClient

# ============================= 获取天气状况 =========================

def get_weather(city: str) -> str:
    # 调用wttr.in API 查询天气
    url = f"http://wttr.in/{city}?format=j1"

    try:
        response = requests.get(url)
        # 检查请求是否成功
        response.raise_for_status()
        # 如果成功，则解析数据格式
        date = response.json()

        # 用字典+列表来存储数据
        current_condition = date['current_condition'][0]
        weather_desc = current_condition['weatherDesc'][0]['value']
        temp_c = current_condition['temp_C']

        # 格式化成自然语言，返回
        return f"{city}当前天气：{weather_desc}，气温{temp_c}摄氏度"

    except requests.exceptions.RequestException as e:
        return f"错误！查询天气时遇到网络问题-{e}"
    except (KeyError, IndexError) as e:
        return f"错误！解析天气数据失败，可能是城市名称无效-{e}"


# ========================= 获取景点推荐 =============================

def get_attraction(city: str, weather: str) -> str:
    """
    Tavily Search API的功能是：为AI / Agent提供
    “可直接推理和输出的高质量联网搜索结果”，而不是原始网页数据。
    """

    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return "错误，未配置api_key"

    # 创建一个已完成鉴权配置的 Tavily API 客户端实例
    tavily = TavilyClient(api_key=api_key)

    # 构造查询
    query = f"{city}在{weather}天气下最值得去的景点推荐按及理由"

    try:
        # 调用搜索API
        response = tavily.search(query=query, search_depth="basic", include_answer=True)

        if response.get("answer"):
            return response["answer"]

        formatted_results = []
        for result in response.get("results", []):
            formatted_results.append(f"- {result['title']}：{result['content']}")

        if not formatted_results:
            return "抱歉，没有找到相关的旅游景点推荐。"

        return "根据搜索，为您找到以下信息:\n" + "\n".join(formatted_results)

    except Exception as e:
        return f"错误:执行Tavily搜索时出现问题 - {e}"

# 工具映射字典
available_tools = {
    "get_weather": get_weather,
    "get_attraction": get_attraction,
}