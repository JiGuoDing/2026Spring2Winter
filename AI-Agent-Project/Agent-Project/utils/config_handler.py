import yaml
from utils.path_tool import get_abs_path

def load_rag_config(config_path: str=get_abs_path(r"config/rag.yaml"), encoding="utf-8") -> dict:
    with open(config_path, encoding=encoding) as f:
        return yaml.load(f, Loader=yaml.FullLoader)

def load_prompt_config(config_path: str=get_abs_path(r"config/prompt.yaml"), encoding="utf-8") -> dict:
    with open(config_path, encoding=encoding) as f:
        return yaml.load(f, Loader=yaml.FullLoader)

def load_chroma_config(config_path: str=get_abs_path(r"config/chroma.yaml"), encoding="utf-8") -> dict:
    with open(config_path, encoding=encoding) as f:
        return yaml.load(f, Loader=yaml.FullLoader)

def load_agent_config(config_path: str = get_abs_path(r"config/agent.yaml"), encoding="utf-8") -> dict:
    with open(config_path, encoding=encoding) as f:
        return yaml.load(f, Loader=yaml.FullLoader)

rag_config = load_rag_config()
prompt_config = load_prompt_config()
chroma_config = load_chroma_config()
agent_config = load_agent_config()

if __name__ == "__main__":
    print(rag_config["chat_model _name"])