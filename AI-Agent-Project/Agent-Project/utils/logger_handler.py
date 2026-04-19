import logging
import os

from utils.path_tool import get_abs_path
from datetime import datetime

# 日志保存的根目录
LOG_ROOT = get_abs_path("logs")

# 确保日志根目录存在
os.makedirs(LOG_ROOT, exist_ok=True)

# 日志的格式配置
DEFAULT_LOG_FORMAT = logging.Formatter(
    '%(asctime)s - %(name)-8s [%(levelname)-8s] %(filename)s:%(lineno)d - %(message)s',
)

def get_logger(name="agent", console_level=logging.INFO, file_level=logging.DEBUG, log_file=None) -> logging.Logger:
    logger = logging.getLogger(name=name)
    logger.setLevel(logging.DEBUG)

    # 避免重复添加 Handler，避免日志重复输出
    if logger.handlers:
        return logger

    # 控制台 Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(DEFAULT_LOG_FORMAT)

    logger.addHandler(console_handler)

    if not log_file:
        log_file = os.path.join(LOG_ROOT, f"{name}_{datetime.now().strftime('%Y%m%d%H%M%S')}.log")

    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(file_level)
    file_handler.setFormatter(DEFAULT_LOG_FORMAT)

    logger.addHandler(file_handler)

    return logger

logger = get_logger()

if __name__ == "__main__":
    logger.info("[INFO] 调试")
    logger.warning("[WARN] 调试")
    logger.error("[ERROR] 调试")
    logger.debug("[DEBUG] 调试")