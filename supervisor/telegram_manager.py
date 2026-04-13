"""
Telegram Manager — RESTful API integration for Ouroboros.

Manages Telegram bot communication using direct HTTP requests to Bot API.
No external async libraries required.
"""
import asyncio
import json
import logging
from typing import Dict, Optional, Any, Callable
import aiohttp

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}"


class TelegramManager:
    """Simple Telegram bot manager using RESTful API."""

    def __init__(self, token: str):
        self.token = token
        self.api_url = TELEGRAM_API.format(token=token)
        self._session: Optional[aiohttp.ClientSession] = None
        self._bot_info: Optional[Dict] = None
        self._running = False
        self._on_message: Optional[Callable] = None

    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def _request(self, method: str, **kwargs) -> Dict:
        """Make a request to Telegram Bot API."""
        url = f"{self.api_url}/{method}"
        session = await self.get_session()

        try:
            async with session.post(url, **kwargs) as resp:
                data = await resp.json()
                if not data.get("ok"):
                    logger.error(f"Telegram API error: {data}")
                    raise Exception(f"Telegram API error: {data.get('description', 'Unknown error')}")
                return data
        except aiohttp.ClientError as e:
            logger.error(f"HTTP request failed: {e}")
            raise

    async def get_me(self) -> Dict[str, Any]:
        """Get bot info."""
        if self._bot_info is None:
            result = await self._request("getMe")
            self._bot_info = result["result"]
            logger.info(f"Telegram bot: @{self._bot_info['username']}")
        return self._bot_info

    async def send_message(
        self,
        chat_id: int,
        text: str,
        parse_mode: str = None,
        reply_markup: Dict = None
    ) -> Dict:
        """Send a message to a chat."""
        payload = {"chat_id": chat_id, "text": text}
        if parse_mode:
            payload["parse_mode"] = parse_mode
        if reply_markup:
            payload["reply_markup"] = reply_markup
        return await self._request("sendMessage", json=payload)

    async def get_updates(
        self,
        offset: int = 0,
        timeout: int = 30,
        limit: int = 100
    ) -> list:
        """Get updates from Telegram (long polling)."""
        payload = {"offset": offset, "timeout": timeout, "limit": limit}
        result = await self._request("getUpdates", json=payload, timeout=timeout + 5)
        return result.get("result", [])

    async def delete_webhook(self) -> Dict:
        """Delete any existing webhook."""
        logger.info("Deleting Telegram webhook...")
        return await self._request("deleteWebhook")

    def set_message_handler(self, handler: Callable):
        """Set callback for incoming messages."""
        self._on_message = handler

    async def start_polling(self):
        """Start long polling for updates."""
        await self.get_me()
        await self.delete_webhook()

        self._running = True
        offset = 0
        logger.info("Starting Telegram polling...")

        while self._running:
            try:
                updates = await self.get_updates(offset=offset, timeout=30)
                for update in updates:
                    if "message" in update:
                        await self._handle_message(update["message"])
                        offset = update["update_id"] + 1
                    elif "edited_message" in update:
                        await self._handle_message(update["edited_message"])
                        offset = update["update_id"] + 1
                if updates:
                    if not updates:
                        offset = updates[-1]["update_id"] + 1
            except asyncio.CancelledError:
                logger.info("Polling cancelled")
                break
            except Exception as e:
                logger.error(f"Polling error: {e}")
                await asyncio.sleep(5)

    async def stop_polling(self):
        """Stop polling."""
        self._running = False

    async def _handle_message(self, message: Dict):
        """Process incoming message."""
        chat_id = message["chat"]["id"]
        text = message.get("text", "")
        user = message["from"]

        logger.info(f"Telegram message from {user['first_name']} (@{user.get('username', 'N/A')}): {text}")

        if self._on_message:
            await self._on_message(chat_id, user, text, message)

    async def health_check(self) -> bool:
        """Check if bot is accessible."""
        try:
            await self.get_me()
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    @property
    def bot_username(self) -> Optional[str]:
        """Get bot username."""
        if self._bot_info:
            return self._bot_info.get("username")
        return None
