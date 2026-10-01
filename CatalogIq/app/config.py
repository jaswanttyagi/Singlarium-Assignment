import os
from dotenv import load_dotenv

load_dotenv()
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "mock")
LLM_CONCURRENCY = int(os.getenv("LLM_CONCURRENCY", 5))
MOCK_LATENCY_MS = int(os.getenv("MOCK_LATENCY_MS", 200))
MOCK_FAILURE_RATE = float(os.getenv("MOCK_FAILURE_RATE", 0.1))

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-2.5-flash"
)
float(os.getenv("MOCK_FAILURE_RATE", 0.1)) 