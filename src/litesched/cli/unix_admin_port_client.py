import asyncio
import ssl
import sys

import msgspec

from litesched.cli.unix_abstract_admin_port_client import parse_args
from litesched.models import AddTimer, RemoveTimer, UpdateTimer

ADDRESS = "/tmp/litesched"


async def admin_client(args: AddTimer | RemoveTimer | UpdateTimer) -> None:
    ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=".certs/cert.pem")
    ssl_context.load_cert_chain(certfile=".certs/cert.pem", keyfile=".certs/key.pem")
    reader, writer = await asyncio.open_unix_connection(
        path=ADDRESS,
        ssl=ssl_context,
        server_hostname="127.0.0.1",
    )

    data = msgspec.json.encode(args)
    writer.write(data)
    await writer.drain()

    data = await reader.read(1024)
    print(f"Received: {data.decode()!r}")

    print("Close the connection")
    writer.close()
    await writer.wait_closed()


def main() -> int:
    args = parse_args()
    try:
        asyncio.run(admin_client(args))
    except Exception as e:
        print(f"ERROR: {e!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
