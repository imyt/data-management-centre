import sys
import asyncio
import selectors
import uvicorn

async def run_server():
    config = uvicorn.Config("app.main:app", host="127.0.0.1", port=8000, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.run(
            run_server(),
            loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()),
        )
    else:
        asyncio.run(run_server())
