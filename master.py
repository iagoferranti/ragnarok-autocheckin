import os
import json
import time
import sys
import requests
import subprocess
import textwrap
import ctypes

# Habilita cores no CMD
os.system('')

# --- CLASSE DE ESTILO ---
class Cores:
    RESET = '\033[0m'
    VERDE = '\033[92m'
    AMARELO = '\033[93m'
    VERMELHO = '\033[91m'
    CIANO = '\033[96m'
    CINZA = '\033[90m'
    NEGRITO = '\033[1m'

# ===== CONFIGURAÇÕES =====
VERSAO_ATUAL = "1.0.1"
ARQUIVO_NOVAS = "novas_contas.json"
ARQUIVO_PRINCIPAL = "accounts.json"
ARQUIVO_CONFIG = "config.json"

# URLs CONFIGURADAS PARA SEU REPO
URL_VERSION_TXT = "https://raw.githubusercontent.com/iagoferranti/ragnarok-autocheckin/main/version.txt"
URL_DOWNLOAD_EXE = "https://github.com/iagoferranti/ragnarok-autocheckin/releases/latest/download/RagnarokMasterTool.exe"

URL_LISTA_VIP = "https://gist.githubusercontent.com/iagoferranti/2675637690215af512e1e83e1eaf5e84/raw/emails.json"

# Importa os módulos
try:
    import fabricador
    import checkin_bot_v2
except ImportError:
    print(f"{Cores.VERMELHO}❌ ERRO CRÍTICO:{Cores.RESET} Módulos 'fabricador.py' ou 'checkin_bot_v2.py' não encontrados.")
    input("Enter para sair...")
    sys.exit()

def limpar_tela():
    os.system('cls' if os.name == 'nt' else 'clear')

def exibir_logo():
    print(f"""{Cores.CIANO}
    ██████╗  █████╗  ██████╗     ███╗   ███╗ █████╗ ███████╗████████╗███████╗██████╗ 
    ██╔══██╗██╔══██╗██╔════╝     ████╗ ████║██╔══██╗██╔════╝╚══██╔══╝██╔════╝██╔══██╗
    ██████╔╝███████║██║  ███╗    ██╔████╔██║███████║███████╗   ██║   █████╗  ██████╔╝
    ██╔══██╗██╔══██║██║   ██║    ██║╚██╔╝██║██╔══██║╚════██║   ██║   ██╔══╝  ██╔══██╗
    ██║  ██║██║  ██║╚██████╔╝    ██║ ╚═╝ ██║██║  ██║███████║   ██║   ███████╗██║  ██║
    ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝     ╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝   ╚═╝   ╚══════╝╚═╝  ╚═╝
                               {Cores.AMARELO}⚡ LATAM EDITION v{VERSAO_ATUAL} ⚡{Cores.RESET}
    """)

def carregar_config():
    # 1. Defina aqui as configurações que devem ser geradas para o cliente
    config_padrao = {
        "licenca_email": "",
        "headless": False,
        "tag_email": "rag",
        "sobrenome_padrao": "Adamantio da Silva",
        "telegram_token": "",
        "telegram_chat_id": ""
    }
    
    # 2. Se o arquivo NÃO existir, o Python CRIA ele agora
    if not os.path.exists(ARQUIVO_CONFIG):
        print(f"{Cores.CINZA}⚙️  Criando arquivo de configuração padrão...{Cores.RESET}")
        try:
            with open(ARQUIVO_CONFIG, "w", encoding="utf-8") as f:
                json.dump(config_padrao, f, indent=4)
            return config_padrao
        except Exception as e:
            print(f"Erro ao criar config: {e}")
            return config_padrao

    # 3. Se existir, ele lê e atualiza campos faltantes (segurança extra)
    try:
        with open(ARQUIVO_CONFIG, "r", encoding="utf-8") as f:
            user_config = json.load(f)
            # Garante que chaves novas apareçam mesmo em configs antigas
            config_padrao.update(user_config)
            return config_padrao
    except:
        return config_padrao

# --- FUNÇÕES DE AUTO UPDATE ---
def get_base_path():
    if getattr(sys, 'frozen', False): return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def get_short_path(path):
    buffer = ctypes.create_unicode_buffer(1024)
    ctypes.windll.kernel32.GetShortPathNameW(path, buffer, 1024)
    return buffer.value

def verificar_atualizacao():
    # Só roda se for EXE compilado
    if not getattr(sys, 'frozen', False): return

    print(f"\n{Cores.CIANO}🔄 Verificando atualizações...{Cores.RESET}")
    try:
        r = requests.get(URL_VERSION_TXT, timeout=5)
        if r.status_code == 200:
            versao_nuvem = r.text.strip()
            if versao_nuvem != VERSAO_ATUAL:
                print(f"{Cores.AMARELO}🚨 NOVA VERSÃO DISPONÍVEL: {versao_nuvem}{Cores.RESET}")
                print(f"Sua versão: {VERSAO_ATUAL}")
                if input("   >> Atualizar agora? (S/N): ").lower() == 's':
                    realizar_update()
                    sys.exit() # Fecha para atualizar
            else:
                print(f"{Cores.VERDE}✅ Sistema atualizado.{Cores.RESET}")
                time.sleep(1)
    except:
        print(f"{Cores.CINZA}(Skip update check){Cores.RESET}")

def realizar_update():
    print(f"\n{Cores.CIANO}📥 Baixando nova versão...{Cores.RESET}")
    try:
        base_dir = get_base_path()
        nome_exe = os.path.basename(sys.executable)
        caminho_novo = os.path.join(base_dir, "update_temp.exe")

        r = requests.get(URL_DOWNLOAD_EXE, stream=True)
        with open(caminho_novo, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192): f.write(chunk)
        
        print(f"{Cores.VERDE}✅ Download concluído! Reiniciando...{Cores.RESET}")
        time.sleep(1)

        try: base_short = get_short_path(base_dir)
        except: base_short = base_dir
        
        bat_script = textwrap.dedent(f"""
            @echo off
            chcp 65001 >NUL
            timeout /t 2 >NUL
            taskkill /PID {os.getpid()} /F > NUL 2>&1
            :LOOP
            del "{nome_exe}" > NUL 2>&1
            if exist "{nome_exe}" (timeout /t 1 >NUL & goto LOOP)
            ren "update_temp.exe" "{nome_exe}"
            cd /d "{base_short}"
            start "" "{nome_exe}"
            del "%~f0" & exit
        """)
        
        bat_path = os.path.join(base_dir, "updater.bat")
        with open(bat_path, "w") as f: f.write(bat_script)
        subprocess.Popen([bat_path], shell=True)
    except Exception as e:
        print(f"{Cores.VERMELHO}Erro update: {e}{Cores.RESET}")
        input()

# --- SISTEMA DE LOGIN ---
def autenticar_usuario():
    limpar_tela()
    exibir_logo()
    print(f"{Cores.NEGRITO}🔒 ÁREA RESTRITA - AUTENTICAÇÃO{Cores.RESET}\n")

    config = carregar_config()
    email = config.get("licenca_email", "")
    path_licenca = "licenca.txt"
    
    if not email and os.path.exists(path_licenca):
        try: 
            with open(path_licenca, "r") as f: email = f.read().strip()
        except: pass
    
    if not email:
        email = input("✉️  Digite seu E-mail de Licença: ").strip()
    else:
        print(f"👤 Usuário detectado: {Cores.AMARELO}{email}{Cores.RESET}")
        print("⏳ Verificando permissões online...")

    try:
        r = requests.get(URL_LISTA_VIP, timeout=10)
        if r.status_code != 200:
            print(f"\n{Cores.VERMELHO}❌ Erro de conexão.{Cores.RESET}")
            return None, None

        try:
            dados_licenca = r.json()
            if isinstance(dados_licenca, list):
                dados_licenca = {e: ["all"] for e in dados_licenca}
            
            dados_licenca = {k.lower().strip(): v for k, v in dados_licenca.items()}
            email_norm = email.lower().strip()

            if email_norm in dados_licenca:
                permissoes = dados_licenca[email_norm]
                with open(path_licenca, "w") as f: f.write(email_norm)
                print(f"\n{Cores.VERDE}✅ Acesso Liberado! Plano: {str(permissoes).upper()}{Cores.RESET}")
                time.sleep(1.5)
                return email_norm, permissoes
            else:
                print(f"\n{Cores.VERMELHO}⛔ Sem licença ativa.{Cores.RESET}")
                if os.path.exists(path_licenca): os.remove(path_licenca)
                
        except json.JSONDecodeError:
            print(f"\n{Cores.VERMELHO}❌ Erro no banco de dados.{Cores.RESET}")
            
    except Exception as e:
        print(f"\n{Cores.VERMELHO}❌ Erro: {e}{Cores.RESET}")

    return None, None

# --- UNIFICAÇÃO ---
def unificar_contas():
    limpar_tela()
    exibir_logo()
    print(f"{Cores.AMARELO}🔄 UNIFICADOR DE CONTAS{Cores.RESET}\n")

    if not os.path.exists(ARQUIVO_NOVAS):
        print(f"⚠️ Arquivo '{ARQUIVO_NOVAS}' não encontrado.")
        input("\nEnter para voltar...")
        return

    try:
        with open(ARQUIVO_NOVAS, "r", encoding="utf-8") as f:
            novas_raw = json.load(f)
    except:
        print("❌ Erro ao ler arquivo.")
        return

    contas_validas = [c for c in novas_raw if c.get('status') == 'PRONTA_PARA_FARMAR']
    if not contas_validas:
        print("⚠️ Nenhuma conta válida encontrada.")
        input("\nEnter para voltar...")
        return

    print(f"   -> Processando {len(contas_validas)} contas novas...")

    contas_principais = []
    if os.path.exists(ARQUIVO_PRINCIPAL):
        try:
            with open(ARQUIVO_PRINCIPAL, "r") as f:
                contas_principais = json.load(f)
        except: pass

    emails_existentes = set(c['email'] for c in contas_principais)
    adicionadas = 0

    for conta in contas_validas:
        if conta['email'] not in emails_existentes:
            contas_principais.append({"email": conta['email'], "password": conta['password']})
            emails_existentes.add(conta['email'])
            adicionadas += 1

    if adicionadas > 0:
        try:
            with open(ARQUIVO_PRINCIPAL, "w", encoding="utf-8") as f:
                json.dump(contas_principais, f, indent=4)
            print(f"\n{Cores.VERDE}✅ {adicionadas} contas integradas!{Cores.RESET}")
            if input(f"\nLimpar arquivo de fabricação? (s/n): ").lower() == 's':
                with open(ARQUIVO_NOVAS, "w") as f: json.dump([], f)
        except: print("Erro ao salvar.")
    else:
        print("\nℹ️ Nenhuma conta nova.")
    input("\nEnter para voltar...")

# --- MENU PRINCIPAL ---
def main():
    # 1. Autentica
    email_usuario, permissoes = autenticar_usuario()
    if not email_usuario:
        input("\nEnter para sair...")
        sys.exit()

    # 2. Verifica Update (Novo)
    verificar_atualizacao()

    while True:
        limpar_tela()
        exibir_logo()
        print(f"👤 Usuário: {Cores.CIANO}{email_usuario}{Cores.RESET}")
        print(f"🔑 Permissões: {Cores.AMARELO}{permissoes}{Cores.RESET}")
        print("\nEscolha uma operação disponível:\n")

        opcoes_validas = []

        if "all" in permissoes or "fabricador" in permissoes:
            print(f"  [1] 🏭 FABRICADOR DE CONTAS")
            opcoes_validas.append('1')
        else:
            print(f"  {Cores.CINZA}[1] 🔒 Fabricador (Bloqueado){Cores.RESET}")

        if "all" in permissoes or "checkin" in permissoes:
            print(f"  [2] 🎰 AUTO FARM (Check-in + Roleta)")
            opcoes_validas.append('2')
        else:
            print(f"  {Cores.CINZA}[2] 🔒 Auto Farm (Bloqueado){Cores.RESET}")

        print(f"  [3] 🔗 UNIFICAR CONTAS")
        opcoes_validas.append('3')
        print(f"  [0] ❌ SAIR")
        opcoes_validas.append('0')
        
        opcao = input("\n>> Digite o número: ").strip()

        if opcao not in opcoes_validas:
            print(f"\n{Cores.VERMELHO}Opção inválida.{Cores.RESET}")
            time.sleep(1)
            continue

        if opcao == '1':
            limpar_tela()
            try: fabricador.executar()
            except Exception as e: print(f"Erro: {e}"); input()

        elif opcao == '2':
            limpar_tela()
            if not os.path.exists(ARQUIVO_PRINCIPAL):
                print(f"{Cores.AMARELO}⚠️ Arquivo '{ARQUIVO_PRINCIPAL}' não encontrado!{Cores.RESET}")
                input("\nEnter para voltar...")
                continue
            try: checkin_bot_v2.executar()
            except Exception as e: print(f"Erro: {e}"); input()

        elif opcao == '3':
            unificar_contas()

        elif opcao == '0':
            print("\nAté logo! 👋")
            time.sleep(1)
            break

if __name__ == "__main__":
    main()