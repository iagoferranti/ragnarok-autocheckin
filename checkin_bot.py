import os
import sys
import json
import time
import random
import requests
import subprocess

# --- DEFINIÇÃO DE PASTAS ---
def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

pasta_navegadores = os.path.join(get_base_path(), "navegadores")
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = pasta_navegadores

from playwright.sync_api import sync_playwright
from playwright.__main__ import main as playwright_installer

# ===== CONFIGURAÇÕES =====
VERSAO_ATUAL = "1.1"
NOME_EXECUTAVEL = "AutoCheckin.exe"

URL_VERSION_TXT = "https://raw.githubusercontent.com/iagoferranti/ragnarok-autocheckin/refs/heads/main/version.txt"
URL_DOWNLOAD_EXE = "https://github.com/iagoferranti/ragnarok-autocheckin/releases/latest/download/AutoCheckin.exe"
URL_LISTA_VIP = "https://gist.githubusercontent.com/iagoferranti/2675637690215af512e1e83e1eaf5e84/raw/emails.json"

LOGIN_URL = "https://ro.gnjoylatam.com/pt/event/decemberroulette"
CHECKIN_URL = "https://ro.gnjoylatam.com/pt/event/decemberroulette"
HEADLESS = False 
WAIT_TIMEOUT_MS = 60000 


# ===== SISTEMA DE ATUALIZAÇÃO (MODO AGRESSIVO) =====
def realizar_atualizacao_auto():
    print("\n[UPDATE] Baixando nova versão... Aguarde...")
    try:
        # 1. Baixa o novo arquivo
        r = requests.get(URL_DOWNLOAD_EXE, stream=True)
        nome_temp = "update_new.exe"
        caminho_temp = os.path.join(get_base_path(), nome_temp)
        
        with open(caminho_temp, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # 2. Identifica o processo atual
        nome_atual = os.path.basename(sys.executable)
        pid_atual = os.getpid() # Pega o ID do processo para matar ele com certeza
        caminho_bat = os.path.join(get_base_path(), "update.bat")
        
        # 3. Script BAT Assassino
        # - Espera 2s
        # - Tenta matar o processo antigo pelo PID (garantia extra)
        # - Deleta o arquivo antigo
        # - Renomeia o novo
        # - Inicia o novo
        bat_script = f"""
        @echo off
        timeout /t 2 /nobreak > NUL
        taskkill /PID {pid_atual} /F > NUL 2>&1
        
        :LOOP
        del "{nome_atual}"
        if exist "{nome_atual}" (
            timeout /t 1 /nobreak > NUL
            goto LOOP
        )
        
        ren "{nome_temp}" "{nome_atual}"
        start "" "{nome_atual}"
        del "%~f0"
        """
        
        with open(caminho_bat, "w") as f: f.write(bat_script)
        
        print("[UPDATE] Reiniciando em 3 segundos...")
        
        # 4. Executa o BAT
        subprocess.Popen([caminho_bat], shell=True)
        
        # 5. PUXA A TOMADA (Sai sem exceções)
        os._exit(0)

    except Exception as e:
        print(f"[ERRO UPDATE] {e}")
        input("Enter para continuar na versão atual...")

def verificar_atualizacao():
    if not getattr(sys, 'frozen', False): return
    print(f"\n[UPDATE] Versão instalada: {VERSAO_ATUAL}")
    try:
        r = requests.get(URL_VERSION_TXT)
        if r.status_code == 200:
            remota = r.text.strip()
            if remota != VERSAO_ATUAL:
                print(f"🚨 NOVA VERSÃO DISPONÍVEL: {remota}")
                msg = input("Deseja atualizar agora? (S/N): ").lower()
                if msg == 's':
                    realizar_atualizacao_auto()
                    # Garante parada aqui se o os._exit falhar (impossível, mas...)
                    return True 
            else:
                print("[UPDATE] Sistema atualizado.")
    except: pass
    return False

# ===== RESTO DAS FUNÇÕES (IGUAIS) =====
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

    print("[SISTEMA] Baixando navegador (1ª vez)...")
    try:
        sys.argv = ["playwright", "install", "chromium"]
        try: playwright_installer()
        except SystemExit: pass
        
        executavel = encontrar_executavel_chrome()
        if not executavel: raise Exception("Executável não encontrado.")
        print("[SISTEMA] Pronto!")
        return executavel
    except Exception as e:
        print(f"\n[ERRO] {e}")
        input("Enter para sair...")
        sys.exit(1)

def verificar_licenca_online():
    print("\n[SEGURANÇA] Verificando licença...")
    arquivo_licenca = os.path.join(get_base_path(), "licenca.txt")
    email_usuario = ""
    if os.path.exists(arquivo_licenca):
        try:
            with open(arquivo_licenca, "r") as f: email_usuario = f.read().strip()
        except: pass
    if not email_usuario:
        print("Este software é restrito.")
        email_usuario = input(">> Seu E-mail: ").strip()
    try:
        r = requests.get(URL_LISTA_VIP)
        if r.status_code != 200: return False
        try: lista = r.json()
        except: lista = r.text.splitlines()
        if any(email_usuario.lower() == email.lower() for email in lista):
            print(f"✅ Autorizado: {email_usuario}")
            with open(arquivo_licenca, "w") as f: f.write(email_usuario)
            return True
        else:
            print("⛔ ACESSO NEGADO.")
            if os.path.exists(arquivo_licenca): os.remove(arquivo_licenca)
            return False
    except: return False

def setup_contas():
    caminho = os.path.join(get_base_path(), "accounts.json")
    if os.path.exists(caminho):
        try:
            with open(caminho, "r", encoding="utf-8") as f: return json.load(f)
        except: pass
    print("\n=== CONFIGURAÇÃO CONTAS ===")
    while True:
        try:
            qtd = int(input(">> Quantas contas? "))
            if qtd > 0: break
        except: pass
    novas = [{"email": input("Email: ").strip(), "password": input("Senha: ").strip()} for _ in range(qtd)]
    try:
        with open(caminho, "w", encoding="utf-8") as f: json.dump(novas, f, indent=4)
    except: pass
    return novas

# ... (Funções do bot: digitar_humano, tentar_clicar_checkbox, etc. MANTENHA ELAS AQUI) ...
# Para economizar espaço, vou assumir que você tem elas salvas. Se não, avise que mando tudo de novo.
def digitar_humano(page, seletor, texto):
    try:
        page.bring_to_front()
        page.focus(seletor)
        page.type(seletor, texto, delay=random.randint(50, 150))
    except: page.fill(seletor, texto)

def tentar_clicar_checkbox(page):
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
    except: pass

def aguardar_validacao_ou_refresh(page, tentativa_atual):
    print("   🛡️ Verificando segurança...")
    inicio = time.time()
    while time.time() - inicio < 20:
        if page.locator("text=Sucesso").count() > 0 or page.locator("text=concluída").count() > 0:
            print("      ✅ Sucesso Automático!")
            time.sleep(1); return "OK"
        if verificar_se_precisa_clique(page):
            if tentativa_atual < 2:
                print("      ⚠️ Checkbox pede clique. Forçando F5..."); return "REFRESH"
            else:
                print("      ⚠️ Clicando forçado..."); clicar_checkbox_forca_bruta(page); time.sleep(2)
        if page.locator("text=Verificando segurança").count() > 0 or page.locator("text=Just a moment").count() > 0:
            if time.time() - inicio > 15 and tentativa_atual < 2:
                print("      ⚠️ Travou. Forçando F5..."); return "REFRESH"
            print("      ⏳ Processando..."); time.sleep(2); continue
        if time.time() - inicio > 5:
            print("      ❓ Texto sumiu. Seguindo..."); return "OK"
    return "TIMEOUT"

def limpar_overlays(page):
    try:
        page.evaluate("""const selectors=['.styles_dimd_layer__NtwPg','.cookieprivacy_cookieprivacy__Mz1XD','div[class*="modal"]'];selectors.forEach(sel=>document.querySelectorAll(sel).forEach(el=>el.remove()));""")
    except: pass

def obter_url_evento(browser_path):
    arquivo_config = os.path.join(get_base_path(), "config_evento.json")
    if os.path.exists(arquivo_config):
        try:
            with open(arquivo_config, "r") as f:
                dados = json.load(f)
                if time.time() - dados.get("timestamp", 0) < 86400:
                    print(f"[EVENTO] Usando URL salva: {dados['url']}")
                    return dados['url']
        except: pass

    print("\n[EVENTO] Buscando URL da Máquina PonPon no site oficial...")
    nova_url = None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=browser_path, headless=True)
            page = browser.new_page()
            try:
                page.goto("https://www.gnjoylatam.com/pt", timeout=30000)
                botao = page.locator("text=Máquina PonPon").first
                if botao.is_visible():
                    print("[EVENTO] Botão encontrado! Capturando link...")
                    with page.expect_navigation(timeout=10000):
                        botao.click()
                    nova_url = page.url
                    print(f"[EVENTO] URL descoberta: {nova_url}")
            except Exception as e: print(f"[AVISO] Busca automática falhou: {e}")
            finally: browser.close()
    except: pass

    if not nova_url or "roulette" not in nova_url:
        print("\n" + "="*50)
        print("⚠️ NÃO FOI POSSÍVEL ACHAR O LINK DO EVENTO")
        print("Acesse https://www.gnjoylatam.com/pt, clique na Máquina PonPon e copie o link.")
        print("="*50)
        while True:
            nova_url = input(">> Cole o Link do Evento aqui: ").strip()
            if "http" in nova_url: break
            print("Link inválido.")

    try:
        with open(arquivo_config, "w") as f: json.dump({"url": nova_url, "timestamp": time.time()}, f)
    except: pass
    return nova_url

def do_checkin_for_account(p, email: str, password: str, browser_path: str, url_evento: str):
    browser = p.chromium.launch(
        executable_path=browser_path,
        headless=HEADLESS,
        args=["--window-size=1366,768", "--force-device-scale-factor=0.75", "--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-background-timer-throttling", "--disable-backgrounding-occluded-windows", "--disable-renderer-backgrounding"]
    )
    context = browser.new_context(viewport={"width": 1366, "height": 768})
    page = context.new_page()
    page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    page.on("dialog", lambda dialog: (print(f"   [ALERTA SITE] {dialog.message}"), dialog.accept()))

    try:
        print(f"\n>>> Conta: {email}")
        max_retries = 3
        login_sucesso = False

        for tentativa in range(max_retries):
            print(f"   🔄 Login {tentativa + 1}/{max_retries}")
            try:
                if tentativa == 0:
                    try: page.goto(url_evento, timeout=WAIT_TIMEOUT_MS)
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
                    page.press("#password", "Enter"); time.sleep(3)
                    
                    try: page.wait_for_url("**roulette**", timeout=10000)
                    except: pass
                    
                    if page.locator('a.page_login__g41B0:has-text("Logout")').count() > 0:
                        login_sucesso = True; break
                    else: print("   [!] Login não confirmado.")
            except: pass

        if not login_sucesso: print(f"   ❌ Falha login."); return

        if page.url != url_evento: page.goto(url_evento); time.sleep(3)
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
            page.goto(url_evento)
            page.locator('a.page_login__g41B0:has-text("Logout")').first.click(timeout=5000)
            print("   ↩ Logout feito.")
        except: pass

    except Exception as e: print(f"   ❌ Erro: {e}")
    finally: browser.close()

def main():
    try:
        if not verificar_licenca_online(): input("Enter para sair..."); return
        
        # Se atualizou, o programa morre aqui e reinicia
        if verificar_atualizacao(): return 

        browser_path = verificar_e_instalar_navegador()
        url_evento = obter_url_evento(browser_path) # <--- Busca URL nova
        contas = setup_contas()
        if not contas: return

        with sync_playwright() as p:
            for acc in contas:
                do_checkin_for_account(p, acc["email"], acc["password"], browser_path, url_evento)
                tempo = random.randint(10, 20)
                print(f"--- Aguardando {tempo}s ---")
                time.sleep(tempo)
        print("\n=== FINALIZADO ===")
    except Exception as e:
        print(f"\n[ERRO GERAL] {e}")
    input("Enter para fechar...")

if __name__ == "__main__":
    main()