import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

API_BASE_URL = os.getenv(
    "API_BASE_URL",
    "https://trec-be-868757013548.europe-west2.run.app"
)
