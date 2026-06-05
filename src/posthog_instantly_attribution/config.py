import os
from dataclasses import dataclass


def _get_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


@dataclass(frozen=True)
class Config:
    posthog_personal_api_key: str
    posthog_project_api_key: str
    posthog_project_id: str
    instantly_api_key: str
    posthog_host: str
    instantly_host: str
    request_timeout_seconds: float
    sleep_seconds: float

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            posthog_personal_api_key=_get_env("POSTHOG_PERSONAL_API_KEY"),
            posthog_project_api_key=_get_env("POSTHOG_PROJECT_API_KEY"),
            posthog_project_id=_get_env("POSTHOG_PROJECT_ID"),
            instantly_api_key=_get_env("INSTANTLY_API_KEY"),
            posthog_host=os.getenv("POSTHOG_HOST", "https://app.posthog.com").rstrip("/"),
            instantly_host=os.getenv("INSTANTLY_HOST", "https://api.instantly.ai").rstrip("/"),
            request_timeout_seconds=float(os.getenv("REQUEST_TIMEOUT_SECONDS", "45")),
            sleep_seconds=float(os.getenv("SLEEP_SECONDS", "0.1")),
        )
