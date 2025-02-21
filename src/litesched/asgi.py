import asyncio
import contextlib
import logging
import ssl
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from datetime import datetime
from functools import partial
from typing import Union

import msgspec
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from litestar import Litestar, get

from litesched.app_config import (
    get_compression_config,
    get_cors_config,
    get_csrf_config,
    get_debug_config,
    get_logging_config,
    get_openapi_config,
)
from litesched.config import APP_NAME, STATIC_DIR
from litesched.models import AddTimer, RemoveTimer, UpdateTimer

logger = logging.getLogger(APP_NAME)


@get("/")
async def main() -> str:
    return "hello world"


@get("/favicon.ico", sync_to_thread=False, cache=True)
def favicon() -> bytes:
    return (STATIC_DIR / "favicon.ico").read_bytes()


async def admin_command_listener(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    app: Litestar,
) -> None:
    data = await reader.read(1024)
    logging.getLogger("uvicorn").info("Received message: %s", data)
    scheduler: AsyncIOScheduler = app.state.scheduler

    command = msgspec.json.decode(data, type=Union[UpdateTimer, AddTimer, RemoveTimer])

    if isinstance(command, UpdateTimer):
        second, minute, hour, day, week, month = command.cron.split()
        scheduler.print_jobs()
        scheduler.reschedule_job(
            command.job_id,
            trigger=CronTrigger(
                month=month,
                week=week,
                day=day,
                hour=hour,
                minute=minute,
                second=second,
            ),
        )
        writer.write("Success!".encode())
        await writer.drain()
    elif isinstance(command, AddTimer):
        second, minute, hour, day, week, month = command.cron.split()
        scheduler.add_job(
            tick,
            trigger=CronTrigger(
                month=month,
                week=week,
                day=day,
                hour=hour,
                minute=minute,
                second=second,
            ),
            id=command.job_id,
        )
        writer.write("Success!".encode())
        await writer.drain()
    elif isinstance(command, RemoveTimer):
        scheduler.remove_job(command.job_id)
        writer.write("Success!".encode())
        await writer.drain()
    else:
        writer.write("Failed!".encode())
        await writer.drain()

    writer.close()
    await writer.wait_closed()
    print("Closed the writer")


async def tick() -> None:
    print("tick: " + datetime.now().strftime(r"%Y-%m-%dT%H:%M:%S%z"))
    background_tasks: set[asyncio.Future] = set()
    try:
        tasks = []
        for i in range(5, 11):
            task = asyncio.create_task(worker(name=str(i), duration=i))
            background_tasks.add(task)
            tasks.append(task)
            task.add_done_callback(background_tasks.discard)
        await asyncio.gather(*tasks, return_exceptions=True)
    except asyncio.CancelledError:
        for background_task in background_tasks:
            background_task.cancel()
        with contextlib.suppress(asyncio.TimeoutError):
            async with asyncio.timeout(10):
                asyncio.gather(*background_tasks, return_exceptions=True)
        raise


async def worker(name: str, duration: float) -> None:
    try:
        print(f"{name}: Sleeping...")
        await asyncio.sleep(duration)
    except asyncio.CancelledError:
        print(f"{name}: Cancelling... ")
        raise


async def start_admin_listener_tcp_socket(
    callback: Callable[[asyncio.StreamReader, asyncio.StreamWriter], Awaitable[None]],
    *,
    port: int = 8888,
    ssl: ssl.SSLContext | None = None,
) -> asyncio.Server:
    logger.debug(f"Starting TCP admin listener at {port=}")
    return await asyncio.start_server(
        client_connected_cb=callback,
        host="127.0.0.1",
        port=port,
        ssl=ssl,
    )


async def start_admin_listener_unix_socket(
    callback: Callable[[asyncio.StreamReader, asyncio.StreamWriter], Awaitable[None]],
    *,
    address: str = f"/tmp/{APP_NAME}_admin_socket",
    ssl: ssl.SSLContext | None = None,
) -> asyncio.Server:
    logger.debug(f"Starting Unix Socket admin listener at {address=}")
    return await asyncio.start_unix_server(
        client_connected_cb=callback,
        path=address,
        ssl=ssl,
    )


async def start_admin_listener_abstract_unix_socket(
    callback: Callable[[asyncio.StreamReader, asyncio.StreamWriter], Awaitable[None]],
    *,
    address: str = f"\0{APP_NAME}_admin_socket",
    ssl: ssl.SSLContext | None = None,
) -> asyncio.Server:
    if not address.startswith("\0"):
        raise ValueError(f"Abstract socket addresses need to start with a null byte ({address})")
    logger.debug(f"Starting Unix Abstract Socket admin listener at {address=}")
    return await asyncio.start_unix_server(
        client_connected_cb=callback,
        path=address,
        ssl=ssl,
    )


@asynccontextmanager
async def lifespan(app: Litestar) -> AsyncIterator[None]:
    # Creating the scheduler and bootstrapping it with a ticker that runs every 3 seconds
    app.state.scheduler = AsyncIOScheduler()
    app.state.scheduler.add_job(
        tick,
        trigger=CronTrigger(second="*/3"),
        id="ticker",
    )
    app.state.scheduler.start()

    # Creating SSL context for admin ports that require mutual TLS authentication
    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.load_cert_chain(certfile=".certs/cert.pem", keyfile=".certs/key.pem")
    ssl_context.verify_mode = ssl.CERT_REQUIRED
    ssl_context.load_verify_locations(cafile=".certs/cert.pem")

    admin_port_callback = partial(admin_command_listener, app=app)

    tasks: list[asyncio.Task[asyncio.Server]] = []
    async with asyncio.TaskGroup() as tg:
        tasks.append(
            tg.create_task(
                start_admin_listener_tcp_socket(
                    admin_port_callback,
                    port=8888,
                    ssl=ssl_context,
                ),
            )
        )
        tasks.append(
            tg.create_task(
                start_admin_listener_unix_socket(
                    admin_port_callback,
                    address=f"/tmp/{APP_NAME}",
                    ssl=ssl_context,
                ),
            )
        )
        tasks.append(
            tg.create_task(
                start_admin_listener_abstract_unix_socket(
                    admin_port_callback,
                    address=f"\0{APP_NAME}",
                    ssl=ssl_context,
                ),
            )
        )
    servers: list[asyncio.Server] = [task.result() for task in tasks]

    try:
        async with contextlib.AsyncExitStack() as stack:
            for server in servers:
                s = await stack.enter_async_context(server)
                asyncio.create_task(s.serve_forever())
            yield
    finally:
        uvicorn_logger = logging.getLogger("uvicorn")
        uvicorn_logger.info("Scheduler shutdown initiated...")
        app.state.scheduler.shutdown()
        uvicorn_logger.info("Scheduler shutdown complete")


def create_app() -> Litestar:
    return Litestar(
        route_handlers=[
            main,
            favicon,
        ],
        lifespan=[lifespan],
        debug=get_debug_config(),
        compression_config=get_compression_config(),
        cors_config=get_cors_config(),
        csrf_config=get_csrf_config(),
        openapi_config=get_openapi_config(),
        logging_config=get_logging_config(),
    )
