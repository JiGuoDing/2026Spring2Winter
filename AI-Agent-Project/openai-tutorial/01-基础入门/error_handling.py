from openai import OpenAI, APIError, RateLimitError, AuthenticationError

client = OpenAI()

try:
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Hello"}]
    )
    print(response.choices[0].message.content)
    
except AuthenticationError:
    print("API Key 无效")
    
except RateLimitError:
    print("请求频率超限")
    
except APIError as e:
    print(f"API 错误：{e}")
    
except Exception as e:
    print(f"未知错误：{e}")
