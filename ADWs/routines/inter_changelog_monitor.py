#!/usr/bin/env python3
"""
ADW: Inter Changelog Monitor — Detecta novos itens em developers.inter.co/changelog
e notifica via Telegram usando o feed JSON nativo do site.

Agendamento: mensal — dia 1 às 08:00 (config/routines.yaml)
Dados persistentes: /home/evonexus/evo-projects-data/inter-changelog-monitor/
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import re
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path

FEED_URL = "https://developers.inter.co/changelog/feed.json"
CHANGELOG_URL = "https://developers.inter.co/changelog"
DATA_DIR = Path(
    os.environ.get(
        "INTER_CHANGELOG_DATA_DIR",
        "/home/evonexus/evo-projects-data/inter-changelog-monitor",
    )
)
KNOWN_IDS_FILE = DATA_DIR / "known_ids.json"
HISTORY_FILE = DATA_DIR / "history.json"
MAX_MSG_LEN = 3800  # Margem segura abaixo do limite do Telegram (4096)


# ---------------------------------------------------------------------------
# HTML → texto limpo (para o conteúdo dos itens do feed)
# ---------------------------------------------------------------------------

def _strip_html(html: str) -> str:
    """Remove tags HTML e ancora links; retorna texto limpo."""
    text = re.sub(r"<a[^>]*href=\"([^\"]+)\"[^>]*>([^<]+)</a>", r"\2 (\1)", html)
    text = re.sub(r"<h[1-6][^>]*>", "\n\n▸ ", text)
    text = re.sub(r"</h[1-6]>", "\n", text)
    text = re.sub(r"<li[^>]*>", "\n  • ", text)
    text = re.sub(r"<p[^>]*>", "\n", text)
    text = re.sub(r"<strong>(.*?)</strong>", r"*\1*", text)
    text = re.sub(r"<code>(.*?)</code>", r"`\1`", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Feed
# ---------------------------------------------------------------------------

def _fetch_feed() -> list[dict]:
    """Retorna lista de itens do feed JSON."""
    req = urllib.request.Request(
        FEED_URL,
        headers={"User-Agent": "Mozilla/5.0 (compatible; EvoNexus-Monitor/1.0)"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    return data.get("items", [])


# ---------------------------------------------------------------------------
# Persistência de IDs conhecidos
# ---------------------------------------------------------------------------

def _load_known_ids() -> set[str]:
    if KNOWN_IDS_FILE.exists():
        try:
            return set(json.loads(KNOWN_IDS_FILE.read_text("utf-8")))
        except Exception:
            pass
    return set()


def _save_known_ids(ids: set[str]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    KNOWN_IDS_FILE.write_text(json.dumps(sorted(ids), indent=2, ensure_ascii=False), "utf-8")


def _append_history(entry: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    history: list = []
    if HISTORY_FILE.exists():
        try:
            history = json.loads(HISTORY_FILE.read_text("utf-8"))
        except Exception:
            pass
    history.append(entry)
    HISTORY_FILE.write_text(
        json.dumps(history[-100:], indent=2, ensure_ascii=False), "utf-8"
    )


# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------

def _send_telegram(text: str) -> bool:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    cid = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not token or not cid:
        print("  ⚠ Telegram não configurado (TELEGRAM_BOT_TOKEN ou TELEGRAM_CHAT_ID ausente)")
        return False
    if len(text) > MAX_MSG_LEN:
        text = text[:MAX_MSG_LEN] + "\n…(truncado)"
    try:
        payload = urllib.parse.urlencode(
            {"chat_id": cid, "text": text, "parse_mode": "HTML"}
        ).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=payload,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            ok = resp.status == 200
        print("  ✓ Telegram enviado" if ok else f"  ⚠ Telegram status {resp.status}")
        return ok
    except Exception as e:
        print(f"  ⚠ Telegram error: {e}")
        return False


def _format_item(item: dict) -> str:
    """Formata um item do feed em texto para Telegram."""
    title = item.get("title") or item.get("id", "Sem título")
    url = item.get("url") or item.get("id", CHANGELOG_URL)
    date_raw = item.get("date_published", "")
    date_str = date_raw[:10] if date_raw else ""

    content_html = item.get("content_html", "")
    content_text = _strip_html(content_html)[:600]
    if len(_strip_html(content_html)) > 600:
        content_text += "\n…"

    parts = [f"<b>{title}</b>"]
    if date_str:
        parts.append(f"📅 {date_str}")
    if url:
        parts.append(f"🔗 <a href='{url}'>Ver detalhes</a>")
    if content_text:
        parts.append(f"\n{content_text}")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    now = datetime.now()
    print(f"[inter-changelog] {now.strftime('%Y-%m-%d %H:%M')} — verificando feed")

    # 1. Busca feed
    try:
        items = _fetch_feed()
    except Exception as e:
        print(f"  ✗ Erro ao buscar feed: {e}")
        _send_telegram(
            f"⚠️ <b>Inter Changelog Monitor</b>\n\n"
            f"Erro ao buscar o feed:\n<code>{e}</code>\n\n"
            f"🔗 {CHANGELOG_URL}"
        )
        sys.exit(1)

    print(f"  → {len(items)} itens no feed")
    all_ids = {item["id"] for item in items if "id" in item}
    known_ids = _load_known_ids()

    # 2. Primeira execução
    if not known_ids:
        _save_known_ids(all_ids)
        _append_history({"date": now.isoformat(), "event": "first_run", "total_items": len(items)})
        latest = items[0] if items else {}
        latest_title = latest.get("title", "—")
        _send_telegram(
            f"🔔 <b>Inter Changelog Monitor</b>\n\n"
            f"✅ Monitoramento iniciado!\n"
            f"📄 {len(items)} entradas registradas\n"
            f"📌 Mais recente: <b>{latest_title}</b>\n"
            f"🔗 <a href='{CHANGELOG_URL}'>Ver changelog</a>\n\n"
            f"Próxima verificação: 1º do mês que vem."
        )
        print(f"  ✓ Primeira execução — {len(items)} IDs salvos.")
        return

    # 3. Detecta novos itens (não estavam na última verificação)
    new_ids = all_ids - known_ids
    if not new_ids:
        _append_history({"date": now.isoformat(), "event": "no_changes"})
        print("  ✓ Sem novidades — nenhuma notificação enviada.")
        return

    # 4. Itens novos encontrados — ordena pela posição no feed (mais recente primeiro)
    new_items = [it for it in items if it.get("id") in new_ids]
    print(f"  → {len(new_items)} item(ns) novo(s) detectado(s)")

    _save_known_ids(all_ids)
    _append_history({
        "date": now.isoformat(),
        "event": "changes_detected",
        "new_count": len(new_items),
        "new_ids": list(new_ids),
    })

    # Envia uma mensagem por item (ou consolida se forem muitos)
    if len(new_items) == 1:
        header = f"🚨 <b>Inter Changelog — 1 novidade!</b>\n\n"
        msg = header + _format_item(new_items[0])
        _send_telegram(msg)
    else:
        # Consolida em uma mensagem
        header = f"🚨 <b>Inter Changelog — {len(new_items)} novidades!</b>\n\n"
        parts = [header]
        for it in new_items:
            title = it.get("title") or it.get("id", "—")
            url = it.get("url") or it.get("id", "")
            date_raw = it.get("date_published", "")[:10]
            line = f"• <b>{title}</b>"
            if date_raw:
                line += f" ({date_raw})"
            if url:
                line += f" — <a href='{url}'>ver</a>"
            parts.append(line)
        parts.append(f"\n🔗 <a href='{CHANGELOG_URL}'>Changelog completo</a>")
        _send_telegram("\n".join(parts))

    print(f"  ✓ {len(new_items)} novidade(s) — notificação enviada.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠ Cancelado.")
