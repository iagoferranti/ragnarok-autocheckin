import time
import re
import requests
import random
import string
import json
import os
import sys
from datetime import datetime
from DrissionPage import ChromiumPage, ChromiumOptions
from DrissionPage.common import Keys

os.system('') # Habilita cores no CMD

# --- CONFIGURAÇÕES PADRÃO ---
ARQUIVO_CONFIG = "config.json"
ARQUIVO_SALVAR = "novas_contas.json"
ARQUIVO_PRINCIPAL = "accounts.json"
URL_LISTA_VIP = "https://gist.githubusercontent.com/iagoferranti/2675637690215af512e1e83e1eaf5e84/raw/emails.json"
TIMEOUT_PADRAO = 40 

# --- CLASSE DE ESTILO ---
class Cores:
    RESET = '\033[0m'
    VERDE = '\033[92m'
    AMARELO = '\033[93m'
    VERMELHO = '\033[91m'
    CIANO = '\033[96m'
    CINZA = '\033[90m'
    NEGRITO = '\033[1m'

def log_info(msg): print(f"{Cores.CIANO}[INFO]{Cores.RESET} {msg}")
def log_sucesso(msg): print(f"{Cores.VERDE}[SUCESSO]{Cores.RESET} {msg}")
def log_aviso(msg): print(f"{Cores.AMARELO}[ALERTA]{Cores.RESET} {msg}")
def log_erro(msg): print(f"{Cores.VERMELHO}[ERRO]{Cores.RESET} {msg}")
def log_sistema(msg): print(f"{Cores.CINZA}   >> {msg}{Cores.RESET}")
def log_debug(msg): print(f"{Cores.CINZA}   [DEBUG] {msg}{Cores.RESET}")

# --- CARREGADOR DE CONFIGURAÇÕES ---
# --- CARREGADOR DE CONFIGURAÇÕES ---
def carregar_config():
    config_padrao = {
        "licenca_email": "",
        "headless": False,
        "tag_email": "rag",
        "sobrenome_padrao": "Silva",
        "telegram_token": "",
        "telegram_chat_id": ""
    }
    # REMOVIDO AQUI O BLOCO QUE CRIAVA O ARQUIVO (json.dump)
    if not os.path.exists(ARQUIVO_CONFIG):
        return config_padrao # Só retorna na memória, não cria arquivo físico

    try:
        with open(ARQUIVO_CONFIG, "r", encoding="utf-8") as f:
            user_config = json.load(f)
            config_padrao.update(user_config)
            return config_padrao
    except: return config_padrao
    if not os.path.exists(ARQUIVO_CONFIG):
        try:
            with open(ARQUIVO_CONFIG, "w", encoding="utf-8") as f:
                json.dump(config_padrao, f, indent=4)
        except: pass
        return config_padrao
    try:
        with open(ARQUIVO_CONFIG, "r", encoding="utf-8") as f:
            user_config = json.load(f)
            config_padrao.update(user_config)
            return config_padrao
    except: return config_padrao

CONF = carregar_config()

try:
    import pyotp
    TEM_PYOTP = True
except ImportError:
    TEM_PYOTP = False

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

# --- ARQUIVOS ---
def carregar_json_seguro(caminho):
    if not os.path.exists(caminho): return []
    try: 
        with open(caminho, "r", encoding="utf-8") as f: return json.load(f)
    except: return []

def salvar_json_seguro(caminho, dados):
    try:
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=4, ensure_ascii=False)
        return True
    except: return False

def consolidar_conta_no_principal(email, senha):
    contas = carregar_json_seguro(ARQUIVO_PRINCIPAL)
    for c in contas:
        if c.get('email') == email: return
    contas.append({"email": email, "password": senha})
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

# --- UTILITÁRIOS ---
def gerar_senha_ragnarok():
    chars = string.ascii_letters + string.digits + "!@#$"
    senha = [
        random.choice(string.ascii_uppercase),
        random.choice(string.ascii_lowercase),
        random.choice(string.digits),
        random.choice("!@#$"),
    ]
    senha += random.choices(chars, k=8)
    random.shuffle(senha)
    return "".join(senha)

def delay_humano():
    time.sleep(random.uniform(0.8, 1.5))

# --- EXTRATOR INTELIGENTE ---
def limpar_html(texto_html):
    clean = re.compile('<.*?>')
    return re.sub(clean, ' ', texto_html)

def extrair_codigo_seguro(texto_bruto):
    if not texto_bruto: return None
    texto_limpo = limpar_html(texto_bruto)
    match = re.search(r'C[oó]digo de Verificaç[aã]o.*?([A-Za-z0-9]{6})', texto_limpo, re.IGNORECASE | re.DOTALL)
    
    if match:
        codigo = match.group(1).strip()
        palavras_proibidas = ['abaixo', 'assets', 'height', 'width', 'style', 'follow', 'codigo', 'verify', 'click', 'button', 'target', 'class', 'border']
        if codigo.lower() in palavras_proibidas: return None
        return codigo
    return None

# --- DRISSION HELPERS ---
def fechar_cookies(page):
    try:
        # Só clica se estiver visível
        btn = page.ele('.cookieprivacy_btn__Pqz8U')
        if btn and btn.states.is_displayed:
            btn.click()
        elif page.ele('text=concordo.'):
            page.ele('text=concordo.').click()
    except: pass

def clicar_com_seguranca(page, seletor, nome_elemento="Elemento"):
    for tentativa in range(3):
        try:
            btn = page.wait.ele_displayed(seletor, timeout=TIMEOUT_PADRAO)
            if btn:
                page.scroll.to_see(btn)
                delay_humano()
                btn.click()
                return True
        except:
            try:
                btn = page.ele(seletor)
                if btn:
                    page.run_js("arguments[0].click()", btn)
                    return True
            except: pass
            time.sleep(1)
    
    log_erro(f"Falha ao clicar em {nome_elemento}.")
    return False

# --- BYPASS CLOUDFLARE DEFINITIVO (V60 - Lógica do Lab) ---
def vencer_cloudflare(page, checar_cookies=True):
    if checar_cookies: fechar_cookies(page)
    
    log_sistema("Analisando Cloudflare...")
    time.sleep(5) # Delay inicial para scripts

    # 1. VERIFICAÇÃO DE SUCESSO REAL (VISÍVEL)
    sucesso_visivel = False
    
    # Checa texto
    ele_texto = page.ele('text:Verificação de segurança para acesso concluída')
    if ele_texto and ele_texto.states.is_displayed:
        sucesso_visivel = True
        
    # Checa classe
    if not sucesso_visivel:
        ele_classe = page.ele('.page_success__gilOx')
        if ele_classe and ele_classe.states.is_displayed:
            sucesso_visivel = True

    if sucesso_visivel:
        log_debug(f"Status: {Cores.VERDE}SUCESSO (Confirmado e Visível).{Cores.RESET}")
        return # Pode seguir

    # 2. SE NÃO ESTÁ VISÍVEL, ESTÁ PENDENTE (OU FANTASMA)
    log_debug(f"Status: {Cores.AMARELO}Pendente ou Fantasma Detectado. Aplicando Manobra...{Cores.RESET}")
    
    # Foco no elemento inicial
    if page.ele('#email'):
        try: page.ele('#email').click()
        except: pass
    else:
        try: page.ele('tag:body').click()
        except: pass
        
    time.sleep(0.5)

    # Sequência de Ouro: 4x Shift+Tab + Espaço
    for _ in range(4):
        page.actions.key_down(Keys.SHIFT).key_down(Keys.TAB).key_up(Keys.TAB).key_up(Keys.SHIFT)
        time.sleep(0.1)
    
    # O Pulo do Gato
    page.actions.key_down(Keys.SPACE).key_up(Keys.SPACE)
    
    ##log_debug("Manobra executada. Aguardando 5s...")
    time.sleep(5)

# --- FUNÇÃO DE LIMPEZA DE SESSÃO ---
def garantir_logout(page):
    """Garante que não há sessão ativa antes de criar nova conta"""
    try:
        # 1. Limpeza técnica (Cookies + Storage)
        page.run_cdp('Network.clearBrowserCookies')
        page.run_cdp('Network.clearBrowserCache')
        page.run_js('localStorage.clear(); sessionStorage.clear();')
    except: pass

    # 2. Limpeza visual (Se houver botão de logout, clica)
    try:
        btn_logout = page.ele('.header_logoutBtn__6Pv_m')
        if btn_logout:
            log_sistema("Sessão ativa detectada. Fazendo Logout...")
            btn_logout.click()
            time.sleep(3)
    except: pass

# ================= PROVEDORES DE E-MAIL =================

class EmailSession:
    def __init__(self):
        self.email = None; self.senha_api = "Senha123"; self.token = None 
        self.login_1sec = None; self.domain_1sec = None; self.provider_name = ""
        self.primeiro_nome = "Jose"
        self.session_requests = None 

class ProviderGuerrilla:
    def gerar(self):
        obj = EmailSession()
        obj.provider_name = "GuerrillaMail"
        obj.session_requests = requests.Session()
        tag = CONF.get("tag_email", "rag")
        try:
            r = obj.session_requests.get("https://api.guerrillamail.com/ajax.php?f=get_email_address", timeout=10)
            data = r.json()
            user_novo = f"{random.choice(['sam','max','leo'])}{tag}{random.randint(100,999)}"
            r_set = obj.session_requests.get(f"https://api.guerrillamail.com/ajax.php?f=set_email_user&email_user={user_novo}&lang=en", timeout=10)
            
            if r_set.status_code == 200 and 'email_addr' in r_set.json():
                obj.email = r_set.json()['email_addr']
            else: obj.email = data['email_addr']
            return obj
        except: return None

    def esperar_codigo(self, obj, filtro):
        try:
            r = obj.session_requests.get(f"https://api.guerrillamail.com/ajax.php?f=check_email&seq=0", timeout=10)
            if r.status_code == 200:
                data = r.json()
                lista = data.get('list', [])
                for msg in lista:
                    if filtro.lower() in msg['mail_subject'].lower():
                        mid = msg['mail_id']
                        r_fetch = obj.session_requests.get(f"https://api.guerrillamail.com/ajax.php?f=fetch_email&email_id={mid}", timeout=10)
                        if r_fetch.status_code == 200:
                            return r_fetch.json().get('mail_body', '')
        except: pass
        return None

class ProviderMailTM:
    def gerar(self):
        obj = EmailSession(); obj.provider_name = "Mail.tm"
        tag = CONF.get("tag_email", "rag")
        try:
            r = requests.get("https://api.mail.tm/domains", timeout=5)
            doms = r.json()['hydra:member']
            coms = [d['domain'] for d in doms if d['domain'].endswith(".com")]
            domain = random.choice(coms) if coms else random.choice(doms)['domain']
            obj.email = f"user{tag}{random.randint(1000,9999)}@{domain}"
            requests.post("https://api.mail.tm/accounts", json={"address": obj.email, "password": obj.senha_api}, timeout=5)
            r_tok = requests.post("https://api.mail.tm/token", json={"address": obj.email, "password": obj.senha_api}, timeout=5)
            if r_tok.status_code == 200:
                obj.token = r_tok.json()['token']
                return obj
        except: pass
        return None

    def esperar_codigo(self, obj, filtro):
        headers = {"Authorization": f"Bearer {obj.token}"}
        try:
            r = requests.get("https://api.mail.tm/messages", headers=headers, timeout=5)
            if r.status_code == 200:
                for msg in r.json()['hydra:member']:
                    if filtro.lower() in msg['subject'].lower() and not msg['seen']:
                        det = requests.get(f"https://api.mail.tm/messages/{msg['id']}", headers=headers)
                        requests.patch(f"https://api.mail.tm/messages/{msg['id']}", headers=headers, json={"seen": True})
                        return det.json()['text']
        except: pass
        return None

class Provider1SecMail:
    def gerar(self):
        obj = EmailSession(); obj.provider_name = "1secmail"
        tag = CONF.get("tag_email", "rag")
        try:
            r = requests.get("https://www.1secmail.com/api/v1/?action=getDomainList", timeout=5)
            if r.status_code == 200:
                doms = r.json()
                bons = [d for d in doms if d.endswith(".com")]
                obj.domain_1sec = random.choice(bons) if bons else "esiix.com"
            else: obj.domain_1sec = "esiix.com"
            obj.login_1sec = f"u{tag}{random.randint(100,999)}"
            obj.email = f"{obj.login_1sec}@{obj.domain_1sec}"
            return obj
        except: return None

    def esperar_codigo(self, obj, filtro):
        try:
            url = f"https://www.1secmail.com/api/v1/?action=getMessages&login={obj.login_1sec}&domain={obj.domain_1sec}"
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                for msg in r.json():
                    if filtro.lower() in msg['subject'].lower():
                        r2 = requests.get(f"https://www.1secmail.com/api/v1/?action=readMessage&login={obj.login_1sec}&domain={obj.domain_1sec}&id={msg['id']}", timeout=5)
                        return r2.json().get('textBody') or r2.json().get('body')
        except: pass
        return None

# --- LOOP PRINCIPAL ---
def criar_conta(page):
    
    # 1. BLINDAGEM: Garante logout ANTES de começar qualquer coisa
    garantir_logout(page)

    for tentativa in range(3):
        if tentativa > 0:
            print(f"\n{Cores.AMARELO}♻️ Alternando Provedor (Tentativa {tentativa+1})...{Cores.RESET}")
            # Limpa cookies entre tentativas também
            garantir_logout(page)
            
        if tentativa == 0: prov = ProviderGuerrilla()
        elif tentativa == 1: prov = ProviderMailTM()
        else: prov = Provider1SecMail()
            
        log_info(f"Gerando identidade via: {Cores.AMARELO}{prov.__class__.__name__}{Cores.RESET}...")
        obj = prov.gerar()
        if not obj: continue
        log_sucesso(f"E-mail Gerado: {Cores.NEGRITO}{obj.email}{Cores.RESET}")
        
        # PROCESSO CADASTRO
        try:
            log_info("Acessando Cadastro...")
            page.get("https://member.gnjoylatam.com/pt/join")
            
            # REFRESH SE TRAVAR
            if not page.wait.ele_displayed('#email', timeout=20):
                log_aviso("Site demorou. Atualizando...")
                page.refresh()
                vencer_cloudflare(page)
                # Tenta logout de novo caso tenha carregado a home logada
                garantir_logout(page)
                if not page.wait.ele_displayed('#email', timeout=20):
                    log_erro("Site não carregou.")
                    continue 

            vencer_cloudflare(page, checar_cookies=True)

            page.ele('#email').click(); page.ele('#email').clear(); page.ele('#email').input(obj.email)
            delay_humano()
            
            if not clicar_com_seguranca(page, 'text=Enviar verificação', "Botão Enviar"):
                continue 
            
            # Espera Código
            print(f"   {Cores.CIANO}⏳ Aguardando e-mail (Cadastro) em {obj.provider_name}...{Cores.RESET}", end="", flush=True)
            cod1 = None
            start_wait = time.time()
            while time.time() - start_wait < 50:
                print(".", end="", flush=True)
                val = prov.esperar_codigo(obj, "Cadastro")
                if val:
                    cod_extraido = extrair_codigo_seguro(val)
                    if cod_extraido: cod1 = cod_extraido; break
                time.sleep(4)
            
            if not cod1:
                print(f"\n   {Cores.VERMELHO}❌ Timeout.{Cores.RESET}")
                continue 
                
            print(f"\n   {Cores.VERDE}🔥 CÓDIGO RECEBIDO: {cod1}{Cores.RESET}")
            page.ele('#authnumber').input(cod1)
            time.sleep(1)
            try: page.ele('text=Verificação concluída').click()
            except: pass
            
            senha = gerar_senha_ragnarok()
            page.ele('#password').input(senha)
            page.ele('#password2').input(senha)
            try:
                page.ele('.page_selectBtn__XfETd').click()
                page.ele('text=Brasil').click()
            except: pass
            page.ele('#firstname').input(obj.primeiro_nome.capitalize())
            page.ele('#lastname').input(CONF.get("sobrenome_padrao", "Silva"))
            page.ele('#birthday').input("01/01/1995")
            page.scroll.to_bottom()
            try:
                page.run_js("document.getElementById('terms1').click()")
                page.run_js("document.getElementById('terms2').click()")
            except: pass
            
            if not clicar_com_seguranca(page, '.page_submitBtn__hk_C0', "Botão CONTINUAR"):
                 if not clicar_com_seguranca(page, 'text=CONTINUAR', "Botão CONTINUAR"): return False
            
            log_sucesso("Cadastro enviado!")
            
            # === LOGIN (COM RESGATE) ===
            log_info("Fazendo Login...")
            if page.ele('text=Entrar'): clicar_com_seguranca(page, 'text=Entrar', "Botão Entrar")
            else: page.get("https://login.gnjoylatam.com")
                
            page.wait.url_change('login', timeout=TIMEOUT_PADRAO)
            vencer_cloudflare(page, False)
            
            page.ele('#email').click(); page.ele('#email').clear(); page.ele('#email').input(obj.email)
            delay_humano()
            page.ele('#password').input(senha)
            delay_humano()
            clicar_com_seguranca(page, 'text=CONTINUAR', "Login")
            
            page.wait.url_change('login.gnjoylatam.com', timeout=30)
            
            # --- OTP ---
            page.get("https://www.gnjoylatam.com/pt")
            
            # LÓGICA DE RESGATE: Se não tiver Perfil, tenta logar de novo
            if not page.ele('.header_mypageBtn__cR1p3') and (page.ele('text=Login') or page.ele('text=Entrar')):
                log_aviso("Sessão perdida. Tentando login de resgate...")
                if clicar_com_seguranca(page, 'text=Login', "Botão Login") or clicar_com_seguranca(page, 'text=Entrar', "Botão Entrar"):
                    page.wait.url_change('login', timeout=15)
                    vencer_cloudflare(page, False)
                    page.ele('#email').input(obj.email)
                    page.ele('#password').input(senha)
                    clicar_com_seguranca(page, 'text=CONTINUAR', "Login")
                    time.sleep(5)
                    page.get("https://www.gnjoylatam.com/pt")

            if not clicar_com_seguranca(page, '.header_mypageBtn__cR1p3', "Perfil"):
                log_erro("Falha crítica: Não logou após cadastro.")
                continue 

            if not clicar_com_seguranca(page, 'text=Conexão OTP', "Menu OTP"): continue
            
            seletores = ['text:Solicitação de serviço OTP', '.page_otp_join_btn__KKBJq']
            clicou = False
            for sel in seletores:
                if clicar_com_seguranca(page, sel, "Solicitar OTP"):
                    clicou = True; break
            
            if not clicou: return False
                
            # 3. AGUARDAR CÓDIGO OTP
            print(f"   {Cores.CIANO}⏳ Aguardando e-mail (OTP) em {obj.provider_name}...{Cores.RESET}", end="", flush=True)
            cod2 = None
            start_wait = time.time()
            while time.time() - start_wait < 50:
                print(".", end="", flush=True)
                val = prov.esperar_codigo(obj, "OTP")
                if val:
                    cod_extraido = extrair_codigo_seguro(val)
                    if cod_extraido: cod2 = cod_extraido; break
                time.sleep(4)

            if not cod2: return False
            print(f"\n   {Cores.VERDE}🔥 CÓDIGO RECEBIDO: {cod2}{Cores.RESET}")
            
            page.wait.ele_displayed('#authnumber', timeout=TIMEOUT_PADRAO)
            page.ele('#authnumber').input(cod2)
            delay_humano()
            
            clicar_com_seguranca(page, 'text=Verificação concluída', "Validar OTP")
            time.sleep(3)
            
            # --- SEED ---
            ele_seed = page.wait.ele_displayed('.page_otp_key__nk3eO', timeout=TIMEOUT_PADRAO)
            if ele_seed:
                seed_text = ele_seed.text
                print(f"   💎 SEED: {Cores.AMARELO}{seed_text}{Cores.RESET}")
                
                if TEM_PYOTP:
                    totp = pyotp.TOTP(seed_text.replace(" ", ""))
                    codigo_app = totp.now()
                    inputs = page.eles('tag:input')
                    for i in inputs:
                        if i.states.is_displayed and not i.attr('disabled') and i.attr('type') == 'text':
                            i.input(codigo_app); break
                    delay_humano()
                    
                    if clicar_com_seguranca(page, 'text=Confirme', "Confirme"):
                        achou_ok = False
                        if clicar_com_seguranca(page, 'text=OK', "OK"): achou_ok = True
                        
                        status = "PRONTA_PARA_FARMAR" if achou_ok else "VERIFICAR_MANUALMENTE"
                        salvar_conta_backup(obj.email, senha, seed_text, status)
                        consolidar_conta_no_principal(obj.email, senha)
                        return True # SUCESSO TOTAL
                else:
                    salvar_conta_backup(obj.email, senha, seed_text, status="FALTA_ATIVAR_APP")
                    return True
            else:
                return False

        except Exception as e:
            log_erro(f"Erro no processo: {e}")
            return False 
            
    return False

# --- FUNÇÃO TRAMPOLIM ---
def verificar_licenca_online(tipo):
    try:
        from master import verificar_licenca_online as v
        return v(tipo)
    except: return True

# --- MAIN ---
def main():
    if not verificar_licenca_online("fabricador"): 
        return

    print(f"\n{Cores.CIANO}>>> FÁBRICA DE CONTAS PREMIUM{Cores.RESET}")
    try: qtd = int(input("\nQuantas contas deseja criar? (Recomendamos no máximo 10 por execução): ").strip() or "1")
    except: qtd = 1
    
    if qtd > 15:
        log_aviso("Quantidade alta. Risco de bloqueio de IP.")
        if input("Continuar? (s/n): ").lower() != 's': return

    print("\n>>> Inicializando Motor...")
    co = ChromiumOptions()
    co.set_argument('--force-device-scale-factor=0.8')
    if CONF.get("headless", False): co.headless(True)
    
    page = ChromiumPage(addr_or_opts=co)

    sucessos = 0
    for i in range(qtd):
        print(f"\n{Cores.NEGRITO}=== CONTA {i+1} DE {qtd} ==={Cores.RESET}")
        
        if criar_conta(page):
            sucessos += 1
            print(f"{Cores.VERDE}✅ Sucesso na conta {i+1}!{Cores.RESET}")
        else:
            print(f"{Cores.VERMELHO}❌ Falha na conta {i+1} (Todas tentativas esgotadas).{Cores.RESET}")
        
        if i < qtd - 1:
            tempo = random.randint(15, 25)
            print(f"zzz Resfriando por {tempo}s...")
            time.sleep(tempo)

    msg_final = f"Fabricação Finalizada. Sucessos: {sucessos}/{qtd}"
    print(f"\n{Cores.NEGRITO}=== {msg_final} ==={Cores.RESET}")
    enviar_telegram(msg_final)
    page.quit()
    input("\nEnter para voltar...")

def executar():
    main()

if __name__ == "__main__":
    main()