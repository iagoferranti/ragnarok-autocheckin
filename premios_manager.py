import os
import json
from urllib.parse import urlsplit, urlunsplit

WATCHLIST_FILE = "premios_watchlist.json"


# =========================================================
# Utils de caminho (compatível com EXE PyInstaller)
# =========================================================
def get_base_path():
    import sys
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _watchlist_path():
    return os.path.join(get_base_path(), WATCHLIST_FILE)


# =========================================================
# Normalização de URL (evita mismatch de evento)
# =========================================================
def normalizar_url(u: str) -> str:
    if not u:
        return ""
    u = u.strip()
    parts = urlsplit(u)
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path.rstrip("/"), "", "")
    )


# =========================================================
# Watchlist
# =========================================================
def carregar_watchlist():
    """
    Retorna:
    {
        "event_url": "...",
        "selected": [ "Item A", "Item B", ... ]
    }
    ou None se não existir
    """
    p = _watchlist_path()
    if not os.path.exists(p):
        return None

    try:
        with open(p, "r", encoding="utf-8") as f:
            wl = json.load(f)

        if not isinstance(wl, dict):
            return None

        if wl.get("event_url"):
            wl["event_url"] = normalizar_url(wl["event_url"])

        wl["selected"] = wl.get("selected", []) or []
        return wl

    except Exception:
        return None


def salvar_watchlist(event_url: str, selected: list):
    payload = {
        "event_url": normalizar_url(event_url),
        "selected": selected,
    }
    with open(_watchlist_path(), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
