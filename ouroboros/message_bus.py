def send_with_budget(chat_id: int, text: str, log_text: Optional[str] = None,
                     force_budget: bool = False, fmt: str = "",
                     is_progress: bool = False) -> None:
    # force_budget kept in signature for caller compat but is a no-op since 3.3.0
    st = load_state()
    owner_id = int(st.get("owner_id") or 0)

    if is_progress and DATA_DIR:
        append_jsonl(DATA_DIR / "logs" / "progress.jsonl", {
            "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "direction": "out", "chat_id": chat_id, "user_id": owner_id,
            "text": text if log_text is None else log_text,
        })
    else:
        log_chat("out", chat_id, owner_id, text if log_text is None else log_text)

    _text = str(text or "")
    if _text.strip() in ("", "\u200b"):
        return
    # Budget footers are now shown in dashboard/status flows, not auto-appended
    # to every outgoing chat message.
    full = _text

    if fmt == "markdown":
        ok, err = _send_markdown(chat_id, full)
        return

    bridge = get_bridge()
    for part in split_message(full):
        bridge.send_message(chat_id, part)

    # Forward to Telegram if manager is set and we have a chat id
    try:
        from supervisor.telegram_manager import TelegramManager  # noqa: F401
    except Exception:
        TelegramManager = None
    if _TELEGRAM_MANAGER is not None and _TELEGRAM_CHAT_ID is not None:
        # Use asyncio to send without blocking
        import asyncio
        async def _tg_send():
            try:
                await _TELEGRAM_MANAGER.send_message(_TELEGRAM_CHAT_ID, full)
            except Exception as e:
                log.error(f"Failed to send Telegram reply: {e}")
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(_tg_send())
        else:
            loop.run_until_complete(_tg_send())
*** End Patch