import os
import json
import time
from urllib.parse import urlsplit, urlunsplit

import unicodedata
import re

def normalizar_premio(txt: str) -> str:
    if not txt:
        return ""
    txt = txt.strip().lower()
    txt = unicodedata.normalize("NFKD", txt)
    txt = "".join(c for c in txt if not unicodedata.combining(c))
    txt = re.sub(r"\s+", " ", txt)
    return txt


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



def configurar_watchlist_manual():
    """
    Menu 6 (100% manual):
    Usuário cola os nomes dos prêmios que deseja monitorar/logar.
    Um por linha. Linha vazia finaliza.
    """
    print("\n🎁 CONFIGURAR PRÊMIOS PARA O LOG (100% MANUAL)\n")
    print("📋 Cole os NOMES DOS PRÊMIOS exatamente como aparecem no site")
    print("👉 Um prêmio por linha")
    print("👉 Não precisa se preocupar com acento/maiúscula (o sistema normaliza)")
    print("👉 ENTER em branco finaliza\n")

    itens = []
    while True:
        ln = input("> ").strip()
        if not ln:
            break
        itens.append(ln)

    if not itens:
        print("❌ Nenhum prêmio informado.")
        input("\nEnter...")
        return

    # remove duplicados mantendo ordem
    vistos = set()
    itens_unicos = []
    for x in itens:
        key = normalizar_premio(x)
        if key and key not in vistos:
            itens_unicos.append(x.strip())   # mantém original bonitinho
            vistos.add(key)


    wl_nova = {
    "selected": itens_unicos,
    "selected_norm": [normalizar_premio(x) for x in itens_unicos],
    "updated_at_epoch": int(time.time())
    }


    salvar_watchlist(wl_nova)

    print("\n✅ Watchlist salva com sucesso!")
    print("🎯 Prêmios monitorados:")
    for p in itens_unicos:
        print("  -", p)

    selected = itens_unicos
    selected_norm = [normalizar_premio(x) for x in selected]

    wl_nova = {
        "selected": selected,
        "selected_norm": selected_norm,
        "updated_at_epoch": int(time.time())
    }
    salvar_watchlist(wl_nova)


    input("\nEnter para voltar ao menu...")




# =========================================================
# Watchlist
# =========================================================

def carregar_watchlist():
    p = _watchlist_path()
    if not os.path.exists(p):
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            wl = json.load(f)
        return wl if isinstance(wl, dict) else None
    except:
        return None


def salvar_watchlist(wl: dict):
    """
    Salva o dicionário inteiro da watchlist.
    Exemplo:
      {"selected": [...], "updated_at_epoch": 123}
    """
    with open(_watchlist_path(), "w", encoding="utf-8") as f:
        json.dump(wl, f, ensure_ascii=False, indent=2)