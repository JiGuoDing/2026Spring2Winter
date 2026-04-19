import os.path
import random

from langchain_core.tools import tool
from rag.rag_service import RagSummarizeService
from utils.config_handler import agent_config
from utils.path_tool import get_abs_path
from utils.logger_handler import logger


rag = RagSummarizeService()

user_ids = ["001", "002", "003", "004", "005", "006", "007", "008"]

months = ["2025-01", "2025-02", "2025-03", "2025-04", "2025-05", "2025-06", "2025-07", "2025-08", "2025-09", "2025-10", "2025-11", "2025-12", ]

external_data = {}

@tool(description="从向量数据库中检索参考资料。")
def rag_summarize(query: str) -> str:
    return rag.rag_summarize(query=query)

@tool(description="获取指定城市的天气，以消息字符串的形式返回。")
def get_weather(city: str) -> str:
    return f"城市 {city} 天气为晴天，气温为 26 摄氏度，空气湿度为 50%，AQI 为 21，最近 6 小时内不会降雨。"

@tool(description="")
def get_user_location() -> str:
    return random.choice(["南京", "杭州", "上海"])

@tool(description="获取用户的 ID，以字符串的形式返回。")
def get_user_id() -> str:
    return random.choice(user_ids)

@tool(description="获取当前月份，以纯字符串的形式返回。")
def get_current_month() -> str:
    return random.choice(months)

def generate_external_data():
    if not external_data:
        external_data_path = get_abs_path(agent_config["external_data_path"])
        if not os.path.exists(external_data_path):
            raise FileNotFoundError(f"外部数据文件 {external_data_path} 不存在")

        with open(external_data_path, "r", encoding="utf-8") as f:
            for line in f.readlines()[1:]:
                fields = line.strip().split(",")

                user_id = fields[0].replace('"', "")
                feature = fields[1].replace('"', "")
                efficiency = fields[2].replace('"', "")
                consumables = fields[3].replace('"', "")
                comparison = fields[4].replace('"', "")
                time = fields[5].replace('"', "")

                if user_id not in external_data:
                    external_data[user_id] = {}

                external_data[user_id][time] = {
                    "特征": feature,
                    "效率": efficiency,
                    "耗材": consumables,
                    "对比": comparison,
                }


@tool(description="从外部系统获取指定用户在指定月份的使用记录，以纯字符串的形式返回，如果未检索到则返回空字符串。")
def fetch_external_data(user_id: str, month: str) -> str:
    generate_external_data()

    try:
        return external_data[user_id][month]
    except KeyError as e:
        logger.error(f"[ERROR] - [fetch_external_data] 未能检索到用户 {user_id} 在 {month} 的使用记录: {str(e)}")
        return ""

@tool(description="无入参，无返回值，调用后触发中间件自动为报告生成的场景动态注入上下文信息，为后续提示词切换提供上下文信息。")
def fill_context_for_report():
    return "fill_context_for_report 已调用"

if __name__ == "__main__":
    print(fetch_external_data(user_id="001", month="2025-02"))