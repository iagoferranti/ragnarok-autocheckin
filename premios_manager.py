import os, re, json, time, datetime

WATCHLIST_FILE = "premios_watchlist.json"

def get_base_path():
    import sys
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def _path_watchlist():
    return os.path.join(get_base_path(), WATCHLIST_FILE)

def carregar_watchlist():
    p = _path_watchlist()
    if not os.path.exists(p):
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            wl = json.load(f)
        return wl if isinstance(wl, dict) else None
    except:
        return None

def _premios_dir():
    return os.path.join(get_base_path(), "premios")

def _relatorios_dir():
    d = os.path.join(_premios_dir(), "relatorios")
    os.makedirs(d, exist_ok=True)
    return d

def _listar_logs_premios():
    d = _premios_dir()
    if not os.path.exists(d):
        return []
    files = []
    for fn in os.listdir(d):
        if fn.lower().endswith(".txt") and fn.lower().startswith("premios_"):
            files.append(os.path.join(d, fn))
    # mais recentes primeiro (ajuda a pegar “último status”)
    files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return files

def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())

def gerar_lista_contas_alvo_por_logs():
    wl = carregar_watchlist()
    if not wl or not (wl.get("selected") or []):
        print("❌ Watchlist não configurada. Use o menu 6 antes.")
        input("\nEnter...")
        return

    desejados = [_norm(x) for x in (wl.get("selected") or []) if str(x).strip()]
    if not desejados:
        print("❌ Watchlist vazia.")
        input("\nEnter...")
        return

    logs = _listar_logs_premios()
    if not logs:
        print("❌ Não encontrei logs em /premios. Rode o farm ao menos uma vez.")
        input("\nEnter...")
        return

    # email -> {itens:set, ocorrencias:[...]}
    achados = {}

    # regex do seu formato
    rx = re.compile(r"^\[(\d{2}:\d{2}:\d{2})\]\s+(.+?)\s+\|\s+giros=(\d+)\s+\|\s+(.+)$")

    for path in logs:
        base = os.path.basename(path)
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("====="):
                        continue
                    m = rx.match(line)
                    if not m:
                        continue
                    hhmmss, email, giros, premios_txt = m.groups()
                    premios_lista = [p.strip() for p in premios_txt.split("+") if p.strip()]
                    premios_norm = [_norm(p) for p in premios_lista]

                    # checa se algum prêmio da linha está na watchlist
                    hits = []
                    for p_raw, p_n in zip(premios_lista, premios_norm):
                        if p_n in desejados:
                            hits.append(p_raw)

                    if not hits:
                        continue

                    email_key = email.strip().lower()
                    if email_key not in achados:
                        achados[email_key] = {"email": email.strip(), "itens": set(), "ocorrencias": []}

                    for h in hits:
                        achados[email_key]["itens"].add(h)

                    achados[email_key]["ocorrencias"].append({
                        "arquivo": base,
                        "hora": hhmmss,
                        "giros": int(giros),
                        "hits": hits,
                        "linha": line,
                    })
        except:
            pass

    if not achados:
        print("⚠️ Nenhuma conta com os prêmios desejados foi encontrada nos logs.")
        input("\nEnter...")
        return

    # gera relatório
    ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    out_dir = _relatorios_dir()
    out_txt = os.path.join(out_dir, f"alvos_{ts}.txt")
    out_csv = os.path.join(out_dir, f"alvos_{ts}.csv")

    # ordena por qtd de itens encontrados (desc)
    lista = list(achados.values())
    lista.sort(key=lambda d: len(d["itens"]), reverse=True)

    with open(out_txt, "w", encoding="utf-8") as f:
        f.write(f"ALVOS GERADOS EM {ts}\n")
        f.write(f"Watchlist: {', '.join(wl.get('selected') or [])}\n")
        f.write("="*70 + "\n\n")

        for d in lista:
            f.write(f"EMAIL: {d['email']}\n")
            f.write(f"PRÊMIOS (match): {', '.join(sorted(d['itens']))}\n")
            # mostra 1 ocorrência mais recente
            if d["ocorrencias"]:
                oc = d["ocorrencias"][0]
                f.write(f"ÚLTIMA OCORRÊNCIA: {oc['arquivo']} [{oc['hora']}] giros={oc['giros']} -> {', '.join(oc['hits'])}\n")
            f.write("-"*70 + "\n")

    # CSV simples
    with open(out_csv, "w", encoding="utf-8") as f:
        f.write("email,qtde_itens,itens\n")
        for d in lista:
            itens = " | ".join(sorted(d["itens"])).replace('"', '""')
            f.write(f"\"{d['email']}\",{len(d['itens'])},\"{itens}\"\n")

    print(f"\n✅ Lista gerada com sucesso!")
    print(f"📄 TXT: {out_txt}")
    print(f"📄 CSV: {out_csv}")
    print(f"🎯 Contas-alvo encontradas: {len(lista)}")
    input("\nEnter...")
