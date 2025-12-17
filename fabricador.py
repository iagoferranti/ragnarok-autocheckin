import time
import re
import requests
import random
import string
import json
import os
import html
import sys
from urllib.parse import quote
from urllib.parse import quote
from datetime import datetime
from DrissionPage import ChromiumPage, ChromiumOptions
from DrissionPage.common import Keys

os.system('') # Enables ANSI colors in CMD

# --- PROXY UTILS ---
def carregar_proxies_arquivo():
    if not os.path.exists("proxies.txt"):
        return []
    with open("proxies.txt", "r") as f:
        # Remove espaços e linhas vazias
        proxies = [linha.strip() for linha in f if linha.strip()]
    return proxies

def formatar_proxy_requests(proxy_string):
    """
    Converte 'IP:PORT:USER:PASS' para 'http://USER:PASS@IP:PORT'
    """
    if not proxy_string: return None
    
    proxy_string = proxy_string.strip()
    
    # Se vier no formato do seu arquivo (4 partes com :)
    # Ex: 216.10.27.159:6837:ppjbocxs:yf2wchdd99hk
    partes = proxy_string.split(':')
    if len(partes) == 4:
        ip, porta, user, senha = partes
        # O Chrome precisa deste formato aqui:
        proxy_url = f"http://{user}:{senha}@{ip}:{porta}"
        
        return {
            "http": proxy_url,
            "https": proxy_url,
            "url_formatada": proxy_url # Guardamos a string pronta pro Chrome
        }
        
    # Fallback para outros formatos
    if not proxy_string.startswith("http"):
        proxy_string = f"http://{proxy_string}"
        
    return {
        "http": proxy_string,
        "https": proxy_string,
        "url_formatada": proxy_string
    }

# --- DEFAULT CONFIGURATION ---
ARQUIVO_CONFIG = "config.json"
ARQUIVO_SALVAR = "novas_contas.json"
ARQUIVO_PRINCIPAL = "accounts.json"
URL_LISTA_VIP = "https://gist.githubusercontent.com/iagoferranti/2675637690215af512e1e83e1eaf5e84/raw/emails.json"
TIMEOUT_PADRAO = 40 

# --- STYLE CLASS ---
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
    ITALICO = '\033[3m'

TENTATIVAS_BLOQUEIO_IP = 0
MAX_BLOQUEIOS_IP = 3


# --- PREMIUM LOGGING FUNCTIONS ---
def exibir_banner():
    print(f"""{Cores.CIANO}
    ╔══════════════════════════════════════════════════════════════╗
    ║      🏭   R A G N A R O K   A C C O U N T   F A C T O R Y    ║
    ╚══════════════════════════════════════════════════════════════╝
    {Cores.RESET}""")

def log_info(msg): 
    print(f"{Cores.CIANO} ℹ️  {Cores.NEGRITO}INFO:{Cores.RESET} {msg}")

def log_sucesso(msg): 
    print(f"{Cores.VERDE} ✅ {Cores.NEGRITO}SUCESSO:{Cores.RESET} {msg}")

def log_aviso(msg): 
    print(f"{Cores.AMARELO} ⚠️  {Cores.NEGRITO}ALERTA:{Cores.RESET} {msg}")

def log_erro(msg): 
    print(f"{Cores.VERMELHO} ❌ {Cores.NEGRITO}ERRO:{Cores.RESET} {msg}")

def log_sistema(msg): 
    print(f"{Cores.CINZA}    └── {msg}{Cores.RESET}")

def log_debug(msg): 
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"{Cores.CINZA}    [DEBUG {ts}] {msg}{Cores.RESET}")

def barra_progresso(tempo_total, prefixo='', sufixo='', comprimento=30, preenchimento='█'):
    """Exibe uma barra de progresso visual"""
    start_time = time.time()
    while True:
        elapsed_time = time.time() - start_time
        if elapsed_time > tempo_total:
            break
        percent = 100 * (elapsed_time / float(tempo_total))
        filled_length = int(comprimento * elapsed_time // tempo_total)
        bar = preenchimento * filled_length + '-' * (comprimento - filled_length)
        sys.stdout.write(f'\r{prefixo} |{Cores.CIANO}{bar}{Cores.RESET}| {percent:.1f}% {sufixo}')
        sys.stdout.flush()
        time.sleep(0.1)
    sys.stdout.write('\n')

# --- CONFIG LOADER ---
def carregar_config():
    config_padrao = {
        "licenca_email": "", "headless": False, "tag_email": "rag",
        "sobrenome_padrao": "Silva", "telegram_token": "", "telegram_chat_id": ""
    }
    if not os.path.exists(ARQUIVO_CONFIG): return config_padrao 
    try:
        with open(ARQUIVO_CONFIG, "r", encoding="utf-8") as f:
            user_config = json.load(f)
            config_padrao.update(user_config)
            return config_padrao
    except: return config_padrao

CONF = carregar_config()

try: import pyotp; TEM_PYOTP = True
except ImportError: TEM_PYOTP = False

# --- TELEGRAM ---
def enviar_telegram(mensagem):
    token = CONF.get("telegram_token"); chat_id = CONF.get("telegram_chat_id")
    if not token or not chat_id: return
    try: requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data={"chat_id": chat_id, "text": mensagem}, timeout=5)
    except: pass

# --- FILES MANAGEMENT ---
def carregar_json_seguro(caminho):
    if not os.path.exists(caminho): return []
    try: 
        with open(caminho, "r", encoding="utf-8") as f: return json.load(f)
    except: return []

def salvar_json_seguro(caminho, dados):
    try:
        with open(caminho, "w", encoding="utf-8") as f: json.dump(dados, f, indent=4, ensure_ascii=False)
        return True
    except: return False

def consolidar_conta_no_principal(email, senha, seed=None):
    contas = carregar_json_seguro(ARQUIVO_PRINCIPAL)
    for c in contas:
        if c.get('email') == email: return
    nova_conta = {"email": email, "password": senha}
    if seed: nova_conta["seed_otp"] = seed
    contas.append(nova_conta)
    salvar_json_seguro(ARQUIVO_PRINCIPAL, contas)

def salvar_conta_backup(email, senha, seed, status="PRONTA_PARA_FARMAR"):
    dados = carregar_json_seguro(ARQUIVO_SALVAR)
    dados = [c for c in dados if c.get('email') != email]
    nova = {
        "email": email, "password": senha, "seed_otp": seed,
        "data_criacao": datetime.now().strftime("%Y-%m-%d %H:%M"), "status": status
    }
    dados.append(nova)
    salvar_json_seguro(ARQUIVO_SALVAR, dados)

def get_base_path():
    if getattr(sys, 'frozen', False): return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

# --- UTILS ---
def gerar_senha_ragnarok():
    chars = string.ascii_letters + string.digits + "!@#$"
    senha = [random.choice(string.ascii_uppercase), random.choice(string.ascii_lowercase), random.choice(string.digits), random.choice("!@#$")]
    senha += random.choices(chars, k=8); random.shuffle(senha)
    return "".join(senha)

def delay_humano(): time.sleep(random.uniform(0.8, 1.5))

def limpar_html(texto_html): return re.sub(re.compile('<.*?>'), ' ', texto_html)

# --- FUNÇÃO DE EXTRAÇÃO MELHORADA ---
def extrair_codigo_seguro(texto_bruto):
    if not texto_bruto: return None
    
    # 1. Limpeza pesada
    texto = limpar_html(texto_bruto).replace('&nbsp;', ' ')
    
    # Lista de palavras comuns em e-mails que têm 6 letras e confundem o bot
    BLACKLIST = [
        'abaixo', 'assets', 'height', 'width', 'style', 'script', 'border', 
        'verifi', 'cation', 'segura', 'access', 'bottom', 'center', 'family',
        'follow', 'format', 'ground', 'header', 'online', 'public', 'select',
        'server', 'sign', 'simple', 'source', 'strong', 'target', 'title',
        'window', 'yellow', 'codigo', 'codigo'
    ]

    # --- ESTRATÉGIA 1: CÓDIGO MISTO (Letra + Número) ---
    # É a mais segura. Se tiver número e letra misturado (ex: 12abc3), é 99.9% de certeza.
    # Procura algo de 6 digitos que tenha PELO MENOS 1 número e PELO MENOS 1 letra.
    match_misto = re.search(r'\b(?=[a-zA-Z0-9]*\d)(?=[a-zA-Z0-9]*[a-zA-Z])[a-zA-Z0-9]{6}\b', texto)
    if match_misto:
        return match_misto.group(0)

    # --- ESTRATÉGIA 2: CONTEXTO "CÓDIGO:" (Para códigos só de letras ou só números) ---
    # Procura "Código" ou "Code" e pega os próximos 6 caracteres, mas verifica a Blacklist.
    match_contexto = re.search(r'(?:C[oó]digo|Code|OTP)[^a-zA-Z0-9]*([a-zA-Z0-9]{6})\b', texto, re.IGNORECASE)
    if match_contexto:
        codigo = match_contexto.group(1)
        # Se for só letras, checa se não é uma palavra comum (ex: "abaixo")
        if codigo.lower() not in BLACKLIST:
            return codigo

    # --- ESTRATÉGIA 3: NUMÉRICO PURO (Fallback) ---
    # Se não achou misto nem contexto, tenta achar 6 números soltos (ex: 123456)
    match_numerico = re.search(r'\b\d{6}\b', texto)
    if match_numerico:
        return match_numerico.group(0)

    return None


def diagnostico_pagina(page):
    try:
        url = page.url
        titulo = page.title
        # log_debug(f"Página Atual: {url} | Título: {titulo}")
    except: pass

# --- BROWSER ACTIONS ---
def fechar_cookies(page):
    try:
        if page.ele('.cookieprivacy_btn__Pqz8U', timeout=1): page.ele('.cookieprivacy_btn__Pqz8U').click()
        elif page.ele('text=concordo.', timeout=1): page.ele('text=concordo.').click()
    except: pass

def clicar_com_seguranca(page, seletor, nome_elemento="Elemento"):
    for tentativa in range(3):
        try:
            btn = page.wait.ele_displayed(seletor, timeout=TIMEOUT_PADRAO)
            if btn:
                page.scroll.to_see(btn); delay_humano(); btn.click(); return True
        except:
            try:
                btn = page.ele(seletor)
                if btn: page.run_js("arguments[0].click()", btn); return True
            except: pass
            time.sleep(1)
    log_erro(f"Falha ao clicar em {nome_elemento}."); return False

def checar_bloqueio_ip(page):
    global TENTATIVAS_BLOQUEIO_IP

    try:
        body_txt = page.ele('tag:body').text.lower()
        title_txt = page.title.lower() if page.title else ""

        if "429" in title_txt or "too many requests" in body_txt:
            TENTATIVAS_BLOQUEIO_IP += 1

            print(
                f"\n{Cores.VERMELHO}🚨 BLOQUEIO DE IP (429) "
                f"[{TENTATIVAS_BLOQUEIO_IP}/{MAX_BLOQUEIOS_IP}]{Cores.RESET}"
            )

            if TENTATIVAS_BLOQUEIO_IP >= MAX_BLOQUEIOS_IP:
                print(f"\n{Cores.VERMELHO}❌ IP BLOQUEADO DEFINITIVAMENTE NESTA EXECUÇÃO{Cores.RESET}")
                print(f"{Cores.AMARELO}Finalize o script, troque o IP e execute novamente.{Cores.RESET}")
                page.quit()
                os._exit(1)  # encerra tudo imediatamente

            input(f"\n{Cores.VERDE}>>> Troque o IP e pressione ENTER...{Cores.RESET}")
            page.refresh()
            time.sleep(5)
            return True

    except Exception as e:
        log_debug(f"Erro checando bloqueio IP: {e}")

    return False


# --- CLOUDFLARE "OLHOS DE ÁGUIA" (V4.7) ---
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
            # log_debug(f"Status Visual CF: {status_texto}")

        if "concluída" in status_texto.lower() or "sucesso" in status_texto.lower() or "success" in status_texto.lower():
            log_sucesso("Cloudflare Validado!")
            time.sleep(1) 
            return True

        ele_sucesso_icon = page.ele('.page_success__gilOx')
        if ele_sucesso_icon and ele_sucesso_icon.states.is_displayed:
            #  log_debug("Cloudflare: Ícone de sucesso visível.")
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
            log_aviso("Cloudflare detectou falha de segurança (Bloqueio). Recarregando página...")
            page.refresh()
            time.sleep(4)
            continue

        time.sleep(1)
    
    log_erro("Timeout no Cloudflare. Não foi possível validar.")
    return False

def garantir_carregamento(page, seletor_esperado, timeout=30):
    inicio = time.time()
    while time.time() - inicio < timeout:
        if page.ele(seletor_esperado) and page.ele(seletor_esperado).states.is_displayed:
            return True
        if checar_bloqueio_ip(page):
            inicio = time.time()
            continue
        time.sleep(1)
    return False

def garantir_logout(page):
    try:
        page.run_cdp('Network.clearBrowserCookies')
        page.run_cdp('Network.clearBrowserCache')
        page.run_js('localStorage.clear(); sessionStorage.clear();')
    except: pass
    try:
        btn_logout = page.ele('.header_logoutBtn__6Pv_m')
        if btn_logout:
            log_sistema("Sessão ativa detectada. Fazendo Logout...")
            btn_logout.click()
            time.sleep(3)
    except: pass

def clicar_botao_otp(page):
    try:
        btn = page.wait.ele_displayed('css:button.page_otp_status_btn__DulWo.page_otp_join_btn__KKBJq', timeout=15)
        if not btn:
            return False

        # try:
        #     log_debug(
        #         f"OTP btn visible={btn.states.is_displayed} "
        #         f"disabled={btn.attr('disabled')}"
        #     )
        # except:
        #     pass

        try:
            btn.click()
            return True
        except:
            pass

        try:
            page.run_js("arguments[0].click()", btn)
            return True
        except:
            return False
    except:
        return False

def capturar_erro_email(page):
    # tenta primeiro os elementos de erro
    seletores = [
        '.mailauth_errorMessage__Umj_A',
        '.input_errorMsg__hM_98',
    ]

    deadline = time.time() + 4
    while time.time() < deadline:
        textos = []

        # 1) pega textos de elementos de erro
        for sel in seletores:
            try:
                el = page.ele(sel, timeout=0.2)
                if el and el.states.is_displayed:
                    t = (el.text or "").strip()
                    if t:
                        textos.append(t)
            except:
                pass

        # 2) fallback: body (pra erros sem classe estável)
        try:
            body = (page.ele('tag:body').text or "").strip()
            if body:
                textos.append(body)
        except:
            pass

        # normaliza e tenta mapear
        joined = " | ".join(textos)
        low = joined.lower()

        # ✅ MAPEAMENTOS IMPORTANTES
        if "não pode ser utilizado" in low or "nao pode ser utilizado" in low:
            return "EMAIL_INVALIDO", "Este endereço de e-mail não pode ser utilizado."
        if "não é possível se cadastrar com este domínio" in low or "domínio de e-mail" in low or "dominio de e-mail" in low:
            return "DOMINIO_BLOQUEADO", "Domínio bloqueado para cadastro."
        if "segurança" in low and ("insuficiente" in low or "failed" in low):
            return "SEGURANCA_INSUFICIENTE", "Falha de segurança / Cloudflare."
        if "em uso" in low or "já está em uso" in low or "ja esta em uso" in low:
            return "EMAIL_EM_USO", "E-mail já está em uso."

        time.sleep(0.2)

    return None, ""




# ================= EMAIL PROVIDERS =================
class EmailSession:
    def __init__(self):
        self.email = None
        self.senha_api = "Senha123"
        self.token = None
        self.sid_token = None
        self.login_1sec = None
        self.domain_1sec = None
        self.provider_name = ""
        self.primeiro_nome = "Jose"
        self.session_requests = None


# --- CONFIGURAÇÃO DE HEADERS PARA API (Anti-Block) ---
API_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://mail-temp.site/",
    "Origin": "https://mail-temp.site",
    "X-Requested-With": "XMLHttpRequest"
}


# --- CLASSE DO PROVEDOR OTIMIZADA ---
class ProviderMailTempSite:
    # Agora aceita proxy_dict no __init__
    def __init__(self, proxy_dict=None):
        self.proxies = proxy_dict

    def gerar(self, banidos=[]):
        obj = EmailSession()
        obj.provider_name = "MailTempSite"
        tag = CONF.get("tag_email", "rag")
        
        try:
            # Passamos self.proxies aqui
            r = requests.get("https://mail-temp.site/list_domain.php", headers=API_HEADERS, proxies=self.proxies, timeout=15)
            data = r.json()
            
            if data.get('success'):
                doms = [d for d in data.get('domains', []) if d not in banidos]
                if not doms: return None
                
                domain = random.choice(doms)
                sulfixo = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
                obj.email = f"{tag}_{sulfixo}@{domain}"
                return obj
        except Exception as e:
            # log_debug(f"Erro proxy/req: {e}")
            pass
        return None

    def esperar_codigo(self, obj, filtro):
        try:
            url = f"https://mail-temp.site/checkmail.php?mail={obj.email}"
            # Passamos self.proxies aqui também
            r = requests.get(url, headers=API_HEADERS, proxies=self.proxies, timeout=15)
            data = r.json()
            
            if data.get('success'):
                for msg in data.get('emails', []):
                    if filtro.lower() in msg['subject'].lower():
                        r2 = requests.get(f"https://mail-temp.site/viewmail.php?id={msg['id']}", headers=API_HEADERS, proxies=self.proxies, timeout=15)
                        data2 = r2.json()
                        if data2.get('success'):
                            raw_body = data2['email'].get('body', '')
                            return html.unescape(raw_body)
        except Exception:
            pass
        return None

# --- MAIN LOOP ---
def criar_conta(page, blacklist_global, proxy_dict, ultimo_provedor_ok=None):
    garantir_logout(page)
    dominios_banidos = blacklist_global
    # provedores_disponiveis = [ProviderGuerrilla, ProviderMailTM, Provider1SecMail, ProviderMailTempSite]
    provedores_disponiveis = [ProviderMailTempSite]

    # prioriza o provedor "whitelist" (o primeiro que deu bom)
    if ultimo_provedor_ok in provedores_disponiveis:
        provedores_disponiveis = [ultimo_provedor_ok] + [p for p in provedores_disponiveis if p != ultimo_provedor_ok]
    else:
        random.shuffle(provedores_disponiveis)


    contador_tentativas = 0
    
    while contador_tentativas < 15:
        if contador_tentativas > 0:
            print(f"\n{Cores.AMARELO}♻️  Nova Tentativa ({contador_tentativas+1})...{Cores.RESET}")
            garantir_logout(page)
            
        prov_class = provedores_disponiveis[contador_tentativas % len(provedores_disponiveis)]
        log_info(f"Gerando identidade via: {Cores.MAGENTA}{prov_class.__name__}{Cores.RESET}...")
        
        prov = prov_class(proxy_dict=proxy_dict)
        obj = prov.gerar(banidos=list(dominios_banidos))
        
        if not obj:
            log_debug("Provedor não tem domínios disponíveis/limpos. Trocando...")
            contador_tentativas += 1
            continue

        log_sucesso(f"E-mail Gerado: {Cores.NEGRITO}{obj.email}{Cores.RESET}")
        
        try:
            log_info("Acessando Cadastro...")
            page.get("https://member.gnjoylatam.com/pt/join")
            
            if not garantir_carregamento(page, '#email', timeout=30):
                log_erro("Timeout carregando formulário. Site lento ou fora do ar.")
                contador_tentativas += 1; continue

            if not vencer_cloudflare_obrigatorio(page):
                log_erro("Cloudflare barrou. Reiniciando página...")
                page.refresh(); continue
            
            page.ele('#email').click(); page.ele('#email').clear(); page.ele('#email').input(obj.email)
            delay_humano()
            
            if not clicar_com_seguranca(page, 'text=Enviar verificação', "Botão Enviar"):
                contador_tentativas += 1; continue 
            
            # dá um pequeno tempo pro React renderizar o erro
            time.sleep(3)

            # 🔍 DEBUG: texto visível na página inteira
            try:
                body_txt = page.ele('tag:body').text or ""
                # log_debug("BODY (primeiros 400 chars): " + body_txt[:400])
            except:
                pass

            
            tag_erro, texto_erro = capturar_erro_email(page)

            if texto_erro:
                # log_debug(f"ERRO NA TELA [{tag_erro}]: {texto_erro}")

                if tag_erro in ("DOMINIO_BLOQUEADO", "EMAIL_INVALIDO"):
                    dom = obj.email.split('@')[1].lower()
                    log_aviso(f"Email/domínio rejeitado ({dom}). Blacklistando domínio na sessão.")
                    dominios_banidos.add(dom)
                    contador_tentativas += 1
                    continue

                if tag_erro == "SEGURANCA_INSUFICIENTE":
                    log_aviso("Cloudflare falhou (Falso positivo). Recarregando...")
                    page.refresh()
                    continue

                if tag_erro == "EMAIL_EM_USO":
                    log_aviso("E-mail em uso.")
                    contador_tentativas += 1
                    continue


            print(f"   {Cores.CIANO}⏳ Aguardando e-mail...{Cores.RESET}", end="", flush=True)
            cod1 = None; start = time.time()
            
            while time.time() - start < 60:
                print(".", end="", flush=True)
                val = prov.esperar_codigo(obj, "Cadastro")
                if val:
                    cod1 = extrair_codigo_seguro(val)
                    if cod1: break
                time.sleep(4)
            
            if not cod1:
                dom_timeout = obj.email.split('@')[1].lower()
                log_aviso(f"Timeout Email. Domínio {dom_timeout} pode estar bloqueado para recebimento.")
                dominios_banidos.add(dom_timeout)
                contador_tentativas += 1; continue 
                
            print(f"\n   {Cores.VERDE}🔥 CÓDIGO: {cod1}{Cores.RESET}")
            page.ele('#authnumber').input(cod1)
            time.sleep(1)
            try: page.ele('text=Verificação concluída').click()
            except: pass
            
            senha = gerar_senha_ragnarok()
            page.ele('#password').input(senha); page.ele('#password2').input(senha)
            try: page.ele('.page_selectBtn__XfETd').click(); page.ele('text=Brasil').click()
            except: pass
            page.ele('#firstname').input("Jose"); page.ele('#lastname').input(CONF.get("sobrenome_padrao", "Silva"))
            page.ele('#birthday').input("01/01/1995")
            page.scroll.to_bottom()
            try: page.run_js("document.getElementById('terms1').click()"); page.run_js("document.getElementById('terms2').click()")
            except: pass
            
            clicar_com_seguranca(page, '.page_submitBtn__hk_C0', "Botão CONTINUAR")
            log_sucesso("Cadastro enviado!")
            
            # === LOGIN SUB-LOOP ===
            login_sucesso = False
            
            for tentativa_login in range(3):
                log_info(f"Tentativa de Login {tentativa_login+1}/3...")
                diagnostico_pagina(page)
                
                if "login.gnjoylatam" not in page.url:
                    page.get("https://login.gnjoylatam.com")
                    if not garantir_carregamento(page, '#email', timeout=20):
                        log_erro("Não carregou página de login. Tentando recarregar...")
                        continue

                vencer_cloudflare_obrigatorio(page)
                page.ele('#email').input(obj.email)
                page.ele('#password').input(senha)
                time.sleep(1)
                
                # log_debug("Enviando ENTER no campo de senha...")
                page.actions.key_down(Keys.ENTER).key_up(Keys.ENTER)
                time.sleep(2)
                
                if "login.gnjoylatam" in page.url:
                    # log_debug("ENTER não redirecionou. Tentando clique no botão...")
                    clicar_com_seguranca(page, '.page_loginBtn__JUYeS', "Botão Login (Classe)")
                
                # log_debug("Aguardando redirecionamento pós-login...")
                page.wait.url_change('login', timeout=20)
                
                page.get("https://www.gnjoylatam.com/pt")
                time.sleep(2)
                
                if page.ele('text:Logout') or page.ele('.header_logoutBtn__6Pv_m'):
                    log_sucesso("Sessão confirmada (Logout visível).")
                    login_sucesso = True
                    break 
                elif page.ele('.header_rightlist__btn__5cynY') or page.ele('text:Login'):
                    log_aviso("Login não persistiu. Tentando novamente...")
                else:
                    # log_debug("Estado incerto. Assumindo logado.")
                    login_sucesso = True
                    break

            if not login_sucesso:
                log_erro("Falha crítica no Login após 3 tentativas. Descartando conta.")
                contador_tentativas += 1; continue


            # === OTP ===
            page.get("https://www.gnjoylatam.com/pt")
            time.sleep(2)

            # abre o perfil (isso força o fluxo correto de sessão)
            if not clicar_com_seguranca(page, '.header_mypageBtn__cR1p3', "Perfil"):
                log_erro("Perfil não apareceu. Sessão pode não ter persistido.")
                contador_tentativas += 1
                continue

            # entra no menu OTP pelo fluxo normal
            if not clicar_com_seguranca(page, 'text=Conexão OTP', "Menu OTP"):
                log_erro("Não achou o menu 'Conexão OTP'.")
                contador_tentativas += 1
                continue

            # garante que está na URL certa
            if "gotp" not in page.url:
                page.get("https://member.gnjoylatam.com/pt/mypage/gotp")
                time.sleep(2)

            # agora sim, clica no botão
            if not clicar_botao_otp(page):
                log_erro("Não foi possível clicar no botão Solicitação de serviço OTP.")
                consolidar_conta_no_principal(obj.email, senha, seed="SEM_OTP")
                contador_tentativas += 1
                continue

            
            print(f"   {Cores.CIANO}⏳ Aguardando e-mail OTP...{Cores.RESET}", end="", flush=True)
            cod2 = None; start = time.time()
            
            # Espera o segundo e-mail
            while time.time() - start < 60:
                print(".", end="", flush=True)
                val = prov.esperar_codigo(obj, "OTP") # Filtro pode ser 'OTP' ou 'autenticação'
                if not val: val = prov.esperar_codigo(obj, "autenticação")
                
                if val:
                    cod2 = extrair_codigo_seguro(val)
                    if cod2: break
                time.sleep(4)

            if not cod2: 
                log_erro("Timeout esperando código OTP.")
                consolidar_conta_no_principal(obj.email, senha, seed="FALHA_EMAIL_OTP")
                contador_tentativas += 1; continue
            
            print(f"\n   {Cores.VERDE}🔥 OTP: {cod2}{Cores.RESET}")
            
            # Preenche o OTP na modal
            if page.ele('#authnumber'):
                page.ele('#authnumber').input(cod2)
                clicar_com_seguranca(page, 'text=Verificação concluída', "Validar OTP")
                time.sleep(3)
            
            # Captura a SEED
            ele_seed = page.wait.ele_displayed('.page_otp_key__nk3eO', timeout=TIMEOUT_PADRAO)
            if ele_seed:
                seed_text = ele_seed.text
                print(f"   💎 SEED: {Cores.AMARELO}{seed_text}{Cores.RESET}")
                
                if TEM_PYOTP:
                    totp = pyotp.TOTP(seed_text.replace(" ", ""))
                    # Preenche o código do autenticador para confirmar
                    inputs = page.eles('tag:input')
                    for i in inputs:
                        if i.states.is_displayed and not i.attr('disabled') and i.attr('type') == 'text':
                            i.input(totp.now()); break
                    
                    if clicar_com_seguranca(page, 'text=Confirme', "Confirme"):
                        clicar_com_seguranca(page, 'text=OK', "OK")
                        
                        status = "PRONTA_PARA_FARMAR"
                        salvar_conta_backup(obj.email, senha, seed_text, status)
                        consolidar_conta_no_principal(obj.email, senha, seed=seed_text)
                        
                        log_sucesso("CONTA FINALIZADA COM SUCESSO!")
                        return True, prov_class
                else:
                    # Sem PyOTP, salva apenas a seed para configurar depois
                    salvar_conta_backup(obj.email, senha, seed_text, status="FALTA_ATIVAR_APP")
                    consolidar_conta_no_principal(obj.email, senha, seed=seed_text)
                    return True, prov_class
            else:
                log_erro("Não foi possível capturar a SEED.")
                return False, ultimo_provedor_ok

        except Exception as e:
            log_erro(f"Erro no processo: {e}")
            contador_tentativas += 1
            
    return False, ultimo_provedor_ok

def verificar_licenca_online(tipo):
    try: from master import verificar_licenca_online as v; return v(tipo)
    except: return True

def main():
    if not verificar_licenca_online("fabricador"): return
    os.system('cls' if os.name == 'nt' else 'clear'); exibir_banner()
    
    # 1. CARREGA OS PROXIES
    lista_proxies = carregar_proxies_arquivo()
    usar_proxy = len(lista_proxies) > 0
    
    if usar_proxy:
        print(f"{Cores.VERDE}🔌 Proxies carregados: {len(lista_proxies)}{Cores.RESET}")
    else:
        print(f"{Cores.AMARELO}⚠️  Nenhum proxy encontrado em proxies.txt. Usando IP real.{Cores.RESET}")

    try: qtd = int(input(f"\n{Cores.AZUL}>> Quantas contas?: {Cores.RESET}").strip() or "1")
    except: qtd = 1
    
    print("\n>>> Inicializando Motor...")
    
    # Variáveis de controle global
    sucessos = 0
    ultimo_provedor_ok = None
    blacklist_global = set()

    # --- LOOP PRINCIPAL ---
    for i in range(qtd):
        print(f"\n{Cores.NEGRITO}{Cores.AZUL}=== CONTA {i+1} DE {qtd} ==={Cores.RESET}")

        proxy_string = None
        proxy_requests = None

        # 2. CONFIGURA O PROXY DA VEZ
        if usar_proxy:
            # Pega o proxy bruto do arquivo
            proxy_string_bruta = lista_proxies[i % len(lista_proxies)]
            
            # Formata corretamente (Isso resolve o erro da tela preta!)
            proxy_config = formatar_proxy_requests(proxy_string_bruta)
            proxy_url = proxy_config['http'] # Pega a string 'http://user:pass@ip:port'
            
            # Passa o dicionário para a função de criar conta (Requests)
            proxy_requests = proxy_config
            
            print(f"{Cores.CINZA}🛡️  Usando Proxy: {proxy_string_bruta}{Cores.RESET}")
        
        # 3. CONFIGURA O NAVEGADOR
        co = ChromiumOptions()
        co.set_argument('--start-maximized')
        
        if proxy_string:
            # AQUI ESTÁ A CORREÇÃO CRÍTICA:
            # Usamos proxy_url (formatado) e não proxy_string (bruto)
            # O DrissionPage/Chrome precisa de http://user:pass@ip:port
            co.set_argument(f'--proxy-server={proxy_url}')
            
        if CONF.get("headless", False): co.headless(True)
        
        # Inicia o navegador com o IP novo
        page = ChromiumPage(addr_or_opts=co)

        # 4. CHAMA A CRIAÇÃO DE CONTA PASSANDO O PROXY
        try:
            # Atenção: Atualize a definição de 'criar_conta' para aceitar 'proxy_requests'
            ok, prov_ok = criar_conta(page, blacklist_global, proxy_requests, ultimo_provedor_ok)

            if ok:
                sucessos += 1
                if ultimo_provedor_ok is None: ultimo_provedor_ok = prov_ok
                print(f"{Cores.VERDE}✅ Sucesso!{Cores.RESET}")
            else:
                print(f"{Cores.VERMELHO}❌ Falha.{Cores.RESET}")

        except Exception as e:
            log_erro(f"Erro fatal no loop: {e}")

        # 5. FECHA O NAVEGADOR PARA LIMPAR A SESSÃO E O PROXY
        page.quit()

        # Resfriamento entre contas (só se não for a última)
        if i < qtd - 1:
            tempo = random.randint(15, 25)
            barra_progresso(tempo, prefixo='Trocando IP', sufixo='s')

    msg = f"Fim. Sucessos: {sucessos}/{qtd}"
    print(f"\n{Cores.NEGRITO}=== {msg} ==={Cores.RESET}")
    enviar_telegram(msg)
    
    # ... (Bloco de iniciar o farm checkin_bot_v2 continua igual) ...
    if sucessos > 0:
        print(f"\n{Cores.CIANO}🚀 Iniciando Farm...{Cores.RESET}"); barra_progresso(15, prefixo='Carregando', sufixo='s')
        try:
            import checkin_bot_v2
            # ... (Lógica de salvar no accounts.json mantida) ...
            try:
                with open(ARQUIVO_SALVAR, "r") as f: novas = json.load(f)
                if os.path.exists(ARQUIVO_PRINCIPAL):
                    with open(ARQUIVO_PRINCIPAL, "r") as f: principais = json.load(f)
                else: principais = []
                existentes = set(c['email'] for c in principais)
                for n in novas:
                    if n['email'] not in existentes: principais.append(n)
                with open(ARQUIVO_PRINCIPAL, "w") as f: json.dump(principais, f, indent=4)
            except: pass
            
            checkin_bot_v2.executar()
        except: pass
    else: input("\nEnter...")

def executar(): main()

if __name__ == "__main__": main()