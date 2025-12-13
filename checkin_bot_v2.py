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

os.system('') # Cores CMD

# --- CLASSE DE ESTILO ---
class Cores:
    RESET = '\033[0m'
    VERDE = '\033[92m'
    AMARELO = '\033[93m'
    VERMELHO = '\033[91m'
    CIANO = '\033[96m'
    CINZA = '\033[90m'
    NEGRITO = '\033[1m'

# ===== CONFIGURAÇÕES =====
ARQUIVO_HISTORICO = "historico_diario.json"
ARQUIVO_CONFIG = "config.json"
URL_LISTA_VIP = "https://gist.githubusercontent.com/iagoferranti/2675637690215af512e1e83e1eaf5e84/raw/emails.json"

LOGS_SESSAO = []

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

# --- UTILITÁRIOS ---
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
        data_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        nome_arq = f"log_execucao_{data_str}.txt"
        caminho = os.path.join(get_base_path(), nome_arq)
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

# --- LICENÇA ---
def verificar_licenca_online(permissao_necessaria="all"):
    """
    Verifica se o e-mail tem a permissão necessária.
    permissao_necessaria: 'fabricador', 'checkin' ou 'all' (para o menu principal)
    """
    # Configuração de Caminhos e E-mail
    email_conf = CONF.get("licenca_email", "") if 'CONF' in globals() else ""
    path = os.path.join(get_base_path(), "licenca.txt")
    
    if email_conf: email = email_conf
    elif os.path.exists(path):
        try: 
            with open(path, "r") as f: email = f.read().strip()
        except: email = ""
    else: email = ""
    
    # Se não tiver e-mail, pede (apenas se for chamado interativamente, ou retorna falso)
    if not email:
        if 'Cores' in globals(): print(f"{Cores.AMARELO}Licença não encontrada.{Cores.RESET}")
        else: print("Licença não encontrada.")
        email = input("Digite seu E-mail: ").strip()
        
    try:
        r = requests.get(URL_LISTA_VIP, timeout=10)
        if r.status_code == 200:
            try:
                # Tenta ler como o NOVO FORMATO (Dicionário)
                dados_licenca = r.json()
                
                # Se for uma lista antiga (Retrocompatibilidade), converte pra dicionário full
                if isinstance(dados_licenca, list):
                    dados_licenca = {e: ["all"] for e in dados_licenca}
                
                # Normaliza chaves para minúsculo
                dados_licenca = {k.lower().strip(): v for k, v in dados_licenca.items()}
                email_norm = email.lower().strip()
                
                if email_norm in dados_licenca:
                    permissoes = dados_licenca[email_norm]
                    
                    # Lógica de Permissão
                    acesso_liberado = False
                    if "all" in permissoes: acesso_liberado = True
                    elif permissao_necessaria in permissoes: acesso_liberado = True
                    
                    if acesso_liberado:
                        if 'Cores' in globals(): print(f"{Cores.VERDE}Licença Válida ({permissao_necessaria.upper()}){Cores.RESET}")
                        else: print(f"Licença Válida ({permissao_necessaria})")
                        
                        # Salva cache
                        with open(path, "w") as f: f.write(email)
                        return True
                    else:
                        if 'Cores' in globals(): print(f"{Cores.VERMELHO}Seu plano não inclui: {permissao_necessaria}{Cores.RESET}")
                        else: print(f"Seu plano não inclui: {permissao_necessaria}")
                        return False
            except Exception as e:
                print(f"Erro ao processar licença: {e}")
                
    except: pass
    
    if 'Cores' in globals(): print(f"{Cores.VERMELHO}Acesso Negado ou Erro de Conexão.{Cores.RESET}")
    else: print("Acesso Negado ou Erro de Conexão.")
    return False

def setup_contas():
    path = os.path.join(get_base_path(), "accounts.json")
    return carregar_json_seguro(path)

# --- NAVEGAÇÃO ---
def descobrir_url_evento(page):
    path = os.path.join(get_base_path(), "config_evento.json")
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                d = json.load(f)
                if time.time() - d.get("ts", 0) < 86400: return d['url']
        except: pass
        
    print("Buscando URL do evento...")
    try:
        page.get("https://www.gnjoylatam.com/pt")
        btn = page.wait.ele_displayed('text=Máquina PonPon', timeout=15)
        if btn:
            btn.click()
            time.sleep(5) 
            nova = page.latest_tab 
            url = nova.url
            nova.close()
            with open(path, "w") as f: json.dump({"url": url, "ts": time.time()}, f)
            return url
    except: pass
    return input("Cole o link do evento: ").strip()

def fazer_logout(page):
    try:
        page.run_cdp('Network.clearBrowserCookies')
        page.run_cdp('Network.clearBrowserCache')
    except: pass

def processar_roleta(page):
    premio_ganho = None
    try:
        page.scroll.to_bottom()
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
        
        # CLOUDFLARE
        time.sleep(3)
        precisa = True
        if page.ele('.page_success__gilOx') or page.ele('text:concluída'):
             if page.ele('text:concluída').states.is_displayed: precisa = False
        
        if precisa:
            try: page.ele('tag:body').click()
            except: pass
            
            if page.wait.ele_displayed('#email', timeout=5):
                page.run_js("document.getElementById('email').focus()")
                page.ele('#email').click()
            
            for _ in range(4):
                page.actions.key_down(Keys.SHIFT).key_down(Keys.TAB).key_up(Keys.TAB).key_up(Keys.SHIFT)
                time.sleep(0.2)
            page.actions.key_down(Keys.SPACE).key_up(Keys.SPACE)
            time.sleep(5)
            
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
    # Mude de verificar_licenca_online() para:
    if not verificar_licenca_online("checkin"): 
        return # Sai da função
    print(f"\n{Cores.CIANO}>>> AUTO FARM PREMIUM{Cores.RESET}")
    
    co = ChromiumOptions()
    co.set_argument('--force-device-scale-factor=0.75')
    
    # HEADLESS SWITCH
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