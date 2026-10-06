import asyncio
import logging
import time
from abc import ABC, abstractmethod
import websockets
from gapx.state_store import StateStore

logger = logging.getLogger(__name__)

class BaseWSClient(ABC):
    """Simple helper managing WebSocket connection lifecycle, auto-reconnect, and backoff."""
    def __init__(
        self,
        exchange_name: str,
        ws_url: str,
        state_store: StateStore,
        initial_backoff: float = 1.0,
        max_backoff: float = 30.0,
    ):
        self.exchange_name = exchange_name.lower()
        self.ws_url = ws_url
        self.state_store = state_store
        self.initial_backoff = initial_backoff
        self.max_backoff = max_backoff
        
        self.is_connected = False
        self.running = False
        self.last_msg_time = 0.0
        self._task: asyncio.Task | None = None
        self._ping_task: asyncio.Task | None = None

    @abstractmethod
    def get_subscription_payload(self) -> dict | str | None:
        """Returns subscription payload sent upon opening connection."""
        pass

    @abstractmethod
    async def handle_message(self, raw_message: str | bytes) -> None:
        """Parse exchange payload and update state_store."""
        pass

    async def send_ping(self, ws: websockets.WebSocketClientProtocol) -> None:
        """Optional custom ping frame."""
        pass

    async def _ping_loop(self, ws: websockets.WebSocketClientProtocol) -> None:
        try:
            while self.is_connected and self.running:
                await asyncio.sleep(15)
                if self.is_connected:
                    await self.send_ping(ws)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.warning(f"[{self.exchange_name}] Ping error: {e}")

    async def start(self) -> None:
        self.running = True
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        self.running = False
        self.is_connected = False
        if self._ping_task and not self._ping_task.done():
            self._ping_task.cancel()
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _run_loop(self) -> None:
        current_backoff = self.initial_backoff

        while self.running:
            try:
                logger.info(f"[{self.exchange_name}] Connecting to {self.ws_url}...")
                async with websockets.connect(
                    self.ws_url,
                    ping_interval=20,
                    ping_timeout=10,
                    close_timeout=5,
                    max_size=10 * 1024 * 1024,
                ) as ws:
                    self.is_connected = True
                    current_backoff = self.initial_backoff
                    logger.info(f"[{self.exchange_name}] Connected.")

                    sub_payload = self.get_subscription_payload()
                    if sub_payload:
                        if isinstance(sub_payload, dict):
                            import json
                            await ws.send(json.dumps(sub_payload))
                        else:
                            await ws.send(sub_payload)

                    self._ping_task = asyncio.create_task(self._ping_loop(ws))

                    async for message in ws:
                        if not self.running:
                            break
                        self.last_msg_time = time.time()
                        try:
                            await self.handle_message(message)
                        except Exception as e:
                            logger.error(f"[{self.exchange_name}] Parsing error: {e}", exc_info=True)

            except (websockets.ConnectionClosed, websockets.WebSocketException, OSError, asyncio.TimeoutError) as e:
                self.is_connected = False
                logger.warning(f"[{self.exchange_name}] WS connection lost ({e}). Reconnecting in {current_backoff:.1f}s...")
            except asyncio.CancelledError:
                self.is_connected = False
                break
            except Exception as e:
                self.is_connected = False
                logger.error(f"[{self.exchange_name}] Unexpected error: {e}", exc_info=True)

            if self._ping_task and not self._ping_task.done():
                self._ping_task.cancel()

            if self.running:
                await asyncio.sleep(current_backoff)
                current_backoff = min(current_backoff * 2, self.max_backoff)
