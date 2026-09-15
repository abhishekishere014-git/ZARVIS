"""Main entrypoint for running the JARVIS Python Core standalone daemon."""

import asyncio
import signal
import sys
from jarvis.bootstrap import bootstrap_system
from jarvis.config.settings import JarvisSettings
from jarvis.core.engine import JarvisEngine
from jarvis.logging.logger import setup_logging


async def main() -> None:
    settings = JarvisSettings()
    logger = setup_logging(level=settings.log_level, json_format=False)
    logger.info("Initializing JARVIS Python Core Daemon...")

    engine, _ = bootstrap_system(settings=settings)

    loop = asyncio.get_running_loop()

    def handle_signal() -> None:
        logger.info("Signal received, initiating shutdown...")
        asyncio.create_task(engine.shutdown())

    # Attach signal handlers for graceful shutdown (Unix and Windows compatible)
    if sys.platform != "win32":
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, handle_signal)
    else:
        def win_handler(sig, frame):
            logger.info("Signal %s received on Windows, initiating shutdown...", sig)
            loop.call_soon_threadsafe(lambda: asyncio.create_task(engine.shutdown()))

        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                signal.signal(sig, win_handler)
            except Exception:
                pass
        if hasattr(signal, "SIGBREAK"):
            try:
                signal.signal(signal.SIGBREAK, win_handler)
            except Exception:
                pass

    try:
        await engine.start()
        # Keep running until shutdown is triggered
        await engine.run_until_stopped()
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Interrupted. Cleaning up...")
        await engine.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
