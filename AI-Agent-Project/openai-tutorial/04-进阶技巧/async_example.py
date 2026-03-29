import asyncio
from openai import AsyncOpenAI

client = AsyncOpenAI()

async def chat(message):
    """单个聊天请求"""
    response = await client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": message}]
    )
    return response.choices[0].message.content

async def main():
    """并发多个请求示例"""
    print("=== 并发请求示例 ===\n")
    
    # 并发多个请求
    tasks = [
        chat("用一句话解释什么是人工智能"),
        chat("Python 中列表和元组的区别是什么"),
        chat("推荐一本经典的科幻小说"),
        chat("如何学习编程最有效率"),
        chat("解释一下量子计算的原理")
    ]
    
    results = await asyncio.gather(*tasks)
    
    questions = [
        "人工智能",
        "列表 vs 元组",
        "科幻小说推荐",
        "学习方法",
        "量子计算"
    ]
    
    for i, (question, result) in enumerate(zip(questions, results), 1):
        print(f"{i}. {question}:")
        print(f"   {result}\n")

if __name__ == "__main__":
    asyncio.run(main())
