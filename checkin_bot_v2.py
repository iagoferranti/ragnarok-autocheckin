import os
import sys
import json
import time
import random
import datetime
import ctypes
from DrissionPage import ChromiumPage, ChromiumOptions
from DrissionPage.common import Keys

# === INTEGRAÇÃO MODULAR CORRIGIDA ===
from fabricador import config
from fabricador.modules.logger import (
    Cores, log_sucesso, log_erro, log_aviso, log_info, log_debug, log_sistema
)
# Funções de navegação
from fabricador.modules.browser import (
    clicar_com_seguranca,
    garantir_carregamento,
    medir_consumo
)
# Funções de segurança (O ERRO ESTAVA AQUI, AGORA ESTÁ CORRIGIDO)
from fabricador.modules.cloudflare_solver import (
    vencer_cloudflare_obrigatorio,
    checar_bloqueio_ip,
    fechar_cookies
)
from fabricador.modules.files import (
    carregar_json_seguro,
    salvar_json_seguro
)

# === IMPORTAÇÃO OPCIONAL DE PRÊMIOS ===
try:
    from premios_manager import carregar_watchlist, normalizar_premio
    TEM_PREMIOS = True
except ImportError:
    TEM_PREMIOS = False

# ===== VARIÁVEIS GLOBAIS =====
ARQUIVO_HISTORICO = "historico_diario.json"
LOGS_SESSAO = []
SESSION_ID = None
LOG_FILE_PATH = None
PREMIOS_BRUTO_FILE_PATH = None
PREMIOS_FILTRADO_FILE_PATH = None

# --- VISUAL ---
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

# --- LOGS ESPECÍFICOS DE FARM ---
def log_step(icone, texto, cor=Cores.RESET):
    print(f"   {cor}{icone} {texto}{Cores.RESET}")

def registrar_log(email, status, obs=""):
    """Registra o resultado final de uma conta no log e na tela."""
    agora = datetime.datetime.now().strftime("%H:%M:%S")
    linha = f"[{agora}] {email} -> {status} {f'({obs})' if obs else ''}"

    cor_status = Cores.VERDE if status in ["SUCESSO", "JÁ FEITO"] else Cores.VERMELHO
    if status == "EXPIRADO": cor_status = Cores.AMARELO

    icone = "✅" if status in ["SUCESSO", "JÁ FEITO"] else "❌"
    if status == "EXPIRADO": icone = "⚠️"

    print(f"\n   {Cores.NEGRITO}STATUS:{Cores.RESET} {icone} {cor_status}{status}{Cores.RESET}")
    if obs: print(f"   {Cores.CINZA}OBS: {obs}{Cores.RESET}")

    LOGS_SESSAO.append(linha)
    append_log_operacional(linha)

# --- SISTEMA DE ARQUIVOS DE LOG ---
def get_base_path():
    if getattr(sys, 'frozen', False): return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def garantir_pastas_logs():
    base_dir = get_base_path()
    logs_dir = os.path.join(base_dir, "logs")
    premios_dir = os.path.join(base_dir, "premios")
    os.makedirs(logs_dir, exist_ok=True)
    os.makedirs(os.path.join(premios_dir, "bruto"), exist_ok=True)
    os.makedirs(os.path.join(premios_dir, "filtrado"), exist_ok=True)
    return logs_dir, os.path.join(premios_dir, "bruto"), os.path.join(premios_dir, "filtrado")

def iniciar_sessao_logs():
    global SESSION_ID, LOG_FILE_PATH, PREMIOS_BRUTO_FILE_PATH, PREMIOS_FILTRADO_FILE_PATH
    logs_dir, pb_dir, pf_dir = garantir_pastas_logs()

    if SESSION_ID is None:
        SESSION_ID = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    LOG_FILE_PATH = os.path.join(logs_dir, f"log_execucao_{SESSION_ID}.txt")
    PREMIOS_BRUTO_FILE_PATH = os.path.join(pb_dir, f"premios_{SESSION_ID}.txt")
    PREMIOS_FILTRADO_FILE_PATH = os.path.join(pf_dir, "premios_filtrados.txt")

    if not os.path.exists(LOG_FILE_PATH):
        with open(LOG_FILE_PATH, "w", encoding="utf-8") as f:
            f.write(f"===== LOG EXECUCAO {SESSION_ID} =====\n")

def append_log_operacional(linha):
    if not LOG_FILE_PATH: iniciar_sessao_logs()
    try:
        with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
            f.write(linha.rstrip() + "\n")
    except: pass

def append_log_premios_bruto(email, premios, giros):
    if not premios: return
    if not PREMIOS_BRUTO_FILE_PATH: iniciar_sessao_logs()
    try:
        agora = datetime.datetime.now().strftime("%H:%M:%S")
        premios_txt = " + ".join([str(p).strip() for p in premios if p])
        linha = f"[{agora}] {email} | giros={giros} | {premios_txt}"
        with open(PREMIOS_BRUTO_FILE_PATH, "a", encoding="utf-8") as f:
            f.write(linha + "\n")
    except: pass

def append_log_premios_filtrado(email, premios, giros):
    if not premios: return
    if not PREMIOS_FILTRADO_FILE_PATH: iniciar_sessao_logs()
    try:
        agora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        premios_txt = " + ".join(premios)
        linha = f"[{agora}] {email} | giros={giros} | {premios_txt}"
        with open(PREMIOS_FILTRADO_FILE_PATH, "a", encoding="utf-8") as f:
            f.write(linha + "\n")
    except: pass

# --- GERENCIAMENTO DE HISTÓRICO ---
def carregar_historico_hoje():
    hoje = datetime.datetime.now().strftime("%Y-%m-%d")
    dados = carregar_json_seguro(ARQUIVO_HISTORICO)
    if isinstance(dados, list): dados = {} 
    if dados.get("data") == hoje: 
        return set(dados.get("contas", []))
    return set()

def adicionar_ao_historico(email):
    hoje = datetime.datetime.now().strftime("%Y-%m-%d")
    dados = carregar_json_seguro(ARQUIVO_HISTORICO)
    
    if isinstance(dados, list) or dados.get("data") != hoje: 
        dados = {"data": hoje, "contas": []}
    
    if email not in dados["contas"]:
        dados["contas"].append(email)
        salvar_json_seguro(ARQUIVO_HISTORICO, dados)

# --- INTERAÇÃO HUMANA ---
def digitar_como_humano(page, seletor, texto):
    """Digita devagar para parecer humano."""
    for _ in range(3):
        try:
            ele = page.ele(seletor, timeout=2)
            if ele:
                ele.click()
                time.sleep(0.3)
                ele.clear()
                time.sleep(0.3)
                page.actions.type(texto) # DrissionPage type é seguro
                time.sleep(0.5)
                return True
        except: time.sleep(1)
    return False

# --- LÓGICA DE NEGÓCIO (HOME & URL) ---
def preparar_navegador_home(page):
    """Limpa a sessão e vai para a home."""
    try:
        page.run_cdp('Network.clearBrowserCookies')
        page.run_cdp('Network.clearBrowserCache')
        
        page.get("https://www.gnjoylatam.com/pt")
        
        # Fecha modais chatos
        for x in ['.close_btn', '.modal-close', 'text:FECHAR']:
            if page.ele(x, timeout=0.5): page.ele(x).click()

        # Garante logout se ainda estiver logado
        if not (page.ele('@alt=LOGIN BUTTON', timeout=1) or page.ele('text:Login', timeout=1)):
             btn_logout = page.ele('.header_logoutBtn__6Pv_m', timeout=2)
             if btn_logout:
                log_step("🧹", "Limpando sessão anterior...", Cores.CINZA)
                try: btn_logout.click()
                except: page.run_js("arguments[0].click()", btn_logout)
                time.sleep(2)
    except: pass

def descobrir_url_evento(page):
    """Tenta descobrir a URL do evento PonPon/Roleta automaticamente."""
    path = os.path.join(get_base_path(), "config_evento.json")
    
    # Cache de 24h
    if os.path.exists(path):
        try:
            d = json.load(open(path))
            if time.time() - d.get("ts", 0) < 86400: return d['url']
        except: pass
        
    log_step("🔍", "Buscando Evento...", Cores.CIANO)
    url_encontrada = None
    
    btn = page.ele('text=Máquina PonPon', timeout=5) or \
          page.ele('text:PonPon', timeout=2) or \
          page.ele('css:a[href*="roulette"]', timeout=2) or \
          page.ele('css:a[href*="event"]', timeout=2)

    if btn:
        l = btn.attr('href')
        url_encontrada = l if l.startswith('http') else "https://www.gnjoylatam.com" + l
        log_step("🎯", f"URL: {url_encontrada}", Cores.VERDE)
        
    if not url_encontrada:
        url_encontrada = input(f"{Cores.AMARELO}Link não achado. Cole aqui: {Cores.RESET}").strip()
        
    try: json.dump({"url": url_encontrada, "ts": time.time()}, open(path, "w"))
    except: pass
    
    return url_encontrada

# --- LÓGICA DA ROLETA ---
def processar_roleta(page):
    premios = []
    giros_total = 0

    try:
        page.scroll.to_bottom()
        if not page.wait.ele_displayed('.styles_attempts_count__iHKXy', timeout=10):
            return [], 0

        try: qtd = int(page.ele('.styles_attempts_count__iHKXy').text)
        except: qtd = 0

        giros_total = qtd
        if qtd > 0: log_step("🎟️", f"Giros: {qtd}", Cores.AMARELO)

        while qtd > 0:
            if not clicar_com_seguranca(page, '@alt=Start', "Girar Roleta"):
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
                clicar_com_seguranca(page, '.styles_roulette_btn_close__GzdeD', "Fechar Prêmio")
            else:
                break

            try: qtd = int(page.ele('.styles_attempts_count__iHKXy').text)
            except: break

    except: pass
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

        # LOGIN NO EVENTO
        if page.ele('@alt=LOGIN BUTTON') or page.ele('text:Login'):
            
            if clicar_com_seguranca(page, '@alt=LOGIN BUTTON', "Login") or \
               clicar_com_seguranca(page, 'text:Login', "Login Texto"):
                
                if garantir_carregamento(page, '#email', timeout=40):
                    
                    # === OBRIGA CLOUDFLARE (DO MÓDULO BLINDADO) ===
                    if not vencer_cloudflare_obrigatorio(page):
                        log_st = "ERRO CF"
                        log_step("❌", "Falha no Cloudflare", Cores.VERMELHO)
                        raise Exception("Falha Cloudflare")

                    # DIGITAÇÃO HUMANA
                    res_email = digitar_como_humano(page, '#email', email)
                    res_senha = digitar_como_humano(page, '#password', conta['password'])
                    
                    if res_email and res_senha:
                        time.sleep(1)
                        try: page.ele('text=Entrar').click() # Tira foco
                        except: pass
                        
                        # CLICA EM ENTRAR
                        clicou = False
                        if clicar_com_seguranca(page, '.page_loginBtn__JUYeS', "Entrar"): clicou = True
                        elif clicar_com_seguranca(page, 'text=CONTINUAR', "Continuar"): clicou = True
                        
                        if not clicou:
                             page.actions.key_down(Keys.ENTER).key_up(Keys.ENTER)
                        
                        time.sleep(3)
                        # Checa erro
                        erro = page.ele('.input_errorMsg__hM_98') or page.ele('text:A segurança para acesso é insuficiente')
                        if erro and erro.states.is_displayed:
                             log_st = "FALHA AUTH"
                             log_step("❌", f"Erro: {erro.text}", Cores.VERMELHO)
                             return False

                        if garantir_carregamento(page, 'text:Logout', timeout=60):
                            log_step("🔓", "Login Efetuado", Cores.VERDE)
                            
                            if "event" not in page.url: 
                                page.get(url); time.sleep(3)
                            
                            # CHECK-IN
                            page.scroll.to_bottom()
                            btn_check = page.ele('tag:img@@alt=attendance button') or page.ele('text:FAZER CHECK-IN')

                            if btn_check:
                                if "complete" in str(btn_check.attr("src") or ""):
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

                            # ROLETA
                            premios, giros_total = processar_roleta(page)
                            append_log_premios_bruto(email, premios, giros_total)

                            # FILTRAGEM DE PRÊMIOS (SE TIVER MODULO)
                            if TEM_PREMIOS:
                                wl = carregar_watchlist() or {}
                                alvo_norm = set(wl.get("selected_norm") or [normalizar_premio(x) for x in (wl.get("selected") or [])])
                                premios_filtrados = [p for p in premios if normalizar_premio(p) in alvo_norm]
                                append_log_premios_filtrado(email, premios_filtrados, giros_total)
                                if premios_filtrados:
                                    msg = f"ROULETA: {giros_total} giros | " + " + ".join(premios_filtrados)

                            log_step("👋", "Saindo...", Cores.CINZA)
                            clicar_com_seguranca(page, 'text:Logout', "Logout")
                            page.wait.ele_displayed('@alt=LOGIN BUTTON', timeout=15)
                            
                        else:
                            log_st = "FALHA LOGIN"
                            log_step("❌", "Não logou (Timeout)", Cores.VERMELHO)
                    else:
                         log_st = "ERRO DIGITACAO"
                else:
                    log_st = "ERRO SSO"
                    log_step("❌", "Formulário não carregou", Cores.VERMELHO)
        
        elif page.ele('text:Logout'):
            log_step("⚠️", "Já logado. Limpando.", Cores.AMARELO)
            clicar_com_seguranca(page, 'text:Logout', "Logout")
            
        else:
             log_st = "ERRO NAV"

    except Exception as e:
        msg = str(e)
        log_debug(f"Exception: {e}")
    
    registrar_log(email, log_st, msg)
    if sucesso_conta: adicionar_ao_historico(email)
    
    return sucesso_conta 

def main():
    if not config.CONF: config.carregar_user_config()
    
    # Stub de licença (pode usar o do master ou simplificar)
    try: 
        from fabricador.main import verificar_licenca_online as check_lic
        if not check_lic("checkin"): return
    except: pass 

    os.system('cls' if os.name == 'nt' else 'clear')
    exibir_banner_farm()
    
    # Carrega contas do arquivo principal
    contas = carregar_json_seguro(config.ARQUIVO_PRINCIPAL)
    if not contas:
        print(f"\n{Cores.AMARELO}⚠️  Nenhuma conta encontrada em '{config.ARQUIVO_PRINCIPAL}'!{Cores.RESET}")
        return

    print(f"\n{Cores.CINZA}>>> Inicializando Motor Gráfico...{Cores.RESET}")
    co = ChromiumOptions()
    co.set_argument('--start-maximized') 
    co.set_argument('--window-size=1920,1080')
    
    # Usa a config global do fabricador
    if config.CONF.get("headless", False): co.headless(True)
    
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
    page.quit()
    input("\nEnter para voltar...")

def executar(): main()

if __name__ == "__main__": main()