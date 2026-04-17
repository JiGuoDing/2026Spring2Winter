from utils.config_handler import prompt_config
from utils.path_tool import get_abs_path
from utils.logger_handler import logger

def load_system_prompts():
    try:
        system_prompt_path = get_abs_path(prompt_config["main_prompt_path"])
        try:
            return open(system_prompt_path, "r", encoding="utf-8").read()
        except FileNotFoundError as e:
            logger.error(f"[load_system_prompts] 解析系统提示词出错, {str(e)}")
            raise e
    except KeyError as e:
        logger.error(f"[load_system_prompts] 在 yaml 配置项中没有 main_prompt_path 配置项")
        raise e

def load_rag_prompts():
    try:
        rag_prompt_path = get_abs_path(prompt_config["rag_summarize_prompt_path"])
        try:
            return open(rag_prompt_path, "r", encoding="utf-8").read()
        except FileNotFoundError as e:
            logger.error(f"[load_rag_prompts] 解析 RAG 总结提示词出错, {str(e)}")
            raise e
    except KeyError as e:
        logger.error(f"[load_rag_prompts] 在 yaml 配置项中没有 rag_summarize_prompt_path 配置项")
        raise e

def load_report_prompts():
    try:
        report_prompt_path = get_abs_path(prompt_config["report_prompt_path"])
        try:
            return open(report_prompt_path, "r", encoding="utf-8").read()
        except FileNotFoundError as e:
            logger.error(f"[load_report_prompts] 解析报告生成提示词出错, {str(e)}")
            raise e
    except KeyError as e:
        logger.error(f"[load_report_prompts] 在 yaml 配置项中没有 report_prompt_path 配置项")
        raise e
