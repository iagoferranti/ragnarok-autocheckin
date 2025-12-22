import os
import time
import shutil
import tempfile
from DrissionPage import ChromiumPage, ChromiumOptions

# Importa o SEU network.py
from fabricador.modules.network import obter_proxy_novada, criar_extensao_proxy

def rodar():
    print("🔵 === TESTE FINAL: SEU NETWORK.PY ===")

    # 1. Obter dados
    raw_proxy = obter_proxy_novada()['http'] # ex: http://user:pass@host:port
    
    # 2. Parse (Separar os dados)
    # Remove http://
    limpo = raw_proxy.split("://")[1]
    # Separa pelo último @
    partes = limpo.rsplit("@", 1)
    credenciais = partes[0]
    servidor = partes[1]
    
    user, senha = credenciais.split(":")
    host, port = servidor.split(":")

    print(f"   🔨 Host: {host}")
    print(f"   🔨 Port: {port}")
    
    # 3. Caminho Seguro (TEMP)
    temp_dir = tempfile.gettempdir()
    pasta_extensao = os.path.join(temp_dir, "teste_network_v3_safe")
    
    # Limpa se existir
    if os.path.exists(pasta_extensao):
        try: shutil.rmtree(pasta_extensao, ignore_errors=True)
        except: pass

    # 4. Cria a extensão usando SUA função
    path = criar_extensao_proxy(host, int(port), user, senha, pasta_extensao)
    
    if not path:
        print("❌ Erro ao criar extensão.")
        return

    # 5. Configura Browser
    co = ChromiumOptions()
    co.set_argument('--no-first-run')
    # Carrega a extensão
    co.set_argument(f'--load-extension={path}')
    
    # CRUCIAL: Removemos o --proxy-server pois sua extensão já faz isso
    co.remove_argument('--proxy-server') 

    # Perfil limpo
    user_data = os.path.join(temp_dir, "profile_teste_v3")
    if os.path.exists(user_data):
        try: shutil.rmtree(user_data, ignore_errors=True)
        except: pass
    co.set_user_data_path(user_data)

    print("   🌐 Abrindo navegador...")
    page = ChromiumPage(addr_or_opts=co)

    print("   🕵️‍♂️  Verificando IP...")
    time.sleep(3) # Tempo para o Service Worker acordar
    
    tab = page.new_tab("https://api.ipify.org?format=json")
    
    print("\n   📄 RESULTADO:")
    print(tab.html)
    
    print("\n   👉 Verifique se apareceu o IP ou se pediu senha/popup.")
    input("Enter para fechar...")
    page.quit()

if __name__ == "__main__":
    rodar()