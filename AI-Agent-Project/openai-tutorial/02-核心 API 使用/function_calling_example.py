from openai import OpenAI
import json

client = OpenAI()

# 定义工具
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取某个城市的天气信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "城市名称，例如：北京、上海"
                    }
                },
                "required": ["location"]
            }
        }
    }
]

def get_weather(location):
    """模拟天气查询"""
    weather_data = {
        "北京": "晴朗，25°C, 湿度 40%",
        "上海": "多云，22°C, 湿度 60%",
        "广州": "小雨，28°C, 湿度 80%"
    }
    return weather_data.get(location, f"{location}的天气数据暂不可用")

# 第一轮对话
messages = [{"role": "user", "content": "北京天气怎么样？"}]

response = client.chat.completions.create(
    model="gpt-4",
    messages=messages,
    tools=tools
)

# 检查是否需要调用工具
if response.choices[0].message.tool_calls:
    tool_call = response.choices[0].message.tool_calls[0]
    function_name = tool_call.function.name
    arguments = json.loads(tool_call.function.arguments)
    
    print(f"🔧 调用函数：{function_name}")
    print(f"📍 参数：{arguments}")
    
    # 执行函数
    result = get_weather(arguments["location"])
    print(f"📊 返回结果：{result}")
    
    # 添加工具响应到消息
    messages.append(response.choices[0].message)
    messages.append({
        "role": "tool",
        "tool_call_id": tool_call.id,
        "content": result
    })
    
    # 获取最终回复
    final_response = client.chat.completions.create(
        model="gpt-4",
        messages=messages
    )
    
    print(f"\n🤖 AI 回复：{final_response.choices[0].message.content}")
else:
    print(response.choices[0].message.content)
