"""
Token Agent — vazifa murakkabligiga qarab model tanlaydi.
tasks.md da vazifa [OPUS/SONNET/HAIKU] bilan belgilanadi.
"""
import logging
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class Complexity(Enum):
    HIGH = "high"       # Opus: arxitektura, vision prompt, complex reasoning
    MEDIUM = "medium"   # Sonnet: qidiruv, scraping, format, orchestration
    LOW = "low"         # Haiku: CRUD, oddiy format, log, simple tasks


class ModelChoice(Enum):
    OPUS = "claude-opus-4-7"
    SONNET = "claude-sonnet-4-6"
    HAIKU = "claude-haiku-4-5-20251001"


_COMPLEXITY_TO_MODEL: dict[Complexity, ModelChoice] = {
    Complexity.HIGH: ModelChoice.OPUS,
    Complexity.MEDIUM: ModelChoice.SONNET,
    Complexity.LOW: ModelChoice.HAIKU,
}

_TASK_REGISTRY: dict[str, Complexity] = {
    "image_analysis": Complexity.HIGH,
    "prompt_engineering": Complexity.HIGH,
    "architecture_review": Complexity.HIGH,
    "marketplace_search": Complexity.MEDIUM,
    "result_formatting": Complexity.MEDIUM,
    "scraping_orchestration": Complexity.MEDIUM,
    "db_crud": Complexity.LOW,
    "logging": Complexity.LOW,
    "contact_save": Complexity.LOW,
    "health_check": Complexity.LOW,
}


def get_model(task_name: str, override: Optional[Complexity] = None) -> str:
    complexity = override or _TASK_REGISTRY.get(task_name, Complexity.MEDIUM)
    model = _COMPLEXITY_TO_MODEL[complexity]
    logger.debug("Task '%s' → %s (%s)", task_name, model.value, complexity.value)
    return model.value


def log_task_to_md(task_name: str, status: str, model: str) -> None:
    """tasks.md va done.md boshqarish uchun helper."""
    logger.info("[%s] %s — %s", model.upper(), task_name, status)
