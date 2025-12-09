from playwright.sync_api import sync_playwright
import json
import time
import random
import os

# ===== CONFIGURAÇÕES =====
LOGIN_URL = "https://ro.gnjoylatam.com/pt/event/decemberroulette"
CHECKIN_URL = "https://ro.gnjoylatam.com/pt/event/decemberroulette"

# False = Abre a janela para você ver (Melhor para Chrome)
HEADLESS = False 

def load_accounts():
    try:
        caminho = os.path.join(os.path.dirname(__file__), "accounts.json")
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print("❌ Erro: accounts.json não encontrado na mesma pasta.")
        return []

def digitar_como_humano(page, seletor, texto):
    """Digita letra por letra com delay aleatório."""
    try:
        page.focus(seletor)
        for char in texto:
            page.keyboard.type(char)
            # Delay bem curto, mas humano (entre 50ms e 150ms)
            time.sleep(random.uniform(0.05, 0.15))
    except:
        page.fill(seletor, texto)

def resolver_cloudflare_e_esperar(page):
    """Clica no checkbox e espera a validação."""
    print("   🛡️ Verificando segurança...")
    
    # 1. Tenta Clicar
    clicou = False
    try:
        # Procura iframe do desafio
        if page.locator("iframe[src*='turnstile'], iframe[src*='challenges']").count() > 0:
            iframe = page.frame_locator("iframe[src*='turnstile'], iframe[src*='challenges']").first
            
            # Tenta checkbox ou click no container
            if iframe.locator("input[type='checkbox']").count() > 0:
                iframe.locator("input[type='checkbox']").first.click(force=True)
                clicou = True
                print("      👆 Clique no checkbox enviado.")
            else:
                box = page.locator("iframe[src*='turnstile'], iframe[src*='challenges']").first.bounding_box()
                if box:
                    x = box["x"] + (box["width"] / 2)
                    y = box["y"] + (box["height"] / 2)
                    page.mouse.click(x, y)
                    clicou = True
                    print("      👆 Clique por coordenadas.")
    except: pass

    # 2. Se clicou (ou se já estava carregando), espera o texto sumir
    inicio = time.time()
    while time.time() - inicio < 20: # Espera até 20s
        texto_bloqueio = page.locator("text=Verificando segurança").count() > 0 or \
                         page.locator("text=Just a moment").count() > 0 or \
                         page.locator("text=Verifying").count() > 0
        
        if not texto_bloqueio:
            print("   ✅ Validação concluída (Caminho livre).")
            time.sleep(1) 
            return True
        
        print("   ⏳ Aguardando validação do servidor...")
        time.sleep(2)
    
    print("   ⚠️ O tempo de espera acabou, tentando seguir mesmo assim...")
    return False

def do_checkin(p, email, password):
    # --- MUDANÇA AQUI: Usando Chromium (Chrome) ---
    # channel="chrome" tenta usar o Chrome instalado no seu PC (mais humano impossível)
    # Se der erro, remova o 'channel="chrome"' para usar o Chromium padrão
    browser = p.chromium.launch(
        headless=HEADLESS, 
        channel="chrome", 
        args=["--disable-blink-features=AutomationControlled", "--start-maximized"]
    )
    
    context = browser.new_context(viewport={"width": 1366, "height": 768})
    page = context.new_page()

    # Truque para esconder que é robô no Chrome
    page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    try:
        print(f"\n >>> Conta: {email}")
        try: page.goto(LOGIN_URL, timeout=60000)
        except: pass
        
        resolver_cloudflare_e_esperar(page)

        # Lógica de Login
        seletor_login = 'a.page_login__g41B0:has-text("Login")'
        seletor_logout = 'a.page_login__g41B0:has-text("Logout")'

        if page.locator(seletor_logout).count() == 0:
            # Clica no Login se não estiver logado
            if page.locator(seletor_login).is_visible():
                page.locator(seletor_login).first.click()
                time.sleep(3)
            
            resolver_cloudflare_e_esperar(page)

            if page.locator("#email").is_visible():
                print("   -> Digitando e-mail...")
                digitar_como_humano(page, "#email", email)
                
                print("   -> Digitando senha...")
                digitar_como_humano(page, "#password", password)
                
                try: page.locator("input[type='checkbox']").first.check()
                except: pass
                
                # VERIFICAÇÃO CRÍTICA ANTES DE ENVIAR
                resolver_cloudflare_e_esperar(page)
                
                print("   -> Clicando em Continuar...")
                page.click("button.page_loginBtn__JUYeS")
                
                try: page.wait_for_url("**decemberroulette**", timeout=20000)
                except: pass

        # Lógica de Check-in
        if "decemberroulette" not in page.url:
            page.goto(CHECKIN_URL)
            time.sleep(3)

        try:
            btn = page.locator('img[alt="attendance button"]').first
            if btn.is_visible():
                btn.click()
                print(f"   ✅ CHECK-IN REALIZADO: {email}")
                time.sleep(3)
            else:
                print(f"   ℹ️ Botão não apareceu (Já feito ou login falhou).")
        except: pass

        # Logout
        try:
            page.goto(CHECKIN_URL)
            page.locator(seletor_logout).first.click()
            print("   ↩ Logout feito.")
        except: pass

    except Exception as e:
        print(f"   ❌ Erro: {e}")
    finally:
        browser.close()

def main():
    contas = load_accounts()
    with sync_playwright() as p:
        for conta in contas:
            do_checkin(p, conta["email"], conta["password"])
            tempo = random.randint(5, 15)
            print(f"   ... Aguardando {tempo}s ...")
            time.sleep(tempo)

if __name__ == "__main__":
    main()