import os

from openai import OpenAI

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def load_env(env_path=None):
    if env_path is None:
        env_path = os.path.join(SCRIPT_DIR, "..", ".env")
    _env = {}
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    _env[k.strip()] = v.strip()
    return _env


def get_llm_client(env_path=None):
    _env = load_env(env_path)
    return OpenAI(
        base_url=_env.get("OPENAI_BASE_URL", ""),
        api_key=_env.get("OPENAI_API_KEY", ""),
        timeout=120.0,
    ), _env.get("MODEL", "deepseek-v4-pro")


TEMPLATES_DIR = os.path.join(SCRIPT_DIR, "templates")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "..", "output")