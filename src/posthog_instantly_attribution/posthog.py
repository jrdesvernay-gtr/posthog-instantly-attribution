import logging
import re
from typing import Any

import httpx

from .config import Config

logger = logging.getLogger(__name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_email(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    email = value.strip().lower()
    return email if EMAIL_RE.match(email) else None


def get_trial_emails(
    client: httpx.Client,
    config: Config,
    since: str,
    include_already_attributed: bool,
) -> list[str]:
    already_attributed_filter = ""
    if not include_already_attributed:
        already_attributed_filter = """
          AND (
            person.properties.attributed_source IS NULL
            OR person.properties.attributed_source != 'Instantly'
          )
        """

    query = f"""
        SELECT DISTINCT e.distinct_id AS email
        FROM events e
        WHERE e.event = 'trial_started'
          AND e.timestamp >= '{since}'
          AND e.distinct_id IS NOT NULL
          {already_attributed_filter}
    """

    logger.debug("Running HogQL query for trial emails since %s", since)
    response = client.post(
        f"{config.posthog_host}/api/projects/{config.posthog_project_id}/query",
        headers={"Authorization": f"Bearer {config.posthog_personal_api_key}"},
        json={"query": {"kind": "HogQLQuery", "query": query}},
    )
    response.raise_for_status()

    rows = response.json().get("results", [])
    emails: list[str] = []
    seen: set[str] = set()

    for row in rows:
        if not row:
            continue
        email = normalize_email(row[0])
        if not email:
            logger.warning("Skipping non-email distinct_id: %r", row[0])
            continue
        if email not in seen:
            emails.append(email)
            seen.add(email)

    logger.info("Found %d trial signup email(s) since %s", len(emails), since)
    return emails


def set_attributed_source(
    client: httpx.Client,
    config: Config,
    email: str,
    value: str = "Instantly",
) -> None:
    response = client.post(
        f"{config.posthog_host}/capture/",
        json={
            "api_key": config.posthog_project_api_key,
            "event": "$identify",
            "distinct_id": email,
            "properties": {"$set": {"attributed_source": value}},
        },
    )
    response.raise_for_status()
    logger.debug("Set attributed_source=%s for %s", value, email)
