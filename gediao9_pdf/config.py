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


def get_env(key, default=""):
    """读取环境变量，优先系统环境，其次 .env 文件。"""
    val = os.environ.get(key)
    if val is not None and val != "":
        return val
    _env = load_env()
    return _env.get(key, default)


def get_oss_config():
    """从环境变量读取阿里云 OSS 配置，缺失时返回 None。"""
    access_key_id = get_env("OSS_ACCESS_KEY_ID")
    access_key_secret = get_env("OSS_ACCESS_KEY_SECRET")
    if not access_key_id or not access_key_secret:
        return None
    return {
        "access_key_id": access_key_id,
        "access_key_secret": access_key_secret,
        "endpoint": get_env("OSS_ENDPOINT", "oss-cn-beijing.aliyuncs.com"),
        "bucket_name": get_env("OSS_BUCKET_NAME", "gediao9"),
        "access_point_url": get_env("OSS_ACCESS_POINT_URL", ""),
    }


# 文件上传整理接口使用的根目录，可通过环境变量覆盖
INPUT_BASE_DIR = get_env(
    "INPUT_BASE_DIR",
    os.path.join(SCRIPT_DIR, "..", "gediao_temp_content"),
)


def get_llm_client(env_path=None):
    _env = load_env(env_path)
    return OpenAI(
        base_url=_env.get("OPENAI_BASE_URL", ""),
        api_key=_env.get("OPENAI_API_KEY", ""),
        timeout=120.0,
    ), _env.get("MODEL", "deepseek-v4-pro")


TEMPLATES_DIR = os.path.join(SCRIPT_DIR, "templates")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "..", "output")