import time
import re
import requests
import random
import string
import json
import os
import html
import shutil
import zipfile
import unicodedata
import sys
from urllib.parse import quote
from urllib.parse import quote
from datetime import datetime
from DrissionPage import ChromiumPage, ChromiumOptions
from DrissionPage.common import Keys

# ==========================================
# ⚙️ CONFIGURAÇÕES DE TESTE
# ==========================================
MODO_ECONOMICO = True
# ==========================================


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

os.system('') # Enables ANSI colors in CMD

def criar_extensao_proxy(proxy_user, proxy_pass, pasta_destino="."):
    """
    Cria uma extensão MINIMALISTA apenas para autenticação (User/Pass).
    O IP e Porta serão definidos via argumento --proxy-server.
    """
    manifest_json = """
    {
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "Chrome Proxy Auth",
        "permissions": [
            "proxy", "tabs", "unlimitedStorage", "storage", "<all_urls>", "webRequest", "webRequestBlocking"
        ],
        "background": {
            "scripts": ["background.js"]
        },
        "minimum_chrome_version": "22.0.0"
    }
    """

    # Note que removemos a parte de "config = ..."
    # Agora só tem o listener para digitar a senha
    background_js = f"""
    function callbackFn(details) {{
        return {{
            authCredentials: {{
                username: "{proxy_user}",
                password: "{proxy_pass}"
            }}
        }};
    }}

    chrome.webRequest.onAuthRequired.addListener(
        callbackFn,
        {{urls: ["<all_urls>"]}},
        ['blocking']
    );
    """

    # Nome aleatório para evitar conflito
    import random
    nome_pasta = f"auth_plugin_{random.randint(10000, 99999)}"
    caminho_pasta = os.path.join(pasta_destino, nome_pasta)
    
    if not os.path.exists(caminho_pasta):
        os.makedirs(caminho_pasta)

    with open(os.path.join(caminho_pasta, "manifest.json"), "w", encoding="utf-8") as f:
        f.write(manifest_json)
        
    with open(os.path.join(caminho_pasta, "background.js"), "w", encoding="utf-8") as f:
        f.write(background_js)
    
    return os.path.abspath(caminho_pasta)

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
TEM_PROXIES_CARREGADOS = False


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
import re
import unicodedata

def extrair_codigo_seguro(texto_bruto):
    if not texto_bruto:
        return None

    # 1) Limpeza pesada + normalização
    texto = limpar_html(texto_bruto).replace('&nbsp;', ' ')
    texto = unicodedata.normalize("NFKC", texto)

    # 2) Remover cabeçalhos comuns (muito importante no seu caso)
    # Se tiver um bloco de headers e depois uma linha em branco, mantém só depois da linha em branco.
    # (Em muitos bodies “crus”, o conteúdo útil vem depois do primeiro \n\n.)
    partes = re.split(r"\r?\n\r?\n", texto, maxsplit=1)
    if len(partes) == 2:
        texto_body = partes[1]
    else:
        texto_body = texto

    # 3) Compacta espaços
    texto_body = re.sub(r"[ \t]+", " ", texto_body).strip()

    BLACKLIST = {
        'abaixo','assets','height','width','style','script','border',
        'verifi','cation','segura','access','bottom','center','family',
        'follow','format','ground','header','online','public','select',
        'server','sign','simple','source','strong','target','title',
        'window','yellow','codigo'
    }

    # --- ESTRATÉGIA 0: Template "Código de Verificação" na linha + código na linha abaixo ---
    m = re.search(
        r'c[oó]digo\s+de\s+verifica[cç][aã]o\s*[\r\n]+([A-Za-z0-9]{6})\b',
        texto_body,
        re.IGNORECASE
    )
    if m:
        cod = m.group(1).strip()
        if cod.lower() not in BLACKLIST:
            return cod

    # (opcional) versão em inglês
    m = re.search(
        r'verification\s+code\s*[\r\n]+([A-Za-z0-9]{6})\b',
        texto_body,
        re.IGNORECASE
    )
    if m:
        cod = m.group(1).strip()
        if cod.lower() not in BLACKLIST:
            return cod

    # --- ESTRATÉGIA 1: Código misto (letra+número), MAS evita capturar de linhas “técnicas” ---
    # Regra prática: só procura em linhas que não parecem header.
    linhas = [ln.strip() for ln in re.split(r"\r?\n", texto_body) if ln.strip()]
    linhas_filtradas = []
    for ln in linhas:
        low = ln.lower()
        if low.startswith(("message-id:", "date:", "feedback-id:", "from:", "to:", "subject:", "mime-version:", "content-")):
            continue
        linhas_filtradas.append(ln)
    texto_sem_headers = "\n".join(linhas_filtradas)

    m = re.search(r'\b(?=[A-Za-z0-9]*\d)(?=[A-Za-z0-9]*[A-Za-z])[A-Za-z0-9]{6}\b', texto_sem_headers)
    if m:
        return m.group(0)

    # --- ESTRATÉGIA 2: Contexto "Código/Code/OTP" + próximo token 6 chars (sem exigir ":") ---
    m = re.search(
        r'(?:c[oó]digo|code|otp)\s*(?:de\s*verifica[cç][aã]o|verification)?\s*[:\-=\s]*\s*([A-Za-z0-9]{6})\b',
        texto_sem_headers,
        re.IGNORECASE
    )
    if m:
        cod = m.group(1).strip()
        if cod.lower() not in BLACKLIST:
            return cod

    # --- ESTRATÉGIA 3: Numérico puro ---
    m = re.search(r'\b\d{6}\b', texto_sem_headers)
    if m:
        return m.group(0)

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
    global TENTATIVAS_BLOQUEIO_IP, TEM_PROXIES_CARREGADOS

    try:
        # Verifica sinais de bloqueio 429
        # (Adicionei verificação de None para evitar erros se o body não carregar)
        body_ele = page.ele('tag:body')
        body_txt = body_ele.text.lower() if body_ele else ""
        title_txt = page.title.lower() if page.title else ""

        if "429" in title_txt or "too many requests" in body_txt:
            
            # === CENÁRIO 1: AUTOMÁTICO (TEM LISTA DE PROXY) ===
            if TEM_PROXIES_CARREGADOS:
                # Lança o erro específico. O Main vai pegar isso, fechar o browser
                # e abrir o próximo proxy da lista imediatamente.
                raise Exception("IP_BLOCKED_429")

            # === CENÁRIO 2: MANUAL (SEM LISTA, IP RESIDENCIAL/VPN) ===
            else:
                TENTATIVAS_BLOQUEIO_IP += 1
                print(f"\n{Cores.VERMELHO}🚨 BLOQUEIO DE IP (429) DETECTADO!{Cores.RESET}")
                print(f"{Cores.AMARELO}   Como você não está usando lista de proxies, precisa trocar o IP manualmente.{Cores.RESET}")
                
                if TENTATIVAS_BLOQUEIO_IP >= MAX_BLOQUEIOS_IP:
                    print(f"{Cores.VERMELHO}❌ Limite de tentativas manuais excedido.{Cores.RESET}")
                    page.quit()
                    os._exit(1)

                # Trava a tela e espera o usuário dar Enter
                input(f"\n{Cores.VERDE}>>> Troque o IP (VPN/Modem) e pressione ENTER para tentar de novo...{Cores.RESET}")
                
                try: page.refresh()
                except: pass
                
                time.sleep(5)
                return True

    except Exception as e:
        # Se for o nosso erro de troca automática, deixa subir para o Main pegar
        if "IP_BLOCKED_429" in str(e):
            raise e
        # Outros erros de leitura de página ignoramos
        # log_debug(f"Erro checando bloqueio IP: {e}")
        pass

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


# Nome do arquivo de texto para bloqueios manuais
ARQUIVO_BLACKLIST = "blacklist_dominios.txt"

class ProviderMailTM:
    def __init__(self, proxy_dict=None):
        self.proxies = proxy_dict
        self.base_url = "https://api.mail.tm"
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    def _request(self, method, endpoint, data=None, auth_token=None):
        url = f"{self.base_url}{endpoint}"
        h = self.headers.copy()
        if auth_token:
            h["Authorization"] = f"Bearer {auth_token}"
            
        try:
            if method == "GET":
                r = requests.get(url, headers=h, proxies=self.proxies, timeout=15)
            else:
                r = requests.post(url, headers=h, json=data, proxies=self.proxies, timeout=15)
            
            if r.status_code in [200, 201]:
                return r.json()
        except Exception as e:
            print(f"{Cores.VERMELHO}[DEBUG CONEXAO] Erro: {e}{Cores.RESET}")
            pass
        return None

    def gerar(self, banidos=[]):
        obj = EmailSession()
        obj.provider_name = "MailTM" # ou GW, ele ajusta depois
        
        # 1. Pega a lista de domínios
        data_domains = self._request("GET", "/domains")
        if not data_domains: 
            return None
        
        raw_list = []
        if isinstance(data_domains, list):
            raw_list = data_domains
        elif isinstance(data_domains, dict):
            raw_list = data_domains.get('hydra:member', [])

        available_domains = [d.get('domain') for d in raw_list if isinstance(d, dict) and 'domain' in d]
        
        # [DEBUG 2] Mostra EXATAMENTE quais domínios a API entregou
        print(f"{Cores.CIANO}[DEBUG] Domínios disponíveis na API: {available_domains}{Cores.RESET}")

        valid_domains = [d for d in available_domains if d not in banidos]
        
        if not valid_domains: 
            print(f"{Cores.AMARELO}[DEBUG] Todos os domínios foram filtrados pela sua blacklist/banidos.{Cores.RESET}")
            return None
        
        # ... o resto continua igual ...
        domain = random.choice(valid_domains)
        username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
        email = f"{username}@{domain}"
        
        account_data = {"address": email, "password": password}
        
        reg_resp = self._request("POST", "/accounts", data=account_data)
        if not reg_resp: return None
        
        token_resp = self._request("POST", "/token", data=account_data)
        if token_resp and 'token' in token_resp:
            obj.email = email
            obj.password = password
            obj.extra_data = {'token': token_resp['token'], 'id': reg_resp.get('id')}
            return obj
            
        return None

    def esperar_codigo(self, obj_email, filtro_assunto=""):
        if not obj_email or not obj_email.extra_data.get('token'):
            return None
            
        token = obj_email.extra_data['token']
        
        # Busca mensagens
        msgs_data = self._request("GET", "/messages", auth_token=token)
        if not msgs_data: return None
        
        # === CORREÇÃO TAMBÉM NO LER MENSAGENS ===
        msg_list = []
        if isinstance(msgs_data, list):
            msg_list = msgs_data
        elif isinstance(msgs_data, dict):
            msg_list = msgs_data.get('hydra:member', [])
        # ========================================
        
        for msg in msg_list:
            subject = msg.get('subject', '')
            
            if not filtro_assunto or filtro_assunto.lower() in subject.lower():
                msg_id = msg.get('id')
                full_msg = self._request("GET", f"/messages/{msg_id}", auth_token=token)
                
                if full_msg:
                    return full_msg.get('html') or full_msg.get('text') or ""
        
        return None


# --- CLASSE DO MAIL.GW (Cópia da MailTM com URL nova) ---
class ProviderMailGW(ProviderMailTM):
    def __init__(self, proxy_dict=None):
        super().__init__(proxy_dict)
        # A ÚNICA DIFERENÇA É ESSA URL:
        self.base_url = "https://api.mail.gw" 
        # O resto ele herda tudo do pai (ProviderMailTM)
    
    def gerar(self, banidos=[]):
        # Precisamos sobrescrever o gerar apenas para mudar o provider_name
        # e garantir que ele chame o gerar da classe pai corretamente
        obj = super().gerar(banidos)
        if obj:
            obj.provider_name = "MailGW"
        return obj



# ==============================================================================
# 3. CLASSE GUERRILLA MAIL (A Salvação do Volume)
# ==============================================================================
class ProviderGuerrilla:
    def __init__(self, proxy_dict=None):
        self.proxies = proxy_dict
        # API antiga, mas robusta
        self.base_url = "https://api.guerrillamail.com/ajax.php"

    def gerar(self, banidos=[]):
        obj = EmailSession()
        obj.provider_name = "Guerrilla"
        
        try:
            # Guerrilla cria o email automaticamente ao pedir 'get_email_address'
            params = {'f': 'get_email_address'}
            
            # Timeout maior (20s) porque o Guerrilla as vezes é lento
            r = requests.get(self.base_url, params=params, proxies=self.proxies, timeout=20)
            data = r.json()
            
            email = data.get('email_addr')
            sid_token = data.get('sid_token') # O "Crachá" da sessão
            
            if not email: return None

            # Verifica se o domínio está na blacklist
            dominio = email.split('@')[1]
            if dominio in banidos:
                # Dica: O Guerrilla permite trocar o domínio com 'set_email_user',
                # mas para manter simples, vamos descartar e tentar de novo.
                return None
            
            obj.email = email
            # Guerrilla não tem senha, usa o SID_TOKEN para ler a caixa
            obj.password = "sem_senha" 
            obj.extra_data = {'sid_token': sid_token}
            
            return obj
            
        except Exception:
            pass
        return None

    def esperar_codigo(self, obj_email, filtro_assunto=""):
        if not obj_email or not obj_email.extra_data.get('sid_token'):
            return None
            
        sid = obj_email.extra_data['sid_token']
        # 'seq': '0' pede mensagens novas a partir do ID 0
        params = {'f': 'check_email', 'sid_token': sid, 'seq': '0'} 
        
        try:
            r = requests.get(self.base_url, params=params, proxies=self.proxies, timeout=15)
            data = r.json()
            msgs = data.get('list', [])
            
            for m in msgs:
                subject = m.get('mail_subject', '')
                
                # Ignora o e-mail de boas-vindas do próprio Guerrilla
                if 'Welcome' in subject: continue
                
                # O Guerrilla retorna 'mail_excerpt' (resumo do texto)
                # O Ragnarok manda o código logo no começo, então o resumo geralmente serve!
                if not filtro_assunto or filtro_assunto.lower() in subject.lower():
                    excerpt = m.get('mail_excerpt', '')
                    
                    # Tenta achar os 6 números direto no resumo (economiza 1 request)
                    import re
                    match = re.search(r'(?<!\d)(\d{6})(?!\d)', excerpt)
                    if match:
                        return match.group(0) # Retorna o código direto se achar
                    
                    # Se não achou no resumo, baixa o corpo completo
                    mail_id = m.get('mail_id')
                    p_body = {'f': 'fetch_email', 'sid_token': sid, 'email_id': mail_id}
                    r_body = requests.get(self.base_url, params=p_body, proxies=self.proxies)
                    body_data = r_body.json()
                    
                    return body_data.get('mail_body', '')
                    
        except Exception:
            pass
        return None



class ProviderMailTempSite:
    def __init__(self, proxy_dict=None):
        self.proxies = proxy_dict
        
        # 1. Lista Fixa (Hardcoded) - O básico que já sabemos
        self.BLACKLIST_INTERNA = {
            "mail-temp.site", "onesecsmail.xyz", "onesecsmail.info", "onesecsmail.com", 
            "onesecsmail.top", "1secmail.asia", "1secmail.online", "1secmail.top", 
            "1secmail.store", "1secmail.co", "1secmail.info", "destroismails.com", 
            "destroismails.xyz", "destroismails.fun", "destroismails.info", 
            "onetimesmail.store", "onetimesmail.site", "onetimesmail.fun", 
            "onetimesmail.info", "onetimesmail.xyz", "top1tlc.com", "top2tlc.com", 
            "top3tlc.com", "dinlaan.uk", "leedonganh.com", "vietquang.online", 
            "tuantr.shop"
        }
        
        # 2. Lista Externa (Lê do arquivo txt)
        self.BLACKLIST_EXTERNA = self.carregar_blacklist_txt()
        
        # 3. Combina as duas (União de Conjuntos)
        self.BLACKLIST_TOTAL = self.BLACKLIST_INTERNA.union(self.BLACKLIST_EXTERNA)
        
        # Debug para você saber quantos domínios estão bloqueados
        # print(f"DEBUG: Blacklist carregada com {len(self.BLACKLIST_TOTAL)} domínios.")

    def carregar_blacklist_txt(self):
        """Lê o arquivo blacklist_dominios.txt e retorna um set limpo"""
        bloqueados = set()
        if os.path.exists(ARQUIVO_BLACKLIST):
            try:
                with open(ARQUIVO_BLACKLIST, "r", encoding="utf-8") as f:
                    for linha in f:
                        # 1. Tira espaços em branco do começo e fim
                        # 2. Converte para minúsculo
                        # 3. Remove o '@' se o usuário tiver colocado sem querer
                        dominio = linha.strip().lower().replace("@", "")
                        
                        if dominio and not dominio.startswith("#"):
                            bloqueados.add(dominio)
            except Exception as e:
                print(f"{Cores.AMARELO}⚠️ Erro ao ler blacklist externa: {e}{Cores.RESET}")
        return bloqueados

    def gerar(self, banidos=[]):
        obj = EmailSession()
        obj.provider_name = "MailTempSite"
        tag = CONF.get("tag_email", "rag")
        
        try:
            # Solicita lista de domínios para a API
            r = requests.get("https://mail-temp.site/list_domain.php", headers=API_HEADERS, proxies=self.proxies, timeout=15)
            data = r.json()
            
            if data.get('success'):
                # === FILTRAGEM TURBINADA ===
                # Remove se estiver na lista de banidos da sessão (runtime)
                # E remove se estiver na BLACKLIST_TOTAL (código + arquivo txt)
                doms = [
                    d for d in data.get('domains', []) 
                    if d not in banidos and d not in self.BLACKLIST_TOTAL
                ]
                
                if doms:
                    domain = random.choice(doms)
                    sulfixo = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
                    obj.email = f"{tag}_{sulfixo}@{domain}"
                    return obj
                else:
                    # Se caiu aqui, é porque TODOS os domínios que a API ofereceu são ruins
                    # O main vai receber None, esperar 1s e tentar de novo.
                    # Talvez na proxima tentativa a API mande outros dominios.
                    return None

        except Exception:
            pass
            
        return None

    def esperar_codigo(self, obj, filtro):
        try:
            # garante o estado
            if not hasattr(obj, "seen_ids"):
                obj.seen_ids = set()

            url = f"https://mail-temp.site/checkmail.php?mail={quote(obj.email)}"
            r = requests.get(url, headers=API_HEADERS, proxies=self.proxies, timeout=15)
            data = r.json()

            if not data.get("success"):
                return None

            emails = data.get("emails") or []

            # 🔥 DEBUG: imprime SOMENTE quando surgir ID novo
            novos = []
            for m in emails:
                mid = m.get("id")
                if mid and mid not in obj.seen_ids:
                    novos.append((mid, m.get("subject") or ""))

            if novos:
                print(f"\n[DEBUG {filtro.upper()} NOVOS EMAILS] {novos}", end="")

            # processa apenas novos (evita reler os mesmos)
            for msg in emails:
                mid = msg.get("id")
                if not mid or mid in obj.seen_ids:
                    continue

                obj.seen_ids.add(mid)  # marca como visto assim que encostar nele

                subject = (msg.get("subject") or "").lower()

                # filtro
                if filtro.lower() in subject:
                    r2 = requests.get(
                        f"https://mail-temp.site/viewmail.php?id={mid}",
                        headers=API_HEADERS,
                        proxies=self.proxies,
                        timeout=15
                    )
                    data2 = r2.json()
                    if not data2.get("success"):
                        continue

                    raw_body = data2.get("email", {}).get("body", "")
                    body_limpo = html.unescape(raw_body)

                    # print(f"\n[DEBUG {filtro.upper()} BODY HEAD] {body_limpo[:160]}", end="")
                    return body_limpo

        except Exception as e:
            pass
            # print(f"\n[DEBUG BODY LEN] {len(body_limpo)}")
            # print(f"\n[DEBUG BODY SAMPLE]\n{body_limpo[:2000]}\n")


        return None


# --- MAIN LOOP ---
def criar_conta(page, blacklist_global, proxy_dict, ultimo_provedor_ok=None):
    garantir_logout(page)
    dominios_banidos = blacklist_global
    # provedores_disponiveis = [ProviderGuerrilla, ProviderMailTM, Provider1SecMail, ProviderMailTempSite]
    provedores_disponiveis = [ProviderMailTempSite]

    # Se o último que funcionou foi um deles, joga ele pro topo da lista
    if ultimo_provedor_ok in provedores_disponiveis:
         # Prioriza o que deu certo na última conta
        provedores_disponiveis.remove(ultimo_provedor_ok)
        provedores_disponiveis.insert(0, ultimo_provedor_ok)

    contador_tentativas = 0
    
    while contador_tentativas < 15:
        if contador_tentativas > 0:
            print(f"\n{Cores.AMARELO}♻️  Nova Tentativa ({contador_tentativas+1})...{Cores.RESET}")
            garantir_logout(page)
            
        prov_class = provedores_disponiveis[contador_tentativas % len(provedores_disponiveis)]
        log_info(f"Gerando identidade via: {Cores.MAGENTA}{prov_class.__name__}{Cores.RESET}...")
        
        prov = prov_class(proxy_dict=proxy_dict)

        # === [ADICIONADO] LOOP DE TENTATIVA DE EMAIL (Economia de Dados) ===
        # Tenta pegar um e-mail válido 5 vezes antes de desistir e trocar de provedor
        obj = None
        for _ in range(5):
            obj = prov.gerar(banidos=list(dominios_banidos))
            if obj: break # Sucesso!
            time.sleep(1) # Espera 1s para não floodar a API
        # ===================================================================
        
        if not obj:
            log_debug("Provedor não tem domínios disponíveis/limpos após 5 tentativas. Trocando...")
            contador_tentativas += 1
            continue

        log_sucesso(f"E-mail Gerado: {Cores.NEGRITO}{obj.email}{Cores.RESET}")
        
        try:
            log_info("Acessando Cadastro...")
            page.get("https://member.gnjoylatam.com/pt/join")
            
            # === [ADICIONADO] FAIL FAST (Economia de Tempo) ===
            # Se der 403 Forbidden, detecta agora e troca o proxy IMEDIATAMENTE
            checar_bloqueio_ip(page) 
            # ==================================================
            
            if not garantir_carregamento(page, '#email', timeout=30):
                # Se deu timeout, confere se não foi bloqueio que apareceu depois
                checar_bloqueio_ip(page)
                log_erro("Timeout carregando formulário. Site lento ou fora do ar.")
                contador_tentativas += 1; continue

            if not vencer_cloudflare_obrigatorio(page):
                log_erro("Cloudflare barrou. Reiniciando página...")
                page.refresh(); continue
            
            page.ele('#email').click(); page.ele('#email').clear(); page.ele('#email').input(obj.email)
            delay_humano()

            medir_consumo(page, "Página Cadastro")
            
            if not clicar_com_seguranca(page, 'text=Enviar verificação', "Botão Enviar"):
                contador_tentativas += 1; continue 
            
            # dá um pequeno tempo pro React renderizar o erro
            time.sleep(3)

            # 🔍 DEBUG: texto visível na página inteira
            try:
                body_txt = page.ele('tag:body').text or ""
            except:
                pass

            
            tag_erro, texto_erro = capturar_erro_email(page)

            if texto_erro:
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

                medir_consumo(page, "Página Login")
                
                page.actions.key_down(Keys.ENTER).key_up(Keys.ENTER)
                time.sleep(2)
                
                if "login.gnjoylatam" in page.url:
                    clicar_com_seguranca(page, '.page_loginBtn__JUYeS', "Botão Login (Classe)")
                
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
                    login_sucesso = True
                    break

            if not login_sucesso:
                log_erro("Falha crítica no Login após 3 tentativas. Descartando conta.")
                contador_tentativas += 1; continue


            # === OTP ===
            page.get("https://www.gnjoylatam.com/pt")
            time.sleep(2)

            if not clicar_com_seguranca(page, '.header_mypageBtn__cR1p3', "Perfil"):
                log_erro("Perfil não apareceu. Sessão pode não ter persistido.")
                contador_tentativas += 1
                continue

            if not clicar_com_seguranca(page, 'text=Conexão OTP', "Menu OTP"):
                log_erro("Não achou o menu 'Conexão OTP'.")
                contador_tentativas += 1
                continue

            if "gotp" not in page.url:
                page.get("https://member.gnjoylatam.com/pt/mypage/gotp")
                time.sleep(3)

            if not clicar_botao_otp(page):
                log_erro("Não foi possível clicar no botão Solicitação de serviço OTP.")
                consolidar_conta_no_principal(obj.email, senha, seed="SEM_OTP")
                contador_tentativas += 1
                continue

            
            print(f"   {Cores.CIANO}⏳ Aguardando e-mail OTP...{Cores.RESET}", end="", flush=True)
            cod2 = None; start = time.time()
            
            while time.time() - start < 60:
                print(".", end="", flush=True)
                val = prov.esperar_codigo(obj, "OTP")
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
            
            if page.ele('#authnumber'):
                page.ele('#authnumber').input(cod2)
                clicar_com_seguranca(page, 'text=Verificação concluída', "Validar OTP")
                time.sleep(3)
            
            ele_seed = page.wait.ele_displayed('.page_otp_key__nk3eO', timeout=TIMEOUT_PADRAO)
            if ele_seed:
                seed_text = ele_seed.text
                print(f"   💎 SEED: {Cores.AMARELO}{seed_text}{Cores.RESET}")
                
                if TEM_PYOTP:
                    totp = pyotp.TOTP(seed_text.replace(" ", ""))
                    inputs = page.eles('tag:input')
                    for i in inputs:
                        if i.states.is_displayed and not i.attr('disabled') and i.attr('type') == 'text':
                            i.input(totp.now()); break
                    
                    if clicar_com_seguranca(page, 'text=Confirme', "Confirme"):
                        clicar_com_seguranca(page, 'text=OK', "OK")
                        
                        medir_consumo(page, "Fluxo OTP e Finalização")
                        print(f"{Cores.NEGRITO}💰 Custo Total desta Conta: {ACUMULADO_MB:.3f} MB{Cores.RESET}")

                        status = "PRONTA_PARA_FARMAR"
                        salvar_conta_backup(obj.email, senha, seed_text, status)
                        consolidar_conta_no_principal(obj.email, senha, seed=seed_text)
                        
                        log_sucesso("CONTA FINALIZADA COM SUCESSO!")
                        return True, prov_class
                else:
                    salvar_conta_backup(obj.email, senha, seed_text, status="FALTA_ATIVAR_APP")
                    consolidar_conta_no_principal(obj.email, senha, seed=seed_text)
                    return True, prov_class
            else:
                log_erro("Não foi possível capturar a SEED.")
                return False, ultimo_provedor_ok

        except Exception as e:
            # Se o erro for de IP, NÃO engula o erro. Jogue para cima!
            if "IP_BLOCKED_429" in str(e):
                raise e 
            
            log_erro(f"Erro no processo: {e}")
            contador_tentativas += 1
            
    return False, ultimo_provedor_ok

def verificar_licenca_online(tipo):
    try: from master import verificar_licenca_online as v; return v(tipo)
    except: return True

def main():
    if not verificar_licenca_online("fabricador"): return
    os.system('cls' if os.name == 'nt' else 'clear'); exibir_banner()

    global TEM_PROXIES_CARREGADOS
    
    # 1. CARREGA PROXIES E EMBARALHA
    lista_proxies = carregar_proxies_arquivo()
    if lista_proxies:
        random.shuffle(lista_proxies)
        TEM_PROXIES_CARREGADOS = True
        print(f"{Cores.VERDE}🔌 Proxies carregados: {len(lista_proxies)} (Modo Automático Ativo){Cores.RESET}")
    else:
        TEM_PROXIES_CARREGADOS = False
        print(f"{Cores.AMARELO}⚠️  Nenhum proxy encontrado. (Modo Manual Ativo){Cores.RESET}")

    try: qtd = int(input(f"\n{Cores.AZUL}>> Quantas contas?: {Cores.RESET}").strip() or "1")
    except: qtd = 1
    
    print("\n>>> Inicializando Motor...")
    
    sucessos = 0
    ultimo_provedor_ok = None
    blacklist_global = set()

    # Contador global para ir rotacionando a lista a cada tentativa
    contador_global_proxies = 0

    # --- LOOP PRINCIPAL (CONTAS) ---
    for i in range(qtd):
        print(f"\n{Cores.NEGRITO}{Cores.AZUL}=== CONTA {i+1} DE {qtd} ==={Cores.RESET}")

        tentativas_proxy = 0
        
        # Loop infinito para insistir na MESMA conta se o IP for bloqueado
        while True:
            # Trava de segurança para não ficar num loop infinito eterno
            if tentativas_proxy > 10:
                print(f"{Cores.VERMELHO}Muitos proxies falharam nesta conta. Pulando...{Cores.RESET}")
                break

            # ==============================================================================
            # 1. PREPARAÇÃO
            # ==============================================================================
            proxy_requests = None
            proxy_url_chrome = None
            
            if TEM_PROXIES_CARREGADOS and lista_proxies:
                proxy_bruto = lista_proxies[contador_global_proxies % len(lista_proxies)]
                contador_global_proxies += 1
                
                dados_proxy = formatar_proxy_requests(proxy_bruto)
                proxy_requests = dados_proxy 
                proxy_url_chrome = dados_proxy['url_formatada'] 
                
                print(f"{Cores.CINZA}🛡️  Usando Proxy: {proxy_url_chrome} (Tentativa {tentativas_proxy+1}){Cores.RESET}")

            # ==============================================================================
            # 2. ABRE O NAVEGADOR (MÉTODO BLINDADO / HÍBRIDO)
            # ==============================================================================
            co = ChromiumOptions()
            co.set_argument('--start-maximized')

            # === AQUI ESTÁ A MÁGICA ===
            if MODO_ECONOMICO:
                print(f"{Cores.AMARELO}🙈 MODO ECONÔMICO ATIVO: Imagens desligadas!{Cores.RESET}")
                
                # 1. Bloqueia download de Imagens (A maior economia)
                # co.set_argument('--blink-settings=imagesEnabled=false')
                
                # 2. (Opcional) Tenta bloquear outros recursos pesados, mas cuidado pra não quebrar o site
                # co.set_argument('--disable-gpu') 
    # ===========================
            
            plugin_path = None

            if proxy_requests: 
                import urllib.parse
                try:
                    # Desmonta a URL para pegar as partes
                    parsed = urllib.parse.urlparse(proxy_requests['http'])
                    p_host = parsed.hostname
                    p_port = parsed.port
                    p_user = parsed.username
                    p_pass = parsed.password
                    
                    # 1. FORÇA O PROXY VIA COMANDO (Isso evita vazamento de IP)
                    co.set_argument(f"--proxy-server={p_host}:{p_port}")
                    
                    # 2. CRIA EXTENSÃO SÓ PARA A SENHA
                    plugin_path = criar_extensao_proxy(p_user, p_pass)
                    co.add_extension(plugin_path)
                    
                    print(f"{Cores.CINZA}🛡️  Proxy Blindado Ativo: {p_host}:{p_port}{Cores.RESET}")

                except Exception as e:
                    print(f"{Cores.VERMELHO}Erro crítico no proxy: {e}{Cores.RESET}")
                    # Se falhar a montagem, tenta sem nada (vai usar IP real, mas avisa)
                    pass

            if CONF.get("headless", False): co.headless(True)
            
            # Inicia o navegador
            page = ChromiumPage(addr_or_opts=co)

            if CONF.get("headless", False): co.headless(True)
    
            # Inicia o navegador (Com imagens LIGADAS no motor, para enganar o Cloudflare)
            page = ChromiumPage(addr_or_opts=co)

            # === [NOVO] ECONOMIA INTELIGENTE (Bloqueio via Rede) ===
            # Isso impede o download dos arquivos, mas não quebra o motor de renderização
            try:
                page.run_cdp('Network.enable')
                
                # A MUDANÇA ESTÁ AQUI EMBAIXO: urls=[...] em vez de {'urls': [...]}
                page.run_cdp('Network.setBlockedURLs', urls=[
                    "*.jpg", "*.jpeg", "*.png", "*.gif", "*.webp",  # Imagens
                    "*.woff", "*.woff2", "*.ttf", "*.otf",          # Fontes (Pesadas!)
                    "*.mp4", "*.webm", "*.avi",                     # Vídeos
                    "*.ico", "*.svg"                                # Ícones
                ])
                print(f"{Cores.AMARELO}🛡️  Filtro de Rede Ativo: Bloqueando recursos pesados.{Cores.RESET}")
            except Exception as e:
                print(f"{Cores.VERMELHO}Erro ao configurar bloqueio de rede: {e}{Cores.RESET}")

            # ==============================================================================
            # 3. TENTA CRIAR A CONTA
            # ==============================================================================
            try:
                # Executa a criação (apenas UMA vez)
                ok, prov_ok = criar_conta(page, blacklist_global, proxy_requests, ultimo_provedor_ok)
                
                # Fecha o navegador
                page.quit() 
                
                # Faxina da extensão
                if plugin_path and os.path.exists(plugin_path):
                    try: shutil.rmtree(plugin_path)
                    except: pass

                if ok:
                    sucessos += 1
                    if ultimo_provedor_ok is None: ultimo_provedor_ok = prov_ok
                    print(f"{Cores.VERDE}✅ Sucesso!{Cores.RESET}")
                else:
                    print(f"{Cores.VERMELHO}❌ Falha na criação.{Cores.RESET}")

                # Sai do while True e vai para a próxima conta
                break 

            except Exception as e:
                # ==============================================================================
                # 4. TRATAMENTO DE ERRO (IP BLOCK)
                # ==============================================================================
                try: page.quit()
                except: pass
                
                if plugin_path and os.path.exists(plugin_path):
                    try: shutil.rmtree(plugin_path)
                    except: pass

                if "IP_BLOCKED_429" in str(e):
                    print(f"\n{Cores.VERMELHO}♻️  IP 429 Detectado! Trocando para o próximo proxy...{Cores.RESET}")
                    tentativas_proxy += 1
                    time.sleep(2)
                    continue 
                else:
                    log_erro(f"Erro fatal: {e}")
                    break

        if i < qtd - 1:
            tempo = random.randint(15, 25)
            barra_progresso(tempo, prefixo='Resfriando', sufixo='s')

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