import os
import sys
import json
import time
import random
import subprocess
import requests # Necessário para checar versão e licença

# --- DEFINIÇÃO DE PASTAS ---
def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

pasta_navegadores = os.path.join(get_base_path(), "navegadores")
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = pasta_navegadores

from playwright.sync_api import sync_playwright
from playwright.__main__ import main as playwright_installer

# ===== CONFIGURAÇÕES DE DISTRIBUIÇÃO =====
VERSAO_ATUAL = "1.0"
NOME_EXECUTAVEL = "AutoCheckin.exe" # Nome final do arquivo

# 1. LINK DA VERSÃO (SEU ARQUIVO TXT NO GITHUB)
URL_VERSION_TXT = "https://raw.githubusercontent.com/iagoferranti/ragnarok-autocheckin/refs/heads/main/version.txt"

# 2. LINK DO DOWNLOAD (AUTOMÁTICO DO GITHUB RELEASES)
# O robô vai baixar sempre o arquivo "AutoCheckin.exe" da última release
URL_DOWNLOAD_EXE = "https://github.com/iagoferranti/ragnarok-autocheckin/releases/latest/download/AutoCheckin.exe"

# 3. LINK DA LICENÇA)
URL_LISTA_VIP = "https://gist.githubusercontent.com/iagoferranti/2675637690215af512e1e83e1eaf5e84/raw/emails.json"

# ===== CONFIGURAÇÕES DO BOT =====
LOGIN_URL = "https://ro.gnjoylatam.com/pt/event/decemberroulette"
CHECKIN_URL = "https://ro.gnjoylatam.com/pt/event/decemberroulette"
HEADLESS = False 
WAIT_TIMEOUT_MS = 60000 

# ===== SISTEMA DE LICENÇA =====
def verificar_licenca_online():
    print("\n[SEGURANÇA] Verificando permissão de uso...")
    
    # Se o programador esqueceu de configurar o link, libera geral (modo teste)
    if "COLOQUE_AQUI" in URL_LISTA_VIP:
        print("[AVISO] Link da lista VIP não configurado. Modo livre ativado.")
        return True

    arquivo_licenca = os.path.join(get_base_path(), "user_license.key")
    email_usuario = ""

    # Tenta ler e-mail salvo
    if os.path.exists(arquivo_licenca):
        try:
            with open(arquivo_licenca, "r") as f:
                email_usuario = f.read().strip()
        except: pass
    
    # Se não tem salvo, pede
    if not email_usuario:
        print("Este software é restrito. Digite seu e-mail autorizado.")
        email_usuario = input(">> Seu E-mail: ").strip()

    try:
        # Baixa a lista do Gist
        r = requests.get(URL_LISTA_VIP)
        if r.status_code != 200:
            print("❌ Erro ao conectar servidor de licenças.")
            return False
        
        try:
            lista_permitida = r.json() # Tenta ler como JSON
        except:
            # Se falhar JSON, tenta ler linha a linha (txt simples)
            lista_permitida = r.text.splitlines()

        # Verifica se o email está na lista (ignora maiusculas/minusculas)
        if any(email_usuario.lower() == email.lower() for email in lista_permitida):
            print(f"✅ Acesso AUTORIZADO para: {email_usuario}")
            with open(arquivo_licenca, "w") as f: f.write(email_usuario)
            return True
        else:
            print(f"⛔ ACESSO NEGADO. O e-mail '{email_usuario}' não possui licença ativa.")
            if os.path.exists(arquivo_licenca): os.remove(arquivo_licenca)
            return False

    except Exception as e:
        print(f"❌ Erro ao validar licença: {e}")
        return False

# ===== SISTEMA DE ATUALIZAÇÃO =====
def verificar_atualizacao():
    # Só roda atualização se for .exe compilado
    if not getattr(sys, 'frozen', False):
        return

    print(f"\n[UPDATE] Versão instalada: {VERSAO_ATUAL}")
    try:
        r = requests.get(URL_VERSION_TXT)
        if r.status_code == 200:
            versao_remota = r.text.strip()
            
            if versao_remota != VERSAO_ATUAL:
                print(f"🚨 NOVA VERSÃO DISPONÍVEL: {versao_remota}")
                msg = input("Deseja atualizar agora? (S/N): ").lower()
                if msg == 's':
                    realizar_atualizacao_auto()
            else:
                print("[UPDATE] Seu sistema está atualizado.")
    except:
        print("[UPDATE] Não foi possível buscar atualizações.")

def realizar_atualizacao_auto():
    print("[UPDATE] Baixando nova versão... Aguarde...")
    try:
        # 1. Baixa o novo .exe
        r = requests.get(URL_DOWNLOAD_EXE, stream=True)
        nome_temp = "update_new.exe"
        caminho_temp = os.path.join(get_base_path(), nome_temp)
        
        with open(caminho_temp, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # 2. Cria script BAT para substituir os arquivos
        nome_atual = os.path.basename(sys.executable)
        caminho_bat = os.path.join(get_base_path(), "update.bat")
        
        # O script espera 2s, deleta o atual, renomeia o novo e abre
        bat_script = f"""
        @echo off
        timeout /t 2 /nobreak > NUL
        del "{nome_atual}"
        ren "{nome_temp}" "{nome_atual}"
        start "" "{nome_atual}"
        del "%~f0"
        """
        
        with open(caminho_bat, "w") as f: f.write(bat_script)
        
        print("[UPDATE] Reiniciando aplicação...")
        subprocess.Popen([caminho_bat], shell=True)
        sys.exit(0)

    except Exception as e:
        print(f"[ERRO] Falha na atualização: {e}")
        input("Enter para continuar na versão atual...")

# ===== FUNÇÕES DE NAVEGADOR E BOT =====
def encontrar_executavel_chrome():
    if not os.path.exists(pasta_navegadores): return None
    for root, dirs, files in os.walk(pasta_navegadores):
        for file in files:
            if file == "chrome.exe" or file == "headless_shell.exe":
                return os.path.join(root, file)
    return None

def verificar_e_instalar_navegador():
    print(f"\n[SISTEMA] Pasta de navegadores: {pasta_navegadores}")
    executavel = encontrar_executavel_chrome()
    if executavel and os.path.exists(executavel):
        print(f"[SISTEMA] Navegador encontrado.")
        return executavel

    print("[SISTEMA] Baixando navegador portátil... Aguarde.")
    try:
        sys.argv = ["playwright", "install", "chromium"]
        try: playwright_installer()
        except SystemExit: pass
        
        executavel = encontrar_executavel_chrome()
        if not executavel: raise Exception("Executável não encontrado após download.")
        print("[SISTEMA] Pronto!")
        return executavel
    except Exception as e:
        print(f"\n[ERRO] {e}")
        input("Enter para sair...")
        sys.exit(1)

def setup_contas():
    caminho = os.path.join(get_base_path(), "accounts.json")
    if os.path.exists(caminho):
        try:
            with open(caminho, "r", encoding="utf-8") as f: return json.load(f)
        except: pass

    print("\n=== CONFIGURAÇÃO INICIAL ===")
    while True:
        try:
            qtd = int(input(">> Quantas contas? "))
            if qtd > 0: break
        except: pass

    novas = []
    for i in range(qtd):
        print(f"\nConta {i+1}:")
        novas.append({"email": input("Email: ").strip(), "password": input("Senha: ").strip()})

    try:
        with open(caminho, "w", encoding="utf-8") as f: json.dump(novas, f, indent=4)
        print("✅ Salvo!")
    except: pass
    return novas

# Funções auxiliares do bot
def digitar_humano(page, seletor, texto):
    try:
        page.bring_to_front()
        page.focus(seletor)
        page.type(seletor, texto, delay=random.randint(50, 150))
    except: page.fill(seletor, texto)

def verificar_se_precisa_clique(page):
    try:
        if page.locator("iframe[src*='turnstile'], iframe[src*='challenges']").count() > 0:
            iframe = page.frame_locator("iframe[src*='turnstile'], iframe[src*='challenges']").first
            if iframe.locator("input[type='checkbox']").is_visible(): return True
    except: pass
    return False

def clicar_checkbox_forca_bruta(page):
    try:
        if page.locator("iframe[src*='turnstile'], iframe[src*='challenges']").count() > 0:
            iframe = page.frame_locator("iframe[src*='turnstile'], iframe[src*='challenges']").first
            if iframe.locator("input[type='checkbox']").count() > 0:
                iframe.locator("input[type='checkbox']").first.click(force=True)
                return True
            box = page.locator("iframe[src*='turnstile'], iframe[src*='challenges']").first.bounding_box()
            if box:
                page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
                return True
    except: pass
    return False

def aguardar_validacao_ou_refresh(page, tentativa_atual):
    print("   🛡️ Verificando segurança...")
    inicio = time.time()
    while time.time() - inicio < 20:
        if page.locator("text=Sucesso").count() > 0 or page.locator("text=concluída").count() > 0:
            print("      ✅ Sucesso Automático!")
            time.sleep(1)
            return "OK"

        if verificar_se_precisa_clique(page):
            if tentativa_atual < 2: 
                print("      ⚠️ Checkbox pediu clique. Forçando F5...")
                return "REFRESH"
            else:
                print("      ⚠️ Clicando forçado...")
                clicar_checkbox_forca_bruta(page)
                time.sleep(2)

        if page.locator("text=Verificando segurança").count() > 0 or page.locator("text=Just a moment").count() > 0:
            if time.time() - inicio > 15 and tentativa_atual < 2:
                print("      ⚠️ Travou. Forçando F5...")
                return "REFRESH"
            print("      ⏳ Processando...")
            time.sleep(2)
            continue
            
        if time.time() - inicio > 5:
            print("      ❓ Texto sumiu. Seguindo...")
            return "OK"
    return "TIMEOUT"

def limpar_overlays(page):
    try:
        page.evaluate("""
            const selectors = ['.styles_dimd_layer__NtwPg', '.cookieprivacy_cookieprivacy__Mz1XD', 'div[class*="modal"]'];
            selectors.forEach(sel => document.querySelectorAll(sel).forEach(el => el.remove()));
        """)
    except: pass

def do_checkin_for_account(p, email: str, password: str, browser_path: str):
    browser = p.chromium.launch(
        executable_path=browser_path,
        headless=HEADLESS,
        args=["--window-size=1366,768", "--force-device-scale-factor=0.75", "--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-background-timer-throttling", "--disable-backgrounding-occluded-windows", "--disable-renderer-backgrounding"]
    )
    context = browser.new_context(viewport={"width": 1366, "height": 768})
    page = context.new_page()
    page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    try:
        print(f"\n>>> Conta: {email}")
        max_retries = 3
        login_sucesso = False

        for tentativa in range(max_retries):
            print(f"   🔄 Login {tentativa + 1}/{max_retries}")
            try:
                if tentativa == 0:
                    try: page.goto(LOGIN_URL, timeout=WAIT_TIMEOUT_MS)
                    except: pass
                else:
                    page.reload(); page.wait_for_load_state('domcontentloaded'); time.sleep(3)

                page.bring_to_front()
                if aguardar_validacao_ou_refresh(page, tentativa) == "REFRESH": continue

                if page.locator('a.page_login__g41B0:has-text("Logout")').count() > 0:
                    print("   [!] Já logado."); login_sucesso = True; break
                
                if page.locator('a.page_login__g41B0:has-text("Login")').is_visible():
                    print("   -> Indo para login...")
                    page.locator('a.page_login__g41B0:has-text("Login")').first.click(); time.sleep(3)
                
                if aguardar_validacao_ou_refresh(page, tentativa) == "REFRESH": continue
                
                if page.locator("#email").is_visible():
                    digitar_humano(page, "#email", email)
                    digitar_humano(page, "#password", password)
                    try: page.locator("label:has-text('Manter conectado')").click(timeout=1000)
                    except: pass
                    
                    print("   -> Verificação Final...")
                    if aguardar_validacao_ou_refresh(page, tentativa) == "REFRESH": continue
                    
                    print("   -> Enviando...")
                    page.press("#password", "Enter"); time.sleep(2)
                    try: page.wait_for_url("**decemberroulette**", timeout=10000)
                    except: pass
                    
                    if "decemberroulette" in page.url or page.locator('a.page_login__g41B0:has-text("Logout")').count() > 0:
                        login_sucesso = True; break
            except: pass

        if not login_sucesso:
            print(f"   ❌ Falha ao logar."); return

        if "decemberroulette" not in page.url:
            page.goto(CHECKIN_URL); time.sleep(3)
        limpar_overlays(page)
        
        try:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)"); time.sleep(1)
            btn = page.locator('img[alt="attendance button"]').first
            if btn.is_visible():
                btn.scroll_into_view_if_needed(); time.sleep(1); btn.click()
                print(f"   ✅ SUCESSO: {email}"); time.sleep(4)
            else: print("   ⚠️ Botão Check-in não visível.")
        except: pass

        try:
            page.goto(CHECKIN_URL)
            page.locator('a.page_login__g41B0:has-text("Logout")').first.click(timeout=5000)
            print("   ↩ Logout feito.")
        except: pass

    except Exception as e: print(f"   ❌ Erro: {e}")
    finally: browser.close()

def main():
    try:
        # 1. Verifica Permissão
        if not verificar_licenca_online():
            input("Enter para sair..."); return

        # 2. Verifica Update
        verificar_atualizacao()

        # 3. Prepara Ambiente
        browser_path = verificar_e_instalar_navegador()
        contas = setup_contas()
        if not contas: return

        # 4. Executa
        with sync_playwright() as p:
            for acc in contas:
                do_checkin_for_account(p, acc["email"], acc["password"], browser_path)
                tempo = random.randint(10, 20)
                print(f"--- Aguardando {tempo}s ---")
                time.sleep(tempo)
        print("\n=== FINALIZADO ===")
    except Exception as e:
        print(f"\n[ERRO GERAL] {e}")
        import traceback; traceback.print_exc()
    input("Enter para fechar...")

if __name__ == "__main__":
    main()