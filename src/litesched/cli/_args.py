import argparse
from collections.abc import Sequence
from typing import assert_never

from litesched.models import AddTimer, RemoveTimer, UpdateTimer


def parse_args(args: Sequence[str] | None = None) -> AddTimer | RemoveTimer | UpdateTimer:
    parser = argparse.ArgumentParser()
    subparser = parser.add_subparsers(dest="command")

    subparser_add = subparser.add_parser("add")
    subparser_add.add_argument("job_id")
    subparser_add.add_argument("cron")

    subparser_remove = subparser.add_parser("remove")
    subparser_remove.add_argument("job_id")

    subparser_update = subparser.add_parser("update")
    subparser_update.add_argument("job_id")
    subparser_update.add_argument("cron")

    ns = parser.parse_args(args)

    match ns.command:
        case "add":
            return AddTimer(ns.job_id, ns.cron)
        case "remove":
            return RemoveTimer(ns.job_id)
        case "update":
            return UpdateTimer(ns.job_id, ns.cron)
        case _:
            assert_never(ns.command)
