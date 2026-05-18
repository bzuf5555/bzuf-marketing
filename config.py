import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    BOT_TOKEN: str
    GEMINI_API_KEY: str
    MONGODB_URI: str
    RENDER_EXTERNAL_URL: str
    PORT: int
    WEBHOOK_SECRET: str
    MAX_SEARCH_RESULTS: int = 5
    SEARCH_TIMEOUT: int = 10
    MIN_REQUEST_INTERVAL: float = 2.0
    MAX_PARALLEL_SEARCHES: int = 3


def load_config() -> Config:
    required = ["BOT_TOKEN", "GEMINI_API_KEY", "MONGODB_URI"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")

    return Config(
        BOT_TOKEN=os.environ["BOT_TOKEN"],
        GEMINI_API_KEY=os.environ["GEMINI_API_KEY"],
        MONGODB_URI=os.environ["MONGODB_URI"],
        RENDER_EXTERNAL_URL=os.getenv("RENDER_EXTERNAL_URL", ""),
        PORT=int(os.getenv("PORT", 8443)),
        WEBHOOK_SECRET=os.getenv(
            "WEBHOOK_SECRET",
            os.environ["BOT_TOKEN"].replace(":", "_").replace("-", "_")[:32],
        ),
    )
