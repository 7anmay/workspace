from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .config import ConfigStore
from .monitor import ApartmentMonitor
from .notifier import SlackNotifier, format_listing_batch
from .slack_app import ApartmentSlackApp


def main() -> None:
    parser = argparse.ArgumentParser(description="Slack-driven SF apartment availability monitor.")
    parser.add_argument("--config", default="config.yaml", help="Path to config YAML.")
    parser.add_argument("--log-level", default="INFO", help="Python logging level.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Write a starter config file.")
    init_parser.add_argument("--overwrite", action="store_true", help="Overwrite an existing config.")

    run_parser = subparsers.add_parser("run-once", help="Run one search cycle.")
    run_parser.add_argument("--no-slack", action="store_true", help="Print results without Slack notification.")

    subparsers.add_parser("watch", help="Run scheduled searches forever.")
    subparsers.add_parser("slack-bot", help="Listen for Slack commands via Socket Mode.")

    args = parser.parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level.upper()), format="%(levelname)s %(message)s")
    store = ConfigStore(Path(args.config))

    if args.command == "init":
        config = store.init_default(overwrite=args.overwrite)
        print(f"Wrote {store.path} with {len(config.sources)} sources.")
        return

    if args.command == "run-once":
        config = store.load()
        notifier = None if args.no_slack else SlackNotifier(channel_id=config.slack_channel_id)
        fresh = ApartmentMonitor(store, notifier=notifier, notify=not args.no_slack).run_once()
        print(format_listing_batch(fresh, config) if fresh else "No new matching apartments found.")
        return

    if args.command == "watch":
        config = store.load()
        ApartmentMonitor(store, notifier=SlackNotifier(channel_id=config.slack_channel_id)).watch()
        return

    if args.command == "slack-bot":
        ApartmentSlackApp(store).start()
        return
