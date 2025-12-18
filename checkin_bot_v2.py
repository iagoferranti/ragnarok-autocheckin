import os
import sys
import json
import time
import random
import datetime
import requests
import textwrap
import ctypes
from premios_manager import carregar_watchlist, normalizar_url
from DrissionPage import ChromiumPage, ChromiumOptions
from DrissionPage.common import Keys


# ==============================================================================
# 📊 MEDIDOR DE CONSUMO DE DADOS
# ==============================================================================
ACUMULADO_MB = 0

def medir_consumo(page, etapa=""):
    """Soma o peso da página atual ao contador global."""
    global ACUMULADO_MB
    try:
        # Script JS que soma o tamanho de HTML + Imagens + CSS + Scripts baixados
        js_script = """
        var total = 0;
        performance.getEntries().forEach(entry => {
            if (entry.transferSize) { total += entry.transferSize; }
        });
        return total;
        """
        bytes_pagina = page.run_js(js_script)
        mb_pagina = bytes_pagina / (1024 * 1024)
        
        ACUMULADO_MB += mb_pagina
        print(f"{Cores.MAGENTA}📊 [Gasto Dados] {etapa}: +{mb_pagina:.3f} MB | Total Sessão: {ACUMULADO_MB:.3f} MB{Cores.RESET}")
    except:
        pass
# ==============================================================================

os.system('') # Cores CMD

# --- CLASSE DE ESTILO ---
class Cores:
    RESET = '\033[0m'
    VERDE = '\033[92m'
    AMARELO = '\033[93m'
    VERMELHO = '\033[91m'
    CIANO = '\033[96m'
    AZUL = '\033[94m'
    MAGENTA = '\033[95m'
    CINZA = '\033[90m'
    NEGRITO = '\033[1m'

# ===== CONFIGURAÇÕES =====
ARQUIVO_HISTORICO = "historico_diario.json"
ARQUIVO_CONFIG = "config.json"
ARQUIVO_CONTAS = "accounts.json"

LOGS_SESSAO = []

SESSION_ID = None
LOG_FILE_PATH = None
PREMIOS_FILE_PATH = None


# --- CONFIG MANAGER ---
def carregar_config():
    padrao = {"headless": False, "telegram_token": "", "telegram_chat_id": ""}
    if not os.path.exists(ARQUIVO_CONFIG): return padrao 
    try:
        with open(ARQUIVO_CONFIG, "r", encoding="utf-8") as f:
            user = json.load(f)
            padrao.update(user)
            return padrao
    except: return padrao

CONF = carregar_config()

# --- VISUAL & LOGS ---
def definir_titulo(texto):
    if os.name == 'nt':
        try: ctypes.windll.kernel32.SetConsoleTitleW(texto)
        except: pass

def exibir_banner_farm():
    print(f"""{Cores.MAGENTA}
    ╔══════════════════════════════════════════════════════════════╗
    ║   🎰  R A G N A R O K   A U T O   F A R M   S Y S T E M  🎰  ║
    ╚══════════════════════════════════════════════════════════════╝
    {Cores.RESET}""")

def log_step(icone, texto, cor=Cores.RESET):
    print(f"   {cor}{icone} {texto}{Cores.RESET}")

def log_debug(texto):
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"      {Cores.CINZA}[DEBUG {timestamp}] {texto}{Cores.RESET}")

def log_sistema(msg): 
    print(f"{Cores.CINZA}    └── {msg}{Cores.RESET}")

def log_sucesso(msg): 
    print(f"{Cores.VERDE} ✅ {Cores.NEGRITO}SUCESSO:{Cores.RESET} {msg}")

def log_aviso(msg): 
    print(f"{Cores.AMARELO} ⚠️  {Cores.NEGRITO}ALERTA:{Cores.RESET} {msg}")

def log_erro(msg): 
    print(f"{Cores.VERMELHO} ❌ {Cores.NEGRITO}ERRO:{Cores.RESET} {msg}")

# --- UTILITÁRIOS ---
def get_base_path():
    if getattr(sys, 'frozen', False): return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def registrar_log(email, status, obs=""):
    agora = datetime.datetime.now().strftime("%H:%M:%S")
    linha = f"[{agora}] {email} -> {status} {f'({obs})' if obs else ''}"

    cor_status = Cores.VERDE if status in ["SUCESSO", "JÁ FEITO"] else Cores.VERMELHO
    if status == "EXPIRADO": cor_status = Cores.AMARELO

    icone = "✅" if status in ["SUCESSO", "JÁ FEITO"] else "❌"
    if status == "EXPIRADO": icone = "⚠️"

    print(f"\n   {Cores.NEGRITO}STATUS:{Cores.RESET} {icone} {cor_status}{status}{Cores.RESET}")
    if obs: print(f"   {Cores.CINZA}OBS: {obs}{Cores.RESET}")

    LOGS_SESSAO.append(linha)           # mantém em memória
    append_log_operacional(linha)       # ✅ grava no arquivo A CADA CONTA


def garantir_pastas_logs():
    base_dir = get_base_path()
    logs_dir = os.path.join(base_dir, "logs")

    premios_dir = os.path.join(base_dir, "premios")
    premios_bruto_dir = os.path.join(premios_dir, "bruto")
    premios_filtrado_dir = os.path.join(premios_dir, "filtrado")

    os.makedirs(logs_dir, exist_ok=True)
    os.makedirs(premios_bruto_dir, exist_ok=True)
    os.makedirs(premios_filtrado_dir, exist_ok=True)

    return logs_dir, premios_bruto_dir, premios_filtrado_dir




def parse_escolha_indices(s: str, max_n: int):
    # aceita: "1, 3,6,10" / "1 3 6 10" / "1;3;6;10"
    if not s:
        return []
    s = s.replace(";", ",").replace(" ", ",")
    partes = [p.strip() for p in s.split(",") if p.strip()]
    out = []
    for p in partes:
        if not p.isdigit():
            continue
        i = int(p)
        if 1 <= i <= max_n:
            out.append(i)
    # remove duplicados mantendo ordem
    seen = set()
    out2 = []
    for i in out:
        if i not in seen:
            out2.append(i); seen.add(i)
    return out2


PREMIOS_BRUTO_FILE_PATH = None
PREMIOS_FILTRADO_FILE_PATH = None

def iniciar_sessao_logs():
    global SESSION_ID, LOG_FILE_PATH, PREMIOS_BRUTO_FILE_PATH, PREMIOS_FILTRADO_FILE_PATH

    logs_dir, premios_bruto_dir, premios_filtrado_dir = garantir_pastas_logs()

    if SESSION_ID is None:
        SESSION_ID = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    LOG_FILE_PATH = os.path.join(logs_dir, f"log_execucao_{SESSION_ID}.txt")

    PREMIOS_BRUTO_FILE_PATH = os.path.join(premios_bruto_dir, f"premios_{SESSION_ID}.txt")
    PREMIOS_FILTRADO_FILE_PATH = os.path.join(premios_filtrado_dir, f"premios_filtrados.txt")

    # Header log operacional
    if not os.path.exists(LOG_FILE_PATH) or os.path.getsize(LOG_FILE_PATH) == 0:
        with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
            f.write(f"===== LOG EXECUCAO {SESSION_ID} =====\n")

def append_log_operacional(linha: str):
    """Append a cada conta (não perde log se travar)."""
    try:
        if not LOG_FILE_PATH:
            iniciar_sessao_logs()
        with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
            f.write(linha.rstrip() + "\n")
    except:
        pass

def append_log_premios_bruto(email: str, premios: list, giros_total: int):
    try:
        if not premios:
            return
        if not PREMIOS_BRUTO_FILE_PATH:
            iniciar_sessao_logs()

        # header 1x
        if not os.path.exists(PREMIOS_BRUTO_FILE_PATH) or os.path.getsize(PREMIOS_BRUTO_FILE_PATH) == 0:
            with open(PREMIOS_BRUTO_FILE_PATH, "a", encoding="utf-8") as f:
                f.write(f"===== PREMIOS BRUTO {SESSION_ID} =====\n")

        agora = datetime.datetime.now().strftime("%H:%M:%S")
        premios_txt = " + ".join([p.strip() for p in premios if p and str(p).strip()])
        linha = f"[{agora}] {email} | giros={giros_total} | {premios_txt}"

        with open(PREMIOS_BRUTO_FILE_PATH, "a", encoding="utf-8") as f:
            f.write(linha + "\n")
    except:
        pass


def append_log_premios_filtrado(email: str, premios_filtrados: list, giros_total: int):
    """
    Arquivo ÚNICO (append-only): premios/filtrado/premios_filtrados.txt
    """
    try:
        if not premios_filtrados:
            return
        if not PREMIOS_FILTRADO_FILE_PATH:
            iniciar_sessao_logs()

        # header 1x
        if not os.path.exists(PREMIOS_FILTRADO_FILE_PATH) or os.path.getsize(PREMIOS_FILTRADO_FILE_PATH) == 0:
            with open(PREMIOS_FILTRADO_FILE_PATH, "a", encoding="utf-8") as f:
                f.write("===== PREMIOS FILTRADOS (APPEND-ONLY) =====\n")

        agora = datetime.datetime.now().strftime("%H:%M:%S")
        premios_txt = " + ".join([p.strip() for p in premios_filtrados if p and str(p).strip()])
        linha = f"[{agora}] {email} | giros={giros_total} | {premios_txt}"

        with open(PREMIOS_FILTRADO_FILE_PATH, "a", encoding="utf-8") as f:
            f.write(linha + "\n")
    except:
        pass




# --- JSON HELPERS ---
def carregar_json_seguro(caminho):
    if not os.path.exists(caminho): return []
    try: 
        with open(caminho, "r", encoding="utf-8") as f: return json.load(f)
    except: return []

def salvar_json_seguro(caminho, dados):
    try: 
        with open(caminho, "w", encoding="utf-8") as f: json.dump(dados, f, indent=4)
    except: pass

def carregar_historico_hoje():
    hoje = datetime.datetime.now().strftime("%Y-%m-%d")
    dados = carregar_json_seguro(ARQUIVO_HISTORICO)
    if isinstance(dados, list): dados = {}
    if dados.get("data") == hoje: return set(dados.get("contas", []))
    return set()

def adicionar_ao_historico(email):
    hoje = datetime.datetime.now().strftime("%Y-%m-%d")
    dados = carregar_json_seguro(ARQUIVO_HISTORICO)
    if isinstance(dados, list): dados = {"data": hoje, "contas": []}
    if dados.get("data") != hoje: dados = {"data": hoje, "contas": []}
    if email not in dados["contas"]:
        dados["contas"].append(email)
        salvar_json_seguro(ARQUIVO_HISTORICO, dados)

def setup_contas():
    path = os.path.join(get_base_path(), ARQUIVO_CONTAS)
    contas = carregar_json_seguro(path)
    if not contas:
        print(f"\n{Cores.AMARELO}⚠️  Nenhuma conta encontrada em '{ARQUIVO_CONTAS}'!{Cores.RESET}")
        return []
    return contas

def verificar_licenca_online(permissao_necessaria="all"):
    try:
        from master import verificar_licenca_online as v
        return v(permissao_necessaria)
    except: return True

# --- INTERAÇÃO HUMANA ---
def digitar_como_humano(page, seletor, texto):
    for tentativa in range(3): # Tenta 3 vezes
        try:
            ele = page.ele(seletor, timeout=2)
            if ele and ele.states.is_displayed:
                ele.click()
                time.sleep(0.3)
                ele.clear()
                time.sleep(0.3)
                #log_debug(f"Digitando '{texto[:2]}***' em {seletor}")
                page.actions.type(texto)
                time.sleep(0.5)
                return True
            else:
                log_debug(f"Elemento {seletor} não visível na tentativa {tentativa+1}")
        except Exception as e:
            #log_debug(f"Erro ao digitar: {e}")
            time.sleep(1.5)
    return False

def interagir_com_seguranca(page, seletor, acao="click", texto=None, timeout=5):
    inicio = time.time()
    while time.time() - inicio < timeout:
        try:
            ele = page.ele(seletor)
            if ele and ele.states.is_displayed: 
                if acao == "click":
                    #log_debug(f"Clicando em {seletor}")
                    ele.click()
                elif acao == "input":
                    return digitar_como_humano(page, seletor, texto)
                return True
        except Exception: 
            time.sleep(0.5) 
    #log_debug(f"Falha ao interagir com {seletor}")
    return False

# --- BROWSER ACTIONS ---
def fechar_cookies(page):
    try:
        if page.ele('.cookieprivacy_btn__Pqz8U', timeout=1): page.ele('.cookieprivacy_btn__Pqz8U').click()
        elif page.ele('text=concordo.', timeout=1): page.ele('text=concordo.').click()
    except: pass

def checar_bloqueio_ip(page):
    try:
        if "429" in page.title or "too many requests" in page.ele('tag:body').text.lower():
            print(f"\n{Cores.VERMELHO}🚨 BLOQUEIO DE IP (429){Cores.RESET}")
            input(f"\n{Cores.VERDE}>>> Troque o IP e pressione ENTER...{Cores.RESET}")
            page.refresh(); time.sleep(5); return True
    except: pass
    return False

# --- CLOUDFLARE "OLHOS DE ÁGUIA" (Portado do Fabricador V4.7) ---
def vencer_cloudflare_obrigatorio(page):
    log_sistema("Verificando Cloudflare...")
    fechar_cookies(page)
    checar_bloqueio_ip(page)
    
    inicio_tentativa = time.time()
    
    while time.time() - inicio_tentativa < 50:
        ele_msg = page.ele('.turnstile_turnstileMessage__grLkv p') or \
                  page.ele('text:Verificação de segurança para acesso concluída') or \
                  page.ele('text:Verificando segurança para acesso')

        status_texto = "Desconhecido"
        if ele_msg and ele_msg.states.is_displayed:
            status_texto = ele_msg.text
            #log_debug(f"Status Visual CF: {status_texto}")

        if "concluída" in status_texto.lower() or "sucesso" in status_texto.lower() or "success" in status_texto.lower():
            log_sucesso("Cloudflare Validado!")
            time.sleep(1) 
            return True

        ele_sucesso_icon = page.ele('.page_success__gilOx')
        if ele_sucesso_icon and ele_sucesso_icon.states.is_displayed:
             #log_debug("Cloudflare: Ícone de sucesso visível.")
             log_sucesso("Cloudflare Validado!")
             return True

        if "verificando" in status_texto.lower() or status_texto == "Desconhecido":
            # log_sistema("Cloudflare pendente. Tentando manobra (Foco Email -> Shift+Tab)...")
            
            if page.ele('#email'):
                try: 
                    page.ele('#email').click()
                    time.sleep(0.2)
                except: pass
            else:
                try: page.ele('tag:body').click()
                except: pass
            
            for _ in range(4):
                page.actions.key_down(Keys.SHIFT).key_down(Keys.TAB).key_up(Keys.TAB).key_up(Keys.SHIFT)
                time.sleep(0.1)
            
            page.actions.key_down(Keys.SPACE).key_up(Keys.SPACE)
            time.sleep(4) 
            continue

        if "insuficiente" in status_texto.lower() or "failed" in status_texto.lower():
            # log_aviso("Cloudflare detectou falha de segurança (Bloqueio). Recarregando página...")
            page.refresh()
            time.sleep(4)
            continue

        time.sleep(1)
    
    log_erro("Timeout no Cloudflare. Não foi possível validar.")
    return False

def garantir_carregamento(page, seletor_esperado, timeout=30):
    # log_debug(f"Aguardando elemento: {seletor_esperado}")
    inicio = time.time()
    while time.time() - inicio < timeout:
        try:
            ele = page.ele(seletor_esperado)
            if ele and ele.states.is_displayed:
                return True
        except: pass 
            
        if checar_bloqueio_ip(page):
            inicio = time.time()
            continue
        
        time.sleep(1)
    return False

# --- FLUXO 1: HOME PAGE ---
def preparar_navegador_home(page):
    try:
        # log_debug("Limpando cookies...")
        page.run_cdp('Network.clearBrowserCookies')
        page.run_cdp('Network.clearBrowserCache')
        
        page.get("https://www.gnjoylatam.com/pt")
        
        try:
            for x in ['.close_btn', '.modal-close', 'text:FECHAR']:
                if page.ele(x, timeout=0.5): page.ele(x).click()
        except: pass

        if not (page.ele('@alt=LOGIN BUTTON', timeout=1) or page.ele('text:Login', timeout=1) or page.ele('.header_rightlist__btn__5cynY', timeout=1)):
             btn_logout = page.ele('.header_logoutBtn__6Pv_m', timeout=2)
             if btn_logout and btn_logout.states.is_displayed:
                log_step("🧹", "Limpando sessão anterior...", Cores.CINZA)
                interagir_com_seguranca(page, '.header_logoutBtn__6Pv_m', "click")
                time.sleep(2)
        # else:
            # log_debug("Sessão limpa.")

    except: pass

# --- FLUXO 2: PEGAR URL ---
def descobrir_url_evento(page):
    path = os.path.join(get_base_path(), "config_evento.json")
    if os.path.exists(path):
        try:
            d = json.load(open(path)); 
            if time.time() - d.get("ts", 0) < 86400: return d['url']
        except: pass
        
    log_step("🔍", "Buscando Evento...", Cores.CIANO)
    url_encontrada = None
    
    btn = page.ele('text=Máquina PonPon', timeout=5) or page.ele('text:PonPon', timeout=2)
    if not btn: 
        btn = page.ele('css:a[href*="roulette"]', timeout=2) or page.ele('css:a[href*="event"]', timeout=2)

    if btn:
        l = btn.attr('href')
        url_encontrada = l if l.startswith('http') else "https://www.gnjoylatam.com" + l
        log_step("🎯", f"URL: {url_encontrada}", Cores.VERDE)
        
    if not url_encontrada:
        url_encontrada = input(f"{Cores.AMARELO}Link não achado. Cole aqui: {Cores.RESET}").strip()
        
    try: json.dump({"url": url_encontrada, "ts": time.time()}, open(path, "w"))
    except: pass
    
    return url_encontrada


# --- FLUXO 4: ROLETA ---
def processar_roleta(page):
    premios = []
    giros_total = 0

    try:
        page.scroll.to_bottom()
        if not page.wait.ele_displayed('.styles_attempts_count__iHKXy', timeout=10):
            return [], 0

        try:
            qtd = int(page.ele('.styles_attempts_count__iHKXy').text)
        except:
            qtd = 0

        giros_total = qtd
        if qtd > 0:
            log_step("🎟️", f"Giros: {qtd}", Cores.AMARELO)

        while qtd > 0:
            if not interagir_com_seguranca(page, '@alt=Start', "click"):
                break
            time.sleep(1)

            alerta = page.handle_alert(accept=True)
            if alerta:
                print(f"      {Cores.AMARELO}⚠️ Alerta: {alerta}{Cores.RESET}")
                break

            if page.wait.ele_displayed('.styles_prize_object__LLDTh', timeout=20):
                nm = (page.ele('.styles_prize_object__LLDTh').text or "").strip()
                if nm:
                    print(f"      {Cores.MAGENTA}★ PRÊMIO: {Cores.NEGRITO}{nm}{Cores.RESET}")
                    premios.append(nm)

                time.sleep(2)
                interagir_com_seguranca(page, '.styles_roulette_btn_close__GzdeD', "click")
            else:
                break

            try:
                qtd = int(page.ele('.styles_attempts_count__iHKXy').text)
            except:
                break

    except:
        pass

    return premios, giros_total


# --- FLUXO PRINCIPAL DE CONTA ---
def processar(page, conta, url, index, total):
    email = conta['email']
    definir_titulo(f"Farm | {index}/{total} | {email}")
    
    txt = f" 👤 CONTA {str(index).zfill(2)}/{str(total).zfill(2)}: {email} "
    w = max(len(txt), 60)
    print(f"\n{Cores.AZUL}┌{'─'*w}┐")
    print(f"│{Cores.RESET}{txt}{' '*(w-len(txt))}{Cores.AZUL}│")
    print(f"└{'─'*w}┘{Cores.RESET}")
    
    sucesso_conta = False
    log_st = "ERRO" 
    msg = ""
    
    try:
        preparar_navegador_home(page)
        page.get(url)
        time.sleep(2)
        checar_bloqueio_ip(page)

        # CHECK DE LOGIN NO EVENTO
        if page.ele('@alt=LOGIN BUTTON') or page.ele('text:Login'):
            # log_debug("Botão de Login encontrado. Iniciando processo...")
            
            if interagir_com_seguranca(page, '@alt=LOGIN BUTTON', "click") or interagir_com_seguranca(page, 'text:Login', "click"):
                # log_debug("Botão clicado. Esperando formulário...")
                
                if garantir_carregamento(page, '#email', timeout=40):
                    # log_debug("Formulário carregado.")
                    
                    # --- AQUI ESTÁ A CORREÇÃO: OBRIGA O CLOUDFLARE A PASSAR ANTES DE DIGITAR ---
                    if not vencer_cloudflare_obrigatorio(page):
                        log_st = "ERRO CF"
                        log_step("❌", "Falha no Cloudflare", Cores.VERMELHO)
                        raise Exception("Falha Cloudflare")

                    # AGORA DIGITA COM SEGURANÇA
                    res_email = digitar_como_humano(page, '#email', email)
                    res_senha = digitar_como_humano(page, '#password', conta['password'])
                    
                    if res_email and res_senha:
                        time.sleep(1)
                        try: page.ele('text=Entrar').click() # Tira foco
                        except: pass
                        
                        # log_debug("Enviando Login...")
                        
                        # Tenta clicar no botão específico ou dar Enter
                        clicou_login = False
                        if interagir_com_seguranca(page, '.page_loginBtn__JUYeS', "click"): clicou_login = True
                        elif interagir_com_seguranca(page, 'text=CONTINUAR', "click"): clicou_login = True
                        
                        if not clicou_login:
                             page.actions.key_down(Keys.ENTER).key_up(Keys.ENTER)
                        
                        # VERIFICA ERROS ANTES DE ESPERAR LOGOUT
                        time.sleep(3)
                        erro_login = page.ele('.input_errorMsg__hM_98') or page.ele('text:A segurança para acesso é insuficiente')
                        if erro_login and erro_login.states.is_displayed:
                             log_st = "FALHA AUTH"
                             log_step("❌", f"Erro no site: {erro_login.text}", Cores.VERMELHO)
                             return False

                        # log_debug("Aguardando confirmação de login...")
                        if garantir_carregamento(page, 'text:Logout', timeout=60):
                            log_step("🔓", "Login Efetuado", Cores.VERDE)
                            
                            if "event" not in page.url: 
                                page.get(url); time.sleep(3)
                            
                            # CHECK-IN
                            page.scroll.to_bottom()
                            btn_check = page.ele('tag:img@@alt=attendance button')
                            if not btn_check: 
                                btn_check = page.ele('text:FAZER CHECK-IN')

                            if btn_check:
                                if "complete" in str(btn_check.attr("src")):
                                    log_st = "JÁ FEITO"
                                    log_step("📅", "Check-in já feito hoje", Cores.AMARELO)
                                    sucesso_conta = True
                                else:
                                    btn_check.click()
                                    time.sleep(1)

                                    alerta = page.handle_alert(accept=True)
                                    if alerta:
                                        log_step("⚠️", f"Aviso: {alerta}", Cores.AMARELO)
                                        if "período" in alerta.lower() or "not" in alerta.lower():
                                            log_st = "EXPIRADO"; msg = alerta
                                        else:
                                            log_st = "ALERTA"; msg = alerta
                                    else:
                                        time.sleep(2)
                                        log_st = "SUCESSO"
                                        log_step("📅", "Check-in realizado!", Cores.VERDE)
                                        sucesso_conta = True

                            # ✅ ROLETA (sempre tenta rodar, mesmo se já tinha feito check-in)
                            premios, giros_total = processar_roleta(page)

                            # ✅ LOG BRUTO (só grava se tiver prêmio)
                            append_log_premios_bruto(email, premios, giros_total)

                            # ✅ LOG FILTRADO (só grava se tiver match com watchlist do mesmo evento)
                            wl = carregar_watchlist()
                            url_norm = normalizar_url(url)
                            wl_url = normalizar_url((wl or {}).get("event_url", ""))

                            premios_filtrados = []
                            if wl and wl_url and wl_url == url_norm:
                                alvo = set((wl.get("selected") or []))
                                premios_filtrados = [p for p in premios if p in alvo]

                            append_log_premios_filtrado(email, premios_filtrados, giros_total)

                            # msg operacional (consistente)
                            if premios_filtrados:
                                msg = f"ROULETA: {giros_total} giros | " + " + ".join(premios_filtrados)



                            
                            log_step("👋", "Saindo da conta...", Cores.CINZA)
                            interagir_com_seguranca(page, 'text:Logout', "click")
                            page.wait.ele_displayed('@alt=LOGIN BUTTON', timeout=15)
                            
                        else:
                            log_st = "FALHA LOGIN"
                            log_step("❌", "Não logou (Timeout)", Cores.VERMELHO)
                    else:
                         log_st = "ERRO DIGITACAO"
                else:
                    log_st = "ERRO SSO"
                    log_step("❌", "Formulário não carregou", Cores.VERMELHO)
        
        elif page.ele('text:Logout') or page.ele('.page_login__g41B0'):
            log_step("⚠️", "Já estava logado. Considere limpar cookies.", Cores.AMARELO)
            interagir_com_seguranca(page, 'text:Logout', "click")
            
        else:
             log_st = "ERRO NAV"
             log_step("❌", "Estado da página desconhecido", Cores.VERMELHO)

    except Exception as e:
        msg = str(e)
        log_debug(f"Exception: {e}")
    
    registrar_log(email, log_st, msg)
    if sucesso_conta: adicionar_ao_historico(email)
    
    return sucesso_conta 

def main():
    if not verificar_licenca_online("checkin"): return
    os.system('cls' if os.name == 'nt' else 'clear')
    exibir_banner_farm()
    
    contas = setup_contas()
    if not contas: return

    print(f"\n{Cores.CINZA}>>> Inicializando Motor Gráfico...{Cores.RESET}")
    co = ChromiumOptions()
    co.set_argument('--start-maximized') 
    co.set_argument('--window-size=1920,1080')
    if CONF.get("headless", False): co.headless(True)
    
    page = ChromiumPage(addr_or_opts=co)
    try: page.set.window.max()
    except: pass

    iniciar_sessao_logs()

    url = descobrir_url_evento(page)
    ja_foi = carregar_historico_hoje()
    
    contas_para_fazer = [c for c in contas if c['email'] not in ja_foi]
    print(f"{Cores.CIANO}📊 RESUMO:{Cores.RESET} Total: {len(contas)} | Pendentes: {len(contas_para_fazer)} | Feitos: {len(ja_foi)}")
    time.sleep(2)
    
    count_sucesso = 0
    for i, acc in enumerate(contas_para_fazer):
        if processar(page, acc, url, i+1, len(contas_para_fazer)):
            count_sucesso += 1
            
        if i < len(contas_para_fazer) - 1:
            t = random.randint(5, 12)
            print(f"\n{Cores.CINZA}⏳ Aguardando {t}s...{Cores.RESET}")
            time.sleep(t)
        
    msg = f"FARM FINALIZADO - {count_sucesso} SUCESSOS"
    print(f"\n{Cores.VERDE}╔{'═'*(len(msg)+4)}╗\n║  {msg}  ║\n╚{'═'*(len(msg)+4)}╝{Cores.RESET}")

    medir_consumo(page, "Fluxo Check-in Completo")

    # enviar_telegram(msg)
    page.quit()
    input("\nEnter para voltar...")

def executar(): main()

if __name__ == "__main__": main()