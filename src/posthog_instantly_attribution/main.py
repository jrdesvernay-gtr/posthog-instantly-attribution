import argparse
import logging
import sys
import time
from datetime import date, timedelta

import httpx

from .config import Config
from .instantly import exists_in_instantly
from .posthog import get_trial_emails, set_attributed_source

logger = logging.getLogger(__name__)


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        stream=sys.stdout,
    )


def validate_since(value: str) -> str:
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("since must be a date in YYYY-MM-DD format") from exc
    return value


def default_since(lookback_days: int) -> str:
    return (date.today() - timedelta(days=lookback_days)).isoformat()


def run(
    *,
    since: str,
    dry_run: bool,
    include_already_attributed: bool,
) -> int:
    config = Config.from_env()

    matched = 0
    unmatched = 0
    updated = 0
    errors = 0

    with httpx.Client(timeout=config.request_timeout_seconds) as client:
        emails = get_trial_emails(
            client=client,
            config=config,
            since=since,
            include_already_attributed=include_already_attributed,
        )

        if dry_run:
            logger.info("Dry run enabled: no PostHog person properties will be changed")

        for email in emails:
            try:
                if exists_in_instantly(client, config, email):
                    matched += 1
                    if dry_run:
                        logger.info("MATCH (dry run): %s -> would set attributed_source=Instantly", email)
                    else:
                        set_attributed_source(client, config, email, "Instantly")
                        updated += 1
                        logger.info("MATCH: %s -> set attributed_source=Instantly", email)
                else:
                    unmatched += 1
                    logger.info("NO MATCH: %s -> not found in Instantly", email)

            except httpx.HTTPStatusError as exc:
                errors += 1
                logger.error(
                    "HTTP error for %s: status=%d body=%s",
                    email,
                    exc.response.status_code,
                    exc.response.text[:500],
                )
            except Exception as exc:
                errors += 1
                logger.error("Unexpected error for %s: %s: %s", email, type(exc).__name__, exc)

            time.sleep(config.sleep_seconds)

    logger.info(
        "Done. matched=%d unmatched=%d updated=%d errors=%d",
        matched, unmatched, updated, errors,
    )

    return 1 if errors else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Attribute PostHog trial signups to Instantly when the trial email "
            "exists in Instantly. Sets PostHog person property attributed_source=Instantly."
        )
    )
    parser.add_argument(
        "--since",
        type=validate_since,
        default=None,
        help="Start date for trial_started events (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--lookback-days",
        type=int,
        default=2,
        help="Days to look back when --since is omitted (default: 2).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Check Instantly matches but do not update PostHog.",
    )
    parser.add_argument(
        "--include-already-attributed",
        action="store_true",
        help="Include people who already have attributed_source=Instantly.",
    )
    return parser.parse_args()


def main() -> None:
    configure_logging()
    args = parse_args()
    since = args.since or default_since(args.lookback_days)
    raise SystemExit(
        run(
            since=since,
            dry_run=args.dry_run,
            include_already_attributed=args.include_already_attributed,
        )
    )
