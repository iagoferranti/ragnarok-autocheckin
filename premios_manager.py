import os
import json
import time
import unicodedata
import re
import sys

# Nome do arquivo de configuração de watchlist
WATCHLIST_FILE = "premios_watchlist.json"

# =========================================================
# Base path (compatível com EXE PyInstaller e Raiz do Projeto)
# =========================================================
def get_base_path():
    """Retorna o caminho onde o executável ou script principal está rodando."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def _watchlist_path():
    return os.path.join(get_base_path(), WATCHLIST_FILE)

def _premios_dir():
    # Cria pasta premios na raiz se não existir
    p = os.path.join(get_base_path(), "premios")
    os.makedirs(p, exist_ok=True)
    return p

def _premios_filtrado_dir():
    p = os.path.join(_premios_dir(), "filtrado")
    os.makedirs(p, exist_ok=True)
    return p

def _premios_filtrado_file():
    return os.path.join(_premios_filtrado_dir(), "premios_filtrados.txt")

# =========================================================
# Normalização de prêmio (case-insensitive + sem acento)
# =========================================================
def normalizar_premio(txt: str) -> str:
    if not txt:
        return ""
    txt = txt.strip().lower()
    txt = unicodedata.normalize("NFKD", txt)
    txt = "".join(c for c in txt if not unicodedata.combining(c))
    txt = re.sub(r"\s+", " ", txt)
    return txt

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
    with open(_watchlist_path(), "w", encoding="utf-8") as f:
        json.dump(wl, f, ensure_ascii=False, indent=2)

def sync_premios_filtrados_incremental():
    """
    Lê TODOS os .txt dentro de /premios/bruto e adiciona (append)
    no /premios/filtrado/premios_filtrados.txt apenas as linhas com match
    na watchlist. Não sobrescreve e evita duplicatas.
    """
    wl = carregar_watchlist() or {}
    alvo_norm = set(
        wl.get("selected_norm")
        or [normalizar_premio(x) for x in (wl.get("selected") or [])]
    )

    if not alvo_norm:
        raise Exception("Watchlist vazia. Configure no Menu 6 antes.")

    bruto_dir = os.path.join(_premios_dir(), "bruto")
    if not os.path.exists(bruto_dir):
        # Se não tiver a pasta bruto, cria pra evitar erro, mas avisa
        os.makedirs(bruto_dir, exist_ok=True)
        return _premios_filtrado_file(), 0, 0, 0

    out_path = _premios_filtrado_file()

    # carrega linhas já existentes para não duplicar
    existentes = set()
    if os.path.exists(out_path):
        with open(out_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                s = line.strip()
                if not s: continue
                if s.startswith("=====") or s.startswith("gerado_em_epoch=") or s.startswith("watchlist_") or s == "-----":
                    continue
                existentes.add(s)

    # lista txts somente do bruto
    txts = []
    for root, _, files in os.walk(bruto_dir):
        for fn in files:
            if fn.lower().endswith(".txt"):
                txts.append(os.path.join(root, fn))

    if not txts:
        # Nada para sincronizar
        return out_path, 0, 0, 0

    total_lidas = 0
    novas = []

    for path in sorted(txts):
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    s = line.strip()
                    if not s or s.startswith("====="): continue
                    
                    total_lidas += 1

                    if " | " not in s: continue

                    premio = s.split(" | ")[-1].strip()
                    if normalizar_premio(premio) in alvo_norm:
                        if s not in existentes:
                            novas.append(s)
                            existentes.add(s)
        except: pass

    # se arquivo não existe, cria com um header simples
    arquivo_novo = not os.path.exists(out_path)
    try:
        with open(out_path, "a", encoding="utf-8") as f:
            if arquivo_novo:
                f.write("===== PREMIOS FILTRADOS (INCREMENTAL) =====\n")
                f.write(f"criado_em_epoch={int(time.time())}\n")
                f.write("-----\n")
            for l in novas:
                f.write(l + "\n")
    except: pass

    return out_path, len(txts), total_lidas, len(novas)


def configurar_watchlist_manual():
    """
    Menu 6 (100% manual): usuário cola os NOMES que quer monitorar.
    """
    print("\n🎁 CONFIGURAR PRÊMIOS PARA O LOG (100% MANUAL)\n")
    print("📋 Cole os NOMES DOS PRÊMIOS exatamente como aparecem no site")
    print("👉 Um prêmio por linha")
    print("👉 ENTER em branco finaliza\n")

    itens = []
    while True:
        ln = input("> ").strip()
        if not ln: break
        itens.append(ln)

    if not itens:
        print("❌ Nenhum prêmio informado.")
        time.sleep(1) # Pequeno delay
        return

    # remove duplicados mantendo ordem
    vistos = set()
    itens_unicos = []
    for x in itens:
        if x not in vistos:
            itens_unicos.append(x)
            vistos.add(x)

    wl_nova = {
        "selected": itens_unicos,
        "selected_norm": [normalizar_premio(x) for x in itens_unicos],
        "updated_at_epoch": int(time.time()),
    }

    salvar_watchlist(wl_nova)

    print("\n✅ Watchlist salva com sucesso!")
    print("🎯 Prêmios monitorados:")
    for p in itens_unicos:
        print("  -", p)

    # Não precisa de input aqui se o master já tem um
    return