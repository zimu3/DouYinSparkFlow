# 尝试从 .env 文件加载环境变量
import os
if os.path.exists(".env"):
    from dotenv import load_dotenv

    load_dotenv(".env")

from core.web_tasks import run_tasks

run_tasks(os.getenv("RUN_MODE", "smoke"))
