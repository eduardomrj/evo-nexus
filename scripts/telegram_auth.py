#!/usr/bin/env python3
"""
Autentica a sessão do Telegram para o Community Observer.
Execute uma vez: .venv/bin/python scripts/telegram_auth.py
"""
import asyncio
from pathlib import Path
from dotenv import load_dotenv
import os

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

api_id   = int(os.environ["TELEGRAM_API_ID"])
api_hash = os.environ["TELEGRAM_API_HASH"]
session  = str(ROOT / "config" / "telegram_observer_session")

async def main():
    from telethon import TelegramClient
    client = TelegramClient(session, api_id, api_hash)
    await client.start()          # pede telefone + código interativamente
    me = await client.get_me()
    print(f"\nAutenticado como: {me.first_name} (@{me.username})")
    print(f"Sessão salva em: {session}.session")
    await client.disconnect()

asyncio.run(main())
