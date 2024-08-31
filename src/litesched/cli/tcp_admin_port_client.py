import argparse
import asyncio
import ssl
import sys
from collections.abc import Sequence

import msgspec

from litesched.models import AddTimer, RemoveTimer, UpdateTimer

PORT = 8888


async def admin_client(args: AddTimer | RemoveTimer | UpdateTimer) -> None:
    ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=".certs/cert.pem")
    ssl_context.load_cert_chain(certfile=".certs/cert.pem", keyfile=".certs/key.pem")
    reader, writer = await asyncio.open_connection("127.0.0.1", PORT, ssl=ssl_context)

    data = msgspec.json.encode(args)
    writer.write(data)
    await writer.drain()

    data = await reader.read(1024)
    print(f"Received: {data.decode()!r}")

    print("Close the connection")
    writer.close()
    await writer.wait_closed()


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
            raise NotImplementedError(f"Unknown command {ns.command}")


def main() -> int:
    args = parse_args()
    try:
        asyncio.run(admin_client(args))
    except Exception as e:
        print(f"ERROR: {e!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
