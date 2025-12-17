import os
import random
import time
import zipfile
import shutil
import urllib.parse
from DrissionPage import ChromiumPage, ChromiumOptions

# --- ARQUIVOS DE CONFIGURAÇÃO DA EXTENSÃO (CONSTANTES) ---
MANIFEST_JSON = """
{
    "version": "1.0.0",
    "manifest_version": 2,
    "name": "Chrome Proxy Auth",
    "permissions": [
        "proxy", "tabs", "unlimitedStorage", "storage", "<all_urls>", "webRequest", "webRequestBlocking"
    ],
    "background": { "scripts": ["background.js"] },
    "minimum_chrome_version": "22.0.0"
}
"""

# Script APENAS para autenticação (A rota é definida pelo --proxy-server)
BACKGROUND_JS = """
function callbackFn(details) {{
    return {{
        authCredentials: {{
            username: "{user}",
            password: "{passw}"
        }}
    }};
}}

chrome.webRequest.onAuthRequired.addListener(
    callbackFn,
    {{urls: ["<all_urls>"]}},
    ['blocking']
);
"""

def criar_extensao_auth_apenas(proxy_user, proxy_pass, pasta_destino="."):
    """Cria extensão focada APENAS em preencher usuário/senha."""
    nome_pasta = f"auth_plugin_{random.randint(10000,99999)}"
    caminho_pasta = os.path.join(pasta_destino, nome_pasta)
    
    if not os.path.exists(caminho_pasta): os.makedirs(caminho_pasta)
    
    with open(os.path.join(caminho_pasta, "manifest.json"), "w") as f:
        f.write(MANIFEST_JSON)
        
    js_content = BACKGROUND_JS.format(user=proxy_user, passw=proxy_pass)
    with open(os.path.join(caminho_pasta, "background.js"), "w") as f:
        f.write(js_content)
        
    return os.path.abspath(caminho_pasta)

def formatar_proxy_requests(proxy_string):
    proxy_string = proxy_string.strip()
    partes = proxy_string.split(':')
    if len(partes) == 4:
        ip, porta, user, senha = partes
        return {
            "ip": ip, "port": porta, "user": user, "pass": senha,
            "http": f"http://{user}:{senha}@{ip}:{porta}"
        }
    return None

def carregar_proxies():
    if not os.path.exists("proxies.txt"): return []
    with open("proxies.txt", "r") as f: return [l.strip() for l in f if l.strip()]

def main():
    print("🔍 INICIANDO DIAGNÓSTICO BLINDADO...")
    proxies = carregar_proxies()
    if not proxies:
        print("❌ proxies.txt vazio."); return

    proxy_bruto = random.choice(proxies)
    print(f"🎯 Testando: {proxy_bruto}")

    dados = formatar_proxy_requests(proxy_bruto)
    if not dados:
        print("❌ Formato de proxy inválido (use IP:PORT:USER:PASS)")
        return

    # 1. Cria extensão SÓ de autenticação
    plugin_path = criar_extensao_auth_apenas(dados['user'], dados['pass'])
    print(f"🧩 Extensão de Auth criada: {plugin_path}")

    # 2. Configura navegador
    co = ChromiumOptions()
    # AQUI ESTÁ O SEGREDO: Força o proxy via argumento (sem senha)
    co.set_argument(f"--proxy-server={dados['ip']}:{dados['port']}")
    # E adiciona a extensão para "digitar" a senha quando o Chrome pedir
    co.add_extension(plugin_path)
    
    page = ChromiumPage(addr_or_opts=co)

    try:
        print("🌍 Conectando...")
        page.get("https://ipv4.icanhazip.com", timeout=15)
        
        ip_detectado = page.ele("tag:body").text.strip()
        
        print("\n" + "="*40)
        print(f"🔹 IP Proxy Esperado: {dados['ip']}")
        print(f"🔹 IP Detectado:      {ip_detectado}")
        print("="*40 + "\n")

        if dados['ip'] in ip_detectado:
            print("✅ SUCESSO ABSOLUTO! Proxy funcionando e autenticado.")
        else:
            print("❌ FALHA ESTRANHA. O IP não bate, mas não deveria ter vazado.")

    except Exception as e:
        print(f"\n❌ ERRO DE CONEXÃO: {e}")
        print("👉 Isso é BOM! Significa que o proxy morreu mas seu IP REAL NÃO VAZOU.")
        print("👉 Tente rodar de novo para testar outro proxy da lista.")

    finally:
        input("\nEnter para limpar...")
        page.quit()
        if os.path.exists(plugin_path): shutil.rmtree(plugin_path)

if __name__ == "__main__":
    main()