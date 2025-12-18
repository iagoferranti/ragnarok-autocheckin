import os
import json
import time
import unicodedata
import re
from datetime import datetime

WATCHLIST_FILE = "premios_watchlist.json"


def get_base_path():
    import sys
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _watchlist_path():
    return os.path.join(get_base_path(), WATCHLIST_FILE)


def normalizar_premio(txt: str) -> str:
    if not txt:
        return ""
    txt = txt.strip().lower()
    txt = unicodedata.normalize("NFKD", txt)
    txt = "".join(c for c in txt if not unicodedata.combining(c))
    txt = re.sub(r"\s+", " ", txt)
    return txt


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


def _premios_root_dir():
    return os.path.join(get_base_path(), "premios")


def _filtrado_dir():
    d = os.path.join(_premios_root_dir(), "filtrado")
    os.makedirs(d, exist_ok=True)
    return d


def _filtrado_output_path():
    return os.path.join(_filtrado_dir(), "premios_filtrados.txt")


def _iterar_txts_recursivo(pasta: str):
    for root, _, files in os.walk(pasta):
        for fn in files:
            if fn.lower().endswith(".txt"):
                yield os.path.join(root, fn)


def _parse_premios_da_linha(linha: str):
    """
    Extrai a parte de prêmios, assumindo padrão:
      [..] email | giros=X | premio1 + premio2 + ...
    Retorna lista de prêmios (strings) ou [] se não bater.
    """
    try:
        m = re.search(r"\|\s*giros\s*=\s*\d+\s*\|\s*(.+)$", linha.strip())
        if not m:
            return []
        premios_txt = m.group(1).strip()
        if not premios_txt:
            return []
        return [p.strip() for p in premios_txt.split("+") if p.strip()]
    except:
        return []
    

def gerar_lista_contas_alvo_por_logs():
    """
    OPÇÃO 7
    Lê todos os logs antigos de prêmios e gera UM arquivo filtrado
    com base na watchlist atual.
    Executar apenas uma vez para sincronização.
    """

    base_dir = get_base_path()

    premios_dir = os.path.join(base_dir, "premios")
    filtrado_dir = os.path.join(premios_dir, "filtrado")
    os.makedirs(filtrado_dir, exist_ok=True)

    output_path = os.path.join(filtrado_dir, "premios_filtrados.txt")

    wl = carregar_watchlist()
    if not wl or not wl.get("selected"):
        print("⚠️ Watchlist vazia. Configure os prêmios primeiro.")
        input("\nEnter...")
        return

    alvo_norm = set(normalizar_premio(x) for x in wl["selected"])

    # evita duplicar linhas
    linhas_existentes = set()
    if os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            for ln in f:
                linhas_existentes.add(ln.strip())

    total_lidas = 0
    total_gravadas = 0

    for fname in os.listdir(premios_dir):
        if not fname.lower().endswith(".txt"):
            continue

        path = os.path.join(premios_dir, fname)
        if not os.path.isfile(path):
            continue

        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for ln in f:
                ln = ln.strip()
                if not ln.startswith("["):
                    continue

                total_lidas += 1

                # pega texto depois do último |
                try:
                    premio_txt = ln.split("|")[-1].strip()
                except:
                    continue

                if normalizar_premio(premio_txt) in alvo_norm:
                    if ln not in linhas_existentes:
                        with open(output_path, "a", encoding="utf-8") as out:
                            out.write(ln + "\n")
                        linhas_existentes.add(ln)
                        total_gravadas += 1

    print("\n✅ SINCRONIZAÇÃO FINALIZADA")
    print(f"📄 Linhas analisadas: {total_lidas}")
    print(f"🎯 Linhas adicionadas ao filtrado: {total_gravadas}")
    print(f"📂 Arquivo final: {output_path}")

    input("\nEnter para voltar ao menu...")



def sync_filtrado_inicial_por_watchlist():
    """
    OPÇÃO 7:
    - Lê TODOS os .txt dentro de /premios (recursivo)
    - Filtra linhas que contenham qualquer prêmio da watchlist
    - Gera UM arquivo único: /premios/filtrado/premios_filtrados.txt
    - Recria do zero (sync inicial)
    """
    wl = carregar_watchlist() or {}
    selected = wl.get("selected") or []
    alvo_norm = set(wl.get("selected_norm") or [normalizar_premio(x) for x in selected])

    if not alvo_norm:
        print("⚠️ Sua watchlist está vazia. Use o menu 6 antes.")
        input("\nEnter...")
        return

    premios_dir = _premios_root_dir()
    if not os.path.exists(premios_dir):
        print("⚠️ Pasta /premios não existe ainda.")
        input("\nEnter...")
        return

    # pega todos txt dentro de /premios
    arquivos = list(_iterar_txts_recursivo(premios_dir))

    # IMPORTANTÍSSIMO: evita ler o próprio filtrado antigo, se existir
    out_path = _filtrado_output_path()
    arquivos = [a for a in arquivos if os.path.abspath(a) != os.path.abspath(out_path)]

    if not arquivos:
        print("⚠️ Não achei nenhum .txt dentro da pasta /premios.")
        input("\nEnter...")
        return

    linhas_match = []
    vistos = set()  # remove duplicados exatos

    for arq in arquivos:
        try:
            with open(arq, "r", encoding="utf-8", errors="ignore") as f:
                for ln in f:
                    lns = ln.strip()
                    if not lns:
                        continue
                    # pula headers tipo ===== PREMIOS ...
                    if lns.startswith("====="):
                        continue

                    premios = _parse_premios_da_linha(lns)
                    if not premios:
                        continue

                    # se qualquer prêmio da linha bater na watchlist -> mantém a LINHA INTEIRA
                    ok = False
                    for p in premios:
                        if normalizar_premio(p) in alvo_norm:
                            ok = True
                            break

                    if ok:
                        key = lns
                        if key not in vistos:
                            vistos.add(key)
                            linhas_match.append(lns)
        except:
            pass

    if not linhas_match:
        print("ℹ️ Nenhuma linha antiga bateu com a watchlist (ainda).")
        input("\nEnter...")
        return

    # escreve do zero (sync inicial)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("===== PREMIOS FILTRADOS (SYNC INICIAL) =====\n")
        f.write(f"Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total de linhas: {len(linhas_match)}\n")
        f.write("\n")
        for ln in linhas_match:
            f.write(ln + "\n")

    print("\n✅ Sync concluído!")
    print(f"📄 Arquivo gerado: {out_path}")
    print(f"🎯 Linhas filtradas: {len(linhas_match)}")
    input("\nEnter para voltar...")
