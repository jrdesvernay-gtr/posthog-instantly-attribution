import logging

import httpx

from .config import Config

logger = logging.getLogger(__name__)


def exists_in_instantly(client: httpx.Client, config: Config, email: str) -> bool:
    response = client.post(
        f"{config.instantly_host}/api/v2/leads/list",
        headers={"Authorization": f"Bearer {config.instantly_api_key}"},
        json={"contacts": [email], "limit": 1},
    )
    response.raise_for_status()

    found = len(response.json().get("items", [])) > 0
    logger.debug("Instantly lookup for %s: %s", email, "found" if found else "not found")
    return found
