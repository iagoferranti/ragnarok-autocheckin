import os
import json
import time
import unicodedata
import re

WATCHLIST_FILE = "premios_watchlist.json"


# =========================================================
# Base path (compatível com EXE PyInstaller)
# =========================================================
def get_base_path():
    import sys
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _watchlist_path():
    return os.path.join(get_base_path(), WATCHLIST_FILE)


def _premios_dir():
    return os.path.join(get_base_path(), "premios")


def _premios_filtrado_dir():
    return os.path.join(_premios_dir(), "filtrado")


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
        if not ln:
            break
        itens.append(ln)

    if not itens:
        print("❌ Nenhum prêmio informado.")
        input("\nEnter...")
        return

    # remove duplicados mantendo ordem (e também guarda versão normalizada)
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

    input("\nEnter para voltar ao menu...")


# =========================================================
# Opção 7 (SYNC INICIAL): ler todos .txt antigos e gerar 1 filtrado
# =========================================================
def gerar_lista_contas_alvo_por_logs():
    """
    Lê TODOS os .txt dentro de /premios (raiz + subpastas),
    e gera /premios/filtrado/premios_filtrados.txt contendo apenas
    as linhas cujo prêmio bate na watchlist.
    """
    wl = carregar_watchlist() or {}
    alvo_norm = set(wl.get("selected_norm") or [normalizar_premio(x) for x in (wl.get("selected") or [])])

    if not alvo_norm:
        raise Exception("Watchlist vazia. Configure no Menu 6 antes.")

    base = _premios_dir()
    if not os.path.exists(base):
        raise Exception(f"Pasta de prêmios não encontrada: {base}")

    # garante pasta de saída
    os.makedirs(_premios_filtrado_dir(), exist_ok=True)
    out_path = _premios_filtrado_file()

    # coleta TODOS .txt em /premios (inclui raiz, bruto, filtrado etc.)
    txts = []
    for root, _, files in os.walk(base):
        for fn in files:
            if fn.lower().endswith(".txt"):
                full = os.path.join(root, fn)
                # evita ler o próprio arquivo final (se já existir)
                if os.path.abspath(full) == os.path.abspath(out_path):
                    continue
                txts.append(full)

    if not txts:
        raise Exception(f"Não encontrei .txt em: {base}")

    linhas_match = []
    total_lidas = 0

    # regra simples: uma linha “válida” costuma ter: "] email | giros=" e " | "
    # seu log real tem esse formato (ex.: “10X PASSAPORTE”, “2X BÊNÇÃO DO FERREIRO”). :contentReference[oaicite:0]{index=0}
    for path in sorted(txts):
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    s = line.strip()
                    if not s:
                        continue
                    if s.startswith("====="):
                        continue
                    total_lidas += 1

                    # tenta extrair “parte do prêmio” depois do último " | "
                    # exemplo: "[00:13:25] email | giros=1 | 2X BÊNÇÃO DO FERREIRO" :contentReference[oaicite:1]{index=1}
                    if " | " not in s:
                        continue
                    premio = s.split(" | ")[-1].strip()
                    if normalizar_premio(premio) in alvo_norm:
                        linhas_match.append(s)
        except:
            continue

    # grava (sobrescreve) o SYNC inicial
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("===== PREMIOS FILTRADOS (SYNC INICIAL) =====\n")
        f.write(f"gerado_em_epoch={int(time.time())}\n")
        f.write(f"watchlist_itens={len(alvo_norm)}\n")
        f.write(f"arquivos_lidos={len(txts)}\n")
        f.write(f"linhas_lidas={total_lidas}\n")
        f.write(f"matches={len(linhas_match)}\n")
        f.write("-----\n")
        for l in linhas_match:
            f.write(l + "\n")

    return out_path, len(txts), total_lidas, len(linhas_match)
