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
    AZUL = '\033[94m'
    MAGENTA = '\033[95m'
    CINZA = '\033[90m'
    NEGRITO = '\033[1m'

# ===== CONFIGURAÇÕES =====
ARQUIVO_HISTORICO = "historico_diario.json"
ARQUIVO_CONFIG = "config.json"
ARQUIVO_CONTAS = "accounts.json"
URL_LISTA_VIP = "https://gist.githubusercontent.com/iagoferranti/2675637690215af512e1e83e1eaf5e84/raw/emails.json"

LOGS_SESSAO = []

# --- CONFIG MANAGER (PASSIVO) ---
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

# --- VISUAL PREMIUM ---
def definir_titulo(texto):
    if os.name == 'nt':
        ctypes.windll.kernel32.SetConsoleTitleW(texto)

def exibir_banner_farm():
    print(f"""{Cores.MAGENTA}
    ╔══════════════════════════════════════════════════════════════╗
    ║  🎰  R A G N A R O K   A U T O   F A R M   S Y S T E M  🎰   ║
    ╚══════════════════════════════════════════════════════════════╝
    {Cores.RESET}""")

def log_step(icone, texto, cor=Cores.RESET):
    print(f"   {cor}{icone} {texto}{Cores.RESET}")

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
    
    cor_status = Cores.VERDE if status in ["SUCESSO", "JÁ FEITO"] else Cores.VERMELHO
    icone = "✅" if status in ["SUCESSO", "JÁ FEITO"] else "❌"
    
    print(f"\n   {Cores.NEGRITO}STATUS:{Cores.RESET} {icone} {cor_status}{status}{Cores.RESET}")
    if obs: print(f"   {Cores.CINZA}OBS: {obs}{Cores.RESET}")
    
    LOGS_SESSAO.append(linha)

def salvar_arquivo_log():
    try:
        base_dir = get_base_path()
        logs_dir = os.path.join(base_dir, "logs")
        if not os.path.exists(logs_dir): os.makedirs(logs_dir)

        data_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        nome_arq = f"log_execucao_{data_str}.txt"
        
        caminho = os.path.join(logs_dir, nome_arq)
        with open(caminho, "w", encoding="utf-8") as f: 
            f.write("\n".join(LOGS_SESSAO))
    except: pass

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

# --- LICENÇA ---
def verificar_licenca_online(permissao_necessaria="all"):
    try:
        from master import verificar_licenca_online as v
        return v(permissao_necessaria)
    except: return True

# --- INTERFACE ---
def setup_contas():
    path = os.path.join(get_base_path(), ARQUIVO_CONTAS)
    contas = carregar_json_seguro(path)
    if not contas:
        print(f"\n{Cores.AMARELO}⚠️  Nenhuma conta encontrada em '{ARQUIVO_CONTAS}'!{Cores.RESET}")
        time.sleep(3)
        return []
    return contas

# --- NAVEGAÇÃO ---
def descobrir_url_evento(page):
    path = os.path.join(get_base_path(), "config_evento.json")
    
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                d = json.load(f)
                if time.time() - d.get("ts", 0) < 86400: return d['url']
        except: pass
        
    log_step("🔍", "Buscando URL do evento atual...", Cores.CIANO)
    url_encontrada = None
    
    try:
        page.get("https://www.gnjoylatam.com/pt")
        btn = page.wait.ele_displayed('text=Máquina PonPon', timeout=15)
        if not btn: btn = page.wait.ele_displayed('text:PonPon', timeout=5)
              
        if btn:
            btn.click()
            time.sleep(5) 
            nova = page.latest_tab 
            url_encontrada = nova.url
            nova.close() 
    except: pass
    
    if not url_encontrada:
        print(f"{Cores.AMARELO}⚠️ Não detectado automaticamente.{Cores.RESET}")
        url_encontrada = input("   >> Cole o link do evento: ").strip()

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
        if page.handle_alert(accept=True): pass
        
        ele_count = page.wait.ele_displayed('.styles_attempts_count__iHKXy', timeout=5)
        if not ele_count: 
            log_step("🎰", "Roleta não disponível", Cores.CINZA)
            return None
        
        try: qtd = int(ele_count.text)
        except: qtd = 0
        
        if qtd > 0: log_step("🎟️", f"Giros disponíveis: {qtd}", Cores.AMARELO)
        
        while qtd > 0:
            btn = page.ele('@alt=Start')
            if btn:
                btn.click()
                time.sleep(1)
                if page.handle_alert(accept=True): break
                
                ele_premio = page.wait.ele_displayed('.styles_prize_object__LLDTh', timeout=15)
                if ele_premio:
                    nm = ele_premio.text
                    print(f"      {Cores.MAGENTA}★ PRÊMIO:{Cores.RESET} {Cores.NEGRITO}{nm}{Cores.RESET}")
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

def vencer_cloudflare_login(page):
    time.sleep(3)
    sucesso_visivel = False
    ele_texto = page.ele('text:Verificação de segurança para acesso concluída')
    if ele_texto and ele_texto.states.is_displayed: sucesso_visivel = True
    if not sucesso_visivel:
        ele_classe = page.ele('.page_success__gilOx')
        if ele_classe and ele_classe.states.is_displayed: sucesso_visivel = True

    if sucesso_visivel: return

    try: 
        if page.ele('#email'): page.ele('#email').click()
        else: page.ele('tag:body').click()
    except: pass
    time.sleep(0.5)
    for _ in range(4):
        page.actions.key_down(Keys.SHIFT).key_down(Keys.TAB).key_up(Keys.TAB).key_up(Keys.SHIFT)
        time.sleep(0.1)
    page.actions.key_down(Keys.SPACE).key_up(Keys.SPACE)
    time.sleep(5)

# --- 429 PROTECTION ---
def checar_bloqueio_ip(page):
    titulo = page.title.lower() if page.title else ""
    texto_body = page.ele('tag:body').text.lower() if page.ele('tag:body') else ""
    
    if "429" in titulo or "too many requests" in texto_body:
        print(f"\n{Cores.VERMELHO}╔════════════════════════════════════════════════════════════════╗{Cores.RESET}")
        print(f"{Cores.VERMELHO}║               🚨 BLOQUEIO DE IP DETECTADO (429)                ║{Cores.RESET}")
        print(f"{Cores.VERMELHO}╚════════════════════════════════════════════════════════════════╝{Cores.RESET}")
        print(f"\n{Cores.AMARELO}PAUSA DE SEGURANÇA: O servidor bloqueou seu IP.{Cores.RESET}")
        print(f"👉 Troque sua VPN ou reinicie o modem e pressione ENTER.")
        input()
        page.refresh()
        time.sleep(5)
        return True
    return False

def processar(page, conta, url, index, total):
    email = conta['email']
    definir_titulo(f"Ragnarok Farm | Conta {index}/{total} | {email}")
    
    # --- LÓGICA DE ALINHAMENTO DINÂMICO ---
    # 1. Monta o texto puro (sem cores) para medir o tamanho real
    texto_label = f" 👤 CONTA {str(index).zfill(2)}/{str(total).zfill(2)}: "
    texto_email = f"{email} " # Espaço extra no final
    texto_completo = texto_label + texto_email
    
    # 2. Define a largura da caixa (Mínimo 60, ou cresce se o email for gigante)
    largura_box = max(len(texto_completo), 60)
    
    # 3. Calcula preenchimento (padding) para alinhar a borda direita
    padding = " " * (largura_box - len(texto_completo))
    
    # 4. Desenha
    print(f"\n{Cores.AZUL}┌{'─' * largura_box}┐{Cores.RESET}")
    # Aqui montamos a linha com as cores certas
    print(f"{Cores.AZUL}│{Cores.RESET}{texto_label}{Cores.NEGRITO}{texto_email}{Cores.RESET}{padding}{Cores.AZUL}│{Cores.RESET}")
    print(f"{Cores.AZUL}└{'─' * largura_box}┘{Cores.RESET}")
    
    sucesso = False
    log_status = "ERRO"
    msg = ""
    
    try:
        fazer_logout(page)
        page.get(url)
        time.sleep(2)
        
        checar_bloqueio_ip(page)
        
        if page.wait.ele_displayed('text:Login', timeout=5):
            page.ele('text:Login').click()
        elif page.wait.ele_displayed('@alt=LOGIN BUTTON', timeout=5):
            page.ele('@alt=LOGIN BUTTON').click()
            
        page.wait.url_change('login.gnjoylatam.com', timeout=15)
        
        log_step("🛡️", "Bypassing Cloudflare...", Cores.CINZA)
        vencer_cloudflare_login(page)
            
        page.ele('#email').input(email)
        page.ele('#password').input(conta['password'])
        time.sleep(1)
        page.ele('text=CONTINUAR').click()
        
        if page.wait.ele_displayed('text:Logout', timeout=30):
            log_step("🔓", "Login Efetuado", Cores.VERDE)
            
            if page.url != url: page.get(url); time.sleep(3)
            
            # Checkin
            page.scroll.to_bottom()
            btn = page.ele('tag:img@@alt=attendance button')
            if btn:
                if "complete" in btn.attr("src"):
                    log_status = "JÁ FEITO"
                    log_step("📅", "Check-in já realizado hoje", Cores.AMARELO)
                    sucesso = True
                else:
                    btn.click()
                    time.sleep(4)
                    log_status = "SUCESSO"
                    log_step("📅", "Check-in realizado!", Cores.VERDE)
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
    if not verificar_licenca_online("checkin"): return
    os.system('cls' if os.name == 'nt' else 'clear')
    exibir_banner_farm()
    
    contas = setup_contas()
    if not contas: return

    print(f"\n{Cores.CINZA}>>> Inicializando Motor Gráfico...{Cores.RESET}")
    co = ChromiumOptions()
    co.set_argument('--start-maximized') 
    co.set_argument('--window-size=1920,1080')
    co.set_argument('--force-device-scale-factor=0.8')
    
    if CONF.get("headless", False):
        print(f"{Cores.AMARELO}⚠️  Modo Invisível (Headless) Ativo{Cores.RESET}")
        co.headless(True)
        
    page = ChromiumPage(addr_or_opts=co)
    
    # === FORÇA MAXIMIZAR DE VERDADE ===
    try: 
        page.set.window.max()
    except: 
        # Fallback se maximizar falhar
        page.set.window.size(1920, 1080)

    url = descobrir_url_evento(page)
    ja_foi = carregar_historico_hoje()
    
    contas_para_fazer = [c for c in contas if c['email'] not in ja_foi]
    print(f"{Cores.CIANO}📊 RESUMO:{Cores.RESET} Total: {len(contas)} | Pendentes: {len(contas_para_fazer)} | Feitos: {len(ja_foi)}")
    time.sleep(2)
    
    count_sucesso = 0
    total_exec = len(contas_para_fazer)
    
    for i, acc in enumerate(contas_para_fazer):
        processar(page, acc, url, i+1, total_exec)
        count_sucesso += 1
        
        if i < total_exec - 1:
            t = random.randint(5, 12)
            print(f"\n{Cores.CINZA}⏳ Aguardando {t}s para próxima conta...{Cores.RESET}")
            time.sleep(t)
        
    msg_fim = f"FARM FINALIZADO - {count_sucesso} CONTAS PROCESSADAS"
    
    # --- CORREÇÃO DO ERRO DE STR + INT ---
    tam_linha = len(msg_fim) + 4
    print(f"\n{Cores.VERDE}╔{'═' * tam_linha}╗")
    print(f"║  {msg_fim}  ║")
    print(f"╚{'═' * tam_linha}╝{Cores.RESET}")
    
    salvar_arquivo_log()
    enviar_telegram(msg_fim)
    
    page.quit()
    input("\nPressione Enter para voltar ao menu...")

def executar(): main()

if __name__ == "__main__": main()