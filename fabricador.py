import time
import re
import requests
import random
import string
import json
import os
import sys
import shutil
from datetime import datetime
from DrissionPage import ChromiumPage, ChromiumOptions
from DrissionPage.common import Keys

os.system('') # Cores no CMD

# --- CONFIGURAÇÕES PADRÃO ---
ARQUIVO_CONFIG = "config.json"
ARQUIVO_SALVAR = "novas_contas.json"
ARQUIVO_PRINCIPAL = "accounts.json"
URL_LISTA_VIP = "https://gist.githubusercontent.com/iagoferranti/2675637690215af512e1e83e1eaf5e84/raw/emails.json"
TIMEOUT_PADRAO = 30 

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

# --- CARREGADOR DE CONFIGURAÇÕES ---
def carregar_config():
    config_padrao = {
        "licenca_email": "",
        "headless": False,
        "tag_email": "rag",
        "sobrenome_padrao": "Adamantio da Silva",
        "telegram_token": "",
        "telegram_chat_id": ""
    }
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
    time.sleep(random.uniform(0.6, 1.4))

# --- DRISSION HELPERS ---
def fechar_cookies(page):
    try:
        if page.ele('.cookieprivacy_btn__Pqz8U', timeout=2):
            page.ele('.cookieprivacy_btn__Pqz8U').click()
        elif page.ele('text=concordo.', timeout=1):
            page.ele('text=concordo.').click()
    except: pass

def clicar_com_seguranca(page, seletor, nome_elemento="Elemento"):
    log_sistema(f"Procurando: {nome_elemento}...")
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

def vencer_cloudflare(page, checar_cookies=True):
    if checar_cookies: fechar_cookies(page)
    log_sistema("Analisando Cloudflare...")
    time.sleep(3) 
    precisa_clicar = False
    
    ele_sucesso = page.ele('.page_success__gilOx')
    if not ele_sucesso: ele_sucesso = page.ele('text:concluída')
    
    if ele_sucesso and ele_sucesso.states.is_displayed:
        log_sucesso("Cloudflare já validado!")
        precisa_clicar = False
    else:
        ele_check = page.ele('text=Confirme que é humano') or page.ele('.cb-lb')
        ele_load = page.ele('text=Verificando segurança')
        if (ele_check and ele_check.states.is_displayed) or (ele_load and ele_load.states.is_displayed):
            precisa_clicar = True
        else:
            precisa_clicar = True
    
    if precisa_clicar:
        log_sistema("Executando bypass...")
        try: page.ele('tag:body').click()
        except: pass
        if page.wait.ele_displayed('#email', timeout=5):
            page.scroll.to_location(0, 200)
            page.run_js("document.getElementById('email').focus()")
            time.sleep(0.2)
            page.ele('#email').click()
            time.sleep(0.5)
        for _ in range(4): 
            page.actions.key_down(Keys.SHIFT).key_down(Keys.TAB).key_up(Keys.TAB).key_up(Keys.SHIFT)
            time.sleep(0.3)
        page.actions.key_down(Keys.SPACE).key_up(Keys.SPACE)
        log_sistema("Aguardando validação...")
        time.sleep(5)

# --- API E-MAIL INTELIGENTE ---
def testar_acesso_conta(token):
    try:
        r = requests.get(f"https://api.mail.tm/me", headers={"Authorization": f"Bearer {token}"}, timeout=5)
        return r.status_code == 200
    except: return False

def gerar_email_premium(blacklist_dominios=[]):
    log_info("Gerando identidade na API Mail.tm...")
    tag = CONF.get("tag_email", "rag")
    nomes_lista = ['jose', 'junior', 'joao', 'carlos', 'ricardo', 'lucas', 'marcos']
    
    tentativas = 0
    while tentativas < 10:
        try:
            resp = requests.get(f"https://api.mail.tm/domains", timeout=10)
            if resp.status_code == 429:
                log_aviso("API cheia. Aguardando...")
                time.sleep(5); tentativas += 1; continue
            
            # FILTRO DE DOMÍNIOS RUINS
            todos_dominios = resp.json()['hydra:member']
            # Pega domínios que NÃO estão na blacklist
            dominios_validos = [d for d in todos_dominios if d['domain'] not in blacklist_dominios]
            
            if not dominios_validos:
                log_erro("Todos os domínios disponíveis estão na blacklist. Tentando resetar...")
                dominios_validos = todos_dominios # Reseta se acabar as opções

            domain_obj = random.choice(dominios_validos)
            domain = domain_obj['domain']
            
            nome_base = random.choice(nomes_lista)
            sufixo = ''.join(random.choices(string.ascii_lowercase + string.digits, k=random.randint(3, 5)))
            
            email = f"{nome_base}{tag}_{sufixo}@{domain}"
            senha = "SenhaTemporaria123"
            
            r = requests.post(f"https://api.mail.tm/accounts", json={"address": email, "password": senha}, timeout=10)
            if r.status_code in [201, 422]:
                r_tok = requests.post(f"https://api.mail.tm/token", json={"address": email, "password": senha}, timeout=10)
                if r_tok.status_code == 200:
                    token = r_tok.json()['token']
                    if testar_acesso_conta(token):
                        log_sucesso(f"Identidade ({domain}): {Cores.NEGRITO}{email}{Cores.RESET}")
                        return email, senha, token, nome_base
        except: time.sleep(1)
        tentativas += 1
    return None, None, None, None

def esperar_codigo_email(token, filtro_assunto=""):
    print(f"   {Cores.CIANO}⏳ Aguardando e-mail ({filtro_assunto})...{Cores.RESET}", end="", flush=True)
    headers = {"Authorization": f"Bearer {token}"}
    start = time.time()
    
    # 60 segundos de espera máxima para trocar logo de domínio
    TIMEOUT_ESPERA = 60 
    
    while time.time() - start < TIMEOUT_ESPERA:
        try:
            print(".", end="", flush=True)
            r = requests.get(f"https://api.mail.tm/messages", headers=headers, timeout=10)
            if r.status_code == 200:
                msgs = r.json()['hydra:member']
                if msgs:
                    for msg in msgs:
                        assunto = msg.get('subject', '')
                        if filtro_assunto.lower() not in assunto.lower(): continue
                        
                        if not msg['seen']:
                            det = requests.get(f"https://api.mail.tm/messages/{msg['id']}", headers=headers, timeout=10)
                            texto = det.json()['text']
                            requests.patch(f"https://api.mail.tm/messages/{msg['id']}", headers=headers, json={"seen": True})
                            
                            match = re.search(r'C[oó]digo de Verificaç[aã]o\s+([A-Za-z0-9]{6})', texto, re.IGNORECASE)
                            if match:
                                codigo = match.group(1)
                                if "assets" not in codigo.lower():
                                    print(f"\n   {Cores.VERDE}🔥 CÓDIGO RECEBIDO: {codigo}{Cores.RESET}")
                                    return codigo
            time.sleep(3)
        except: time.sleep(3)
    
    print(f"\n   {Cores.AMARELO}⚠️ Timeout: Código não chegou.{Cores.RESET}")
    return None

# --- LICENÇA (AGORA COMPLETA) ---
def verificar_licenca_online(permissao_necessaria="all"):
    """
    Verifica se o e-mail tem a permissão necessária.
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
    
    if not email:
        if 'Cores' in globals(): print(f"{Cores.AMARELO}Licença não encontrada.{Cores.RESET}")
        else: print("Licença não encontrada.")
        email = input("Digite seu E-mail: ").strip()
        
    try:
        r = requests.get(URL_LISTA_VIP, timeout=10)
        if r.status_code == 200:
            try:
                dados_licenca = r.json()
                if isinstance(dados_licenca, list):
                    dados_licenca = {e: ["all"] for e in dados_licenca}
                
                dados_licenca = {k.lower().strip(): v for k, v in dados_licenca.items()}
                email_norm = email.lower().strip()
                
                if email_norm in dados_licenca:
                    permissoes = dados_licenca[email_norm]
                    acesso_liberado = False
                    if "all" in permissoes: acesso_liberado = True
                    elif permissao_necessaria in permissoes: acesso_liberado = True
                    
                    if acesso_liberado:
                        with open(path, "w") as f: f.write(email)
                        return True
            except: pass
                
    except: pass
    
    if 'Cores' in globals(): print(f"{Cores.VERMELHO}Acesso Negado ou Erro de Conexão.{Cores.RESET}")
    else: print("Acesso Negado ou Erro de Conexão.")
    return False

# --- FABRICAÇÃO COM RETRY ---
def criar_uma_conta_com_retry(page):
    """Tenta criar UMA conta, mas se o e-mail falhar, troca de domínio e tenta de novo"""
    blacklist_dominios_sessao = []
    
    for tentativa_dominio in range(3): # Tenta até 3 domínios diferentes
        if tentativa_dominio > 0:
            print(f"\n{Cores.AMARELO}♻️ Tentativa {tentativa_dominio+1} com NOVO domínio...{Cores.RESET}")
        
        email, _, token_email, primeiro_nome = gerar_email_premium(blacklist_dominios_sessao)
        if not email: return False
        
        # Extrai o domínio atual e prepara pra blacklist se falhar
        dominio_atual = email.split('@')[1]
        
        senha_rag = gerar_senha_ragnarok()
        sobrenome = CONF.get("sobrenome_padrao", "Silva")
        
        try:
            try:
                page.run_cdp('Network.clearBrowserCookies')
                page.run_cdp('Network.clearBrowserCache')
            except: pass
            
            log_info("Acessando Cadastro...")
            page.get("https://member.gnjoylatam.com/pt/join")
            
            if not page.wait.ele_displayed('#email', timeout=TIMEOUT_PADRAO):
                return False

            vencer_cloudflare(page, checar_cookies=True)

            page.ele('#email').click(); page.ele('#email').clear(); page.ele('#email').input(email)
            delay_humano()
            
            if not clicar_com_seguranca(page, 'text=Enviar verificação', "Botão Enviar"):
                 blacklist_dominios_sessao.append(dominio_atual)
                 continue # Tenta proximo

            codigo1 = esperar_codigo_email(token_email, filtro_assunto="Cadastro")
            
            # --- PONTO CRÍTICO: SE NÃO CHEGOU, TROCA O DOMÍNIO ---
            if not codigo1:
                log_erro(f"Domínio ruim detectado: {dominio_atual}")
                blacklist_dominios_sessao.append(dominio_atual)
                continue # Volta pro inicio do loop (gera novo email)
            
            # SE CHEGOU AQUI, O DOMÍNIO É BOM! SEGUE O BAILE
            log_sistema(f"Código 1: {codigo1}")
            page.ele('#authnumber').input(codigo1)
            delay_humano()
            
            try:
                btn = page.ele('text=Verificação concluída') or page.ele('.mailauth_keyColor__by8Xo')
                if btn and not btn.attr('disabled'): btn.click()
            except: pass
            time.sleep(2)
            
            page.ele('#password').input(senha_rag)
            page.ele('#password2').input(senha_rag)
            
            btn_pais = page.ele('.page_selectBtn__XfETd')
            if btn_pais and "Brasil" not in btn_pais.text:
                btn_pais.click(); delay_humano(); page.ele('text=Brasil').click()
            
            page.ele('#firstname').input(primeiro_nome.capitalize())
            page.ele('#lastname').input(sobrenome)
            page.ele('#birthday').input("01/01/1995")
            delay_humano()

            page.scroll.to_bottom()
            try:
                page.run_js("document.getElementById('terms1').click()")
                page.run_js("document.getElementById('terms2').click()")
            except:
                if page.ele('#terms1'): page.ele('#terms1').click()
                if page.ele('#terms2'): page.ele('#terms2').click()
            delay_humano()

            if not clicar_com_seguranca(page, '.page_submitBtn__hk_C0', "Botão CONTINUAR"):
                 if not clicar_com_seguranca(page, 'text=CONTINUAR', "Botão CONTINUAR"): return False
            
            log_sucesso("Cadastro enviado!")
            
            # --- LOGIN ---
            log_info("Fazendo Login...")
            if page.wait.ele_displayed('text=Entrar', timeout=TIMEOUT_PADRAO):
                clicar_com_seguranca(page, 'text=Entrar', "Botão Entrar")
            else:
                page.get("https://login.gnjoylatam.com")
                
            page.wait.url_change('login', timeout=TIMEOUT_PADRAO)
            vencer_cloudflare(page, checar_cookies=False)
            
            page.ele('#email').click(); page.ele('#email').clear(); page.ele('#email').input(email)
            delay_humano()
            page.ele('#password').input(senha_rag)
            delay_humano()
            clicar_com_seguranca(page, 'text=CONTINUAR', "Login")
            
            page.wait.url_change('login.gnjoylatam.com', timeout=30)
            
            # --- OTP ---
            if not page.wait.ele_displayed('.header_mypageBtn__cR1p3', timeout=TIMEOUT_PADRAO):
                 page.get("https://www.gnjoylatam.com/pt")
                 if not page.wait.ele_displayed('.header_mypageBtn__cR1p3', timeout=TIMEOUT_PADRAO):
                     return False

            clicar_com_seguranca(page, '.header_mypageBtn__cR1p3', "Perfil")
            clicar_com_seguranca(page, 'text=Conexão OTP', "Menu OTP")
            
            seletores = ['text:Solicitação de serviço OTP', '.page_otp_join_btn__KKBJq']
            clicou = False
            for sel in seletores:
                if clicar_com_seguranca(page, sel, "Solicitar OTP"):
                    clicou = True; break
            
            if not clicou: return False
                
            codigo2 = esperar_codigo_email(token_email, filtro_assunto="OTP")
            if not codigo2: return False
            
            page.wait.ele_displayed('#authnumber', timeout=TIMEOUT_PADRAO)
            page.ele('#authnumber').input(codigo2)
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
                    
                    seletores_conf = ['.page_otp_key_cert_btn__Puava', 'text=Confirme']
                    for sel in seletores_conf:
                        if clicar_com_seguranca(page, sel, "Confirme"): break
                    
                    seletores_ok = ['.alert_confirm__79LSd', 'text=OK', 'tag:button@@text()=OK']
                    achou_ok = False
                    for sel in seletores_ok:
                        if page.wait.ele_displayed(sel, timeout=10):
                            time.sleep(1)
                            try: page.ele(sel).click()
                            except: pass
                            achou_ok = True; break
                    
                    status = "PRONTA_PARA_FARMAR" if achou_ok else "VERIFICAR_MANUALMENTE"
                    salvar_conta_backup(email, senha_rag, seed_text, status)
                    consolidar_conta_no_principal(email, senha_rag)
                    return True # SUCESSO TOTAL
                else:
                    salvar_conta_backup(email, senha_rag, seed_text, status="FALTA_ATIVAR_APP")
                    return True
            else:
                return False

        except Exception as e:
            log_erro(f"Erro no processo: {e}")
            return False # Falha genérica
            
    return False # Falhou 3 vezes

# --- MAIN ATUALIZADA ---
def main():
    if not verificar_licenca_online("fabricador"): 
        return

    print(f"\n{Cores.CIANO}>>> FÁBRICA DE CONTAS PREMIUM (Anti-Block){Cores.RESET}")
    try: qtd = int(input("\nQuantas contas deseja criar? ").strip())
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
        
        # CHAMA A NOVA FUNÇÃO COM RETRY
        if criar_uma_conta_com_retry(page):
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