import os
import time
import shutil
import tempfile
import requests
from DrissionPage import ChromiumPage, ChromiumOptions
from fabricador.modules.network import obter_proxy_novada

# ==========================================
# 🔧 GERADOR DA EXTENSÃO V2 (AUTH ONLY) - CAMINHO SEGURO
# ==========================================
def gerar_extensao_v2_temp(user, password):
    # Usa %TEMP% para garantir caminho curto, sem espaços e sem acentos
    temp_dir = tempfile.gettempdir()
    pasta_destino = os.path.join(temp_dir, "novada_auth_v2_final")
    
    # Limpa e recria para garantir que não tenha lixo
    if os.path.exists(pasta_destino):
        try: shutil.rmtree(pasta_destino, ignore_errors=True)
        except: pass
    os.makedirs(pasta_destino, exist_ok=True)

    print(f"   🔨 Criando extensão em LOCAL SEGURO: {pasta_destino}")

    # MANIFEST V2 (Infalível para Auth em automação)
    manifest_json = """
    {
        "manifest_version": 2,
        "name": "Novada Auth V2 Fixed",
        "version": "1.0",
        "permissions": [
            "proxy", 
            "tabs", 
            "<all_urls>", 
            "webRequest", 
            "webRequestBlocking"
        ],
        "background": {
            "scripts": ["background.js"]
        }
    }
    """

    # Script simples que apenas entrega a senha quando o Proxy pedir
    background_js = f"""
    chrome.webRequest.onAuthRequired.addListener(
        function(details) {{
            console.log("🔐 Entregando credenciais para: " + details.challenger.host);
            return {{
                authCredentials: {{
                    username: "{user}",
                    password: "{password}"
                }}
            }};
        }},
        {{urls: ["<all_urls>"]}},
        ["blocking"]
    );
    """

    with open(os.path.join(pasta_destino, "manifest.json"), "w", encoding='utf-8') as f:
        f.write(manifest_json)
    
    with open(os.path.join(pasta_destino, "background.js"), "w", encoding='utf-8') as f:
        f.write(background_js)
        
    return pasta_destino

# ==========================================
# 🚀 EXECUÇÃO
# ==========================================
def rodar():
    print("🔵 === TESTE FINAL: HÍBRIDO BLINDADO (ARG + EXT V2) ===")

    # 1. Obter e Parsear Proxy
    try:
        dados = obter_proxy_novada()['http'] # Formato: http://user:pass@host:port
        
        # Limpeza robusta da string
        limpo = dados.split("://")[1] if "://" in dados else dados
        partes = limpo.rsplit("@", 1)
        credenciais = partes[0]
        servidor = partes[1]
        
        user, senha = credenciais.split(":")
        host, port = servidor.split(":")
        
        print(f"   🎯 Target: {host}:{port}")
    except Exception as e:
        print(f"❌ Erro parse: {e}")
        return

    # 2. Gerar Extensão de Auth na pasta TEMP
    path_ext = gerar_extensao_v2_temp(user, senha)

    # 3. Configurar Browser
    co = ChromiumOptions()
    co.set_argument('--no-first-run')
    
    # A) FORÇA BRUTA: Define o proxy via flag (Obrigatório conectar por aqui)
    co.set_argument(f'--proxy-server={host}:{port}')
    
    # B) INTELIGÊNCIA: Carrega a extensão para digitar a senha
    co.set_argument(f'--load-extension={path_ext}')
    
    # C) Perfil Limpo e Seguro
    user_data = os.path.join(tempfile.gettempdir(), "perfil_debug_blindado")
    if os.path.exists(user_data):
        try: shutil.rmtree(user_data, ignore_errors=True)
        except: pass
    co.set_user_data_path(user_data)

    print("   🌐 Abrindo navegador...")
    try:
        page = ChromiumPage(addr_or_opts=co)
    except Exception as e:
        print(f"❌ Erro ao abrir navegador: {e}")
        return

    # Diagnóstico Visual
    print("   🕵️‍♂️  Verificando Extensões...")
    page.get("chrome://extensions")
    time.sleep(2) # Pausa para você ver se a extensão apareceu

    print("   🕵️‍♂️  Verificando IP...")
    # Tenta abrir o IP check
    tab = page.new_tab("https://api.ipify.org?format=json")
    
    print("   ⏳ Carregando...")
    time.sleep(5)
    
    html = tab.html
    print(f"\n   📄 RESULTADO HTML:\n   {html}")
    
    if "45.231.138.170" in html:
        print(f"\n❌ FALHA: IP REAL VAZOU! (Verifique se desligou o IPv6)")
    elif "json" in html and "ip" in html:
        print(f"\n✅ SUCESSO ABSOLUTO! IP MUDOU e NÃO TEVE POPUP!")
    else:
        print(f"\n⚠️  Resultado inconclusivo (Possível erro de conexão/proxy morto)")

    input("\nEnter para fechar...")
    page.quit()

if __name__ == "__main__":
    rodar()