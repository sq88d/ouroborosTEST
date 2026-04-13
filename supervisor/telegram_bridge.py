"""Bridge between TelegramManager and Ouroboros message bus.

This module sets up a handler that receives messages from the Telegram
manager and forwards them into the local message bridge, so that they are
treated like any other user message coming from the web UI.
"""

from supervisor.message_bus import get_bridge
from supervisor.telegram_globals import _TELEGRAM_MANAGER, _TELEGRAM_CHAT_ID


def install_handler(manager):
    """Install a callback on a :class:`TelegramManager` instance.

    The callback stores the manager instance and the originating chat id in
    the global ``_TELEGRAM_MANAGER`` / ``_TELEGRAM_CHAT_ID`` variables (used by
    ``message_bus.send_with_budget`` to forward replies back to Telegram) and
    pushes the incoming text onto the local ``LocalChatBridge`` inbox.
    """
    async def _on_message(chat_id, user, text, raw_message):
        # Store globals for reply routing
        global _TELEGRAM_MANAGER, _TELEGRAM_CHAT_ID
        _TELEGRAM_MANAGER = manager
        _TELEGRAM_CHAT_ID = chat_id
        # Forward incoming text to the local bridge (treated as user input)
        bridge = get_bridge()
        # Directly put into the inbox queue – this is internal API but safe.
        bridge._inbox.put(text)
        # Optionally, you could log the inbound message.
        return True

    manager._on_message = _on_message
    return True
