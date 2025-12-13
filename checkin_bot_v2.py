import os
import sys
import json
import time
import random
import datetime
import requests
import subprocess
import textwrap
import ctypes
import shutil
from DrissionPage import ChromiumPage, ChromiumOptions
from DrissionPage.common import Keys

os.system('') # Enable CMD colors

# --- STYLE CLASS ---
class Cores:
    RESET = '\033[0m'
    VERDE = '\033[92m'
    AMARELO = '\033[93m'
    VERMELHO = '\033[91m'
    CIANO = '\033[96m'
    CINZA = '\033[90m'
    NEGRITO = '\033[1m'

# ===== SETTINGS =====
ARQUIVO_HISTORICO = "historico_diario.json"
ARQUIVO_CONFIG = "config.json"
URL_LISTA_VIP = "https://gist.githubusercontent.com/iagoferranti/2675637690215af512e1e83e1eaf5e84/raw/emails.json"

LOGS_SESSAO = []

# --- CONFIG MANAGER (PASSIVE) ---
def carregar_config():
    padrao = {"headless": False, "telegram_token": "", "telegram_chat_id": ""}
    
    # IMPROVEMENT: PASSIVE MODE - Does not create the file, leaves it to the Wizard (master.py)
    if not os.path.exists(ARQUIVO_CONFIG): 
        return padrao 

    try:
        with open(ARQUIVO_CONFIG, "r", encoding="utf-8") as f:
            user = json.load(f)
            padrao.update(user)
            return padrao
    except: return padrao

CONF = carregar_config()

# --- TELEGRAM ---
def enviar_telegram(mensagem):
    token = CONF.get("telegram_token")
    chat_id = CONF.get("telegram_chat_id")
    if not token or not chat_id: return
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {"chat_id": chat_id, "text": mensagem}
        requests.post(url, data=data, timeout=5)
    except: pass

# --- UTILITIES ---
def get_base_path():
    if getattr(sys, 'frozen', False): return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def registrar_log(email, status, obs=""):
    agora = datetime.datetime.now().strftime("%H:%M:%S")
    linha = f"[{agora}] {email} -> {status} {f'({obs})' if obs else ''}"
    cor = Cores.VERDE if status in ["SUCESSO", "JÁ FEITO"] else Cores.VERMELHO
    print(f"   {cor}{status}:{Cores.RESET} {email} {f'| {obs}' if obs else ''}")
    LOGS_SESSAO.append(linha)

def salvar_arquivo_log():
    try:
        # IMPROVEMENT: ORGANIZED LOGS - Creates 'logs' folder
        base_dir = get_base_path()
        logs_dir = os.path.join(base_dir, "logs")
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)

        data_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        nome_arq = f"log_execucao_{data_str}.txt"
        
        # Saves inside logs folder
        caminho = os.path.join(logs_dir, nome_arq)
        with open(caminho, "w", encoding="utf-8") as f: 
            f.write("\n".join(LOGS_SESSAO))
    except: pass

# --- SAFE SAVE JSON ---
def carregar_json_seguro(caminho):
    if not os.path.exists(caminho): return {}
    try:
        with open(caminho, "r", encoding="utf-8") as f: return json.load(f)
    except: return {}

def salvar_json_seguro(caminho, dados):
    try:
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=4)
    except: pass

def carregar_historico_hoje():
    hoje = datetime.datetime.now().strftime("%Y-%m-%d")
    dados = carregar_json_seguro(ARQUIVO_HISTORICO)
    if dados.get("data") == hoje: return set(dados.get("contas", []))
    return set()

def adicionar_ao_historico(email):
    hoje = datetime.datetime.now().strftime("%Y-%m-%d")
    dados = carregar_json_seguro(ARQUIVO_HISTORICO)
    if dados.get("data") != hoje: dados = {"data": hoje, "contas": []}
    if email not in dados["contas"]:
        dados["contas"].append(email)
        salvar_json_seguro(ARQUIVO_HISTORICO, dados)

# --- LICENSE ---
def verificar_licenca_online(permissao_necessaria="all"):
    """
    Checks if email has necessary permission.
    """
    try:
        from master import verificar_licenca_online as v
        return v(permissao_necessaria)
    except:
        # Local fallback if running isolated
        return True

def setup_contas():
    path = os.path.join(get_base_path(), "accounts.json")
    return carregar_json_seguro(path)

# --- SMART NAVIGATION ---
def descobrir_url_evento(page):
    path = os.path.join(get_base_path(), "config_evento.json")
    
    # 1. Try to use 24h Cache
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                d = json.load(f)
                if time.time() - d.get("ts", 0) < 86400: 
                    return d['url']
        except: pass
        
    print("Buscando URL do evento atual...")
    url_encontrada = None
    
    # 2. Try to discover via Home Page (Safe Method)
    try:
        page.get("https://www.gnjoylatam.com/pt")
        # Search for button with flexible text
        btn = page.wait.ele_displayed('text=Máquina PonPon', timeout=15)
        if not btn:
             btn = page.wait.ele_displayed('text:PonPon', timeout=5)
             
        if btn:
            btn.click()
            time.sleep(5) 
            nova = page.latest_tab 
            url_encontrada = nova.url
            nova.close() # Close new tab to avoid clutter
    except: pass
    
    # 3. Fallback: Ask user if not found automatically
    if not url_encontrada:
        print(f"{Cores.AMARELO}⚠️ Não foi possível detectar o evento automaticamente.{Cores.RESET}")
        url_encontrada = input("Cole o link do evento (ex: .../decemberroulette): ").strip()

    # 4. Save result (Automatic or Manual) to cache
    if url_encontrada:
        try:
            with open(path, "w") as f: 
                json.dump({"url": url_encontrada, "ts": time.time()}, f)
        except: pass
        
    return url_encontrada

def fazer_logout(page):
    try:
        page.run_cdp('Network.clearBrowserCookies')
        page.run_cdp('Network.clearBrowserCache')
    except: pass

def processar_roleta(page):
    premio_ganho = None
    try:
        page.scroll.to_bottom()
        
        # Close "event ended" alerts if they appear
        if page.handle_alert(accept=True): pass
        
        ele_count = page.wait.ele_displayed('.styles_attempts_count__iHKXy', timeout=5)
        if not ele_count: return None
        
        try: qtd = int(ele_count.text)
        except: qtd = 0
        
        if qtd > 0: print(f"   🎰 Giros disponíveis: {qtd}")
        
        while qtd > 0:
            btn = page.ele('@alt=Start')
            if btn:
                btn.click()
                time.sleep(1)
                if page.handle_alert(accept=True): break
                
                ele_premio = page.wait.ele_displayed('.styles_prize_object__LLDTh', timeout=15)
                if ele_premio:
                    nm = ele_premio.text
                    print(f"      🎉 {Cores.AMARELO}Ganhou: {nm}{Cores.RESET}")
                    if premio_ganho: premio_ganho += f" + {nm}"
                    else: premio_ganho = f"Prêmio: {nm}"
                    time.sleep(2)
                    try: page.ele('.styles_roulette_btn_close__GzdeD').click()
                    except: page.ele('tag:body').click()
                else: break
                try: qtd = int(page.ele('.styles_attempts_count__iHKXy').text)
                except: break
            else: break
    except: pass
    return premio_ganho

# --- CLOUDFLARE BYPASS LOGIC (V60 - Real Visibility) ---
def vencer_cloudflare_login(page):
    time.sleep(5)
    
    # 1. CHECK FOR REAL SUCCESS (VISIBLE)
    sucesso_visivel = False
    
    # Check text
    ele_texto = page.ele('text:Verificação de segurança para acesso concluída')
    if ele_texto and ele_texto.states.is_displayed:
        sucesso_visivel = True
        
    # Check class
    if not sucesso_visivel:
        ele_classe = page.ele('.page_success__gilOx')
        if ele_classe and ele_classe.states.is_displayed:
            sucesso_visivel = True

    if sucesso_visivel:
        # If already green and visible, do nothing
        return

    # 2. IF NOT VISIBLE, IT IS PENDING (OR GHOST) -> APPLY MANEUVER
    # Ensure focus
    try: 
        if page.ele('#email'):
            page.ele('#email').click()
        else:
            page.ele('tag:body').click()
    except: pass
        
    time.sleep(0.5)

    # Golden Sequence: 4x Shift+Tab + Space
    for _ in range(4):
        page.actions.key_down(Keys.SHIFT).key_down(Keys.TAB).key_up(Keys.TAB).key_up(Keys.SHIFT)
        time.sleep(0.1)
    
    page.actions.key_down(Keys.SPACE).key_up(Keys.SPACE)
    time.sleep(5)

def processar(page, conta, url):
    email = conta['email']
    print(f"\n>>> Conta: {email}")
    sucesso = False
    log_status = "ERRO"
    msg = ""
    
    try:
        fazer_logout(page)
        page.get(url)
        time.sleep(2)
        
        if page.wait.ele_displayed('text:Login', timeout=5):
            page.ele('text:Login').click()
        elif page.wait.ele_displayed('@alt=LOGIN BUTTON', timeout=5):
            page.ele('@alt=LOGIN BUTTON').click()
            
        page.wait.url_change('login.gnjoylatam.com', timeout=15)
        
        # --- APPLIES NEW CLOUDFLARE LOGIC ---
        vencer_cloudflare_login(page)
            
        page.ele('#email').input(email)
        page.ele('#password').input(conta['password'])
        time.sleep(1)
        page.ele('text=CONTINUAR').click()
        
        if page.wait.ele_displayed('text:Logout', timeout=30):
            print("   ✅ Login OK")
            
            if page.url != url: page.get(url); time.sleep(3)
            
            # Checkin
            page.scroll.to_bottom()
            btn = page.ele('tag:img@@alt=attendance button')
            if btn:
                if "complete" in btn.attr("src"):
                    log_status = "JÁ FEITO"
                    sucesso = True
                else:
                    btn.click()
                    time.sleep(4)
                    log_status = "SUCESSO"
                    sucesso = True
            
            # Roleta
            p = processar_roleta(page)
            if p: msg = p
            
        else:
            log_status = "FALHA LOGIN"
            
    except Exception as e:
        msg = str(e)
    
    registrar_log(email, log_status, msg)
    if sucesso: adicionar_ao_historico(email)
    fazer_logout(page)

def main():
    if not verificar_licenca_online("checkin"): 
        return
    print(f"\n{Cores.CIANO}>>> AUTO FARM PREMIUM{Cores.RESET}")
    
    co = ChromiumOptions()
    co.set_argument('--force-device-scale-factor=0.75')
    
    if CONF.get("headless", False):
        print(f"{Cores.AMARELO}Modo Invisível Ativo.{Cores.RESET}")
        co.headless(True)
        
    page = ChromiumPage(addr_or_opts=co)
    
    url = descobrir_url_evento(page)
    contas = setup_contas()
    ja_foi = carregar_historico_hoje()
    
    print(f"Total Contas: {len(contas)} | Já feitas hoje: {len(ja_foi)}")
    
    count_sucesso = 0
    for acc in contas:
        if acc['email'] in ja_foi:
            print(f"{Cores.CINZA}⏩ Pulando {acc['email']}{Cores.RESET}")
            continue
            
        processar(page, acc, url)
        count_sucesso += 1
        
        t = random.randint(5, 12)
        print(f"--- Aguardando {t}s ---")
        time.sleep(t)
        
    msg_fim = f"FARM FINALIZADO. Processados: {count_sucesso}"
    print(f"\n{Cores.VERDE}=== {msg_fim} ==={Cores.RESET}")
    salvar_arquivo_log()
    enviar_telegram(msg_fim)
    
    page.quit()
    input("Enter para sair...")

def executar(): main()

if __name__ == "__main__": main()