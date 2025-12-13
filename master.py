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
def obter_versao_local():
    """Lê a versão do arquivo version.txt embutido ou na pasta"""
    try:
        # Se estiver rodando como .exe (PyInstaller)
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            # Se estiver rodando como script .py normal
            base_path = os.path.dirname(os.path.abspath(__file__))
            
        caminho_arquivo = os.path.join(base_path, "version.txt")
        
        if os.path.exists(caminho_arquivo):
            with open(caminho_arquivo, "r", encoding="utf-8") as f:
                return f.read().strip()
    except: pass
    return "0.0.0" # Fallback se der erro

VERSAO_ATUAL = obter_versao_local() # <--- AGORA ELE LÊ DO ARQUIVO

# ===== CONFIGURAÇÕES =====
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

# --- WIZARD DE CONFIGURAÇÃO ---
def criar_config_interativo():
    limpar_tela()
    exibir_logo()
    print(f"{Cores.VERDE}⚙️  BEM-VINDO AO ASSISTENTE DE CONFIGURAÇÃO ⚙️{Cores.RESET}")
    print("Vamos configurar seu ambiente na primeira execução.\n")
    
    config = {
        "licenca_email": "",
        "headless": False,
        "tag_email": "rag",
        "sobrenome_padrao": "Silva",
        "telegram_token": "",
        "telegram_chat_id": "",
        "smailpro_api_key": ""
    }

    # 1. Modo Janela
    print(f"{Cores.AMARELO}[1] MODO DE VISUALIZAÇÃO{Cores.RESET}")
    print("Você deseja ver o navegador trabalhando? (Recomendado para evitar bloqueios)")
    resp_head = input("   >> Ver janela do Chrome? (S/N) [Padrão: S]: ").strip().lower()
    if resp_head == 'n':
        print(f"   ⚠️  {Cores.VERMELHO}Atenção: Modo Invisível aumenta risco de Cloudflare.{Cores.RESET}")
        config["headless"] = True
    else:
        config["headless"] = False
    print("")

    # 2. Tag de Email
    print(f"{Cores.AMARELO}[2] TAG DE E-MAIL{Cores.RESET}")
    print("Prefixo usado nos e-mails temporários (ex: userRAG123@...).")
    resp_tag = input("   >> Digite a TAG (Enter para 'rag'): ").strip()
    config["tag_email"] = resp_tag if resp_tag else "rag"
    print("")

    # 3. Sobrenome
    print(f"{Cores.AMARELO}[3] SOBRENOME PADRÃO{Cores.RESET}")
    print("Sobrenome usado no cadastro das contas.")
    resp_sobre = input("   >> Digite o Sobrenome (Enter para 'Silva'): ").strip()
    config["sobrenome_padrao"] = resp_sobre if resp_sobre else "Silva"
    print("")

    # 4. Telegram
    print(f"{Cores.AMARELO}[4] NOTIFICAÇÕES TELEGRAM (Opcional){Cores.RESET}")
    resp_token = input("   >> Token do Bot (Enter para pular): ").strip()
    if resp_token:
        config["telegram_token"] = resp_token
        config["telegram_chat_id"] = input("   >> Chat ID: ").strip()
    print("")

    # 5. Licença
    print(f"{Cores.AMARELO}[5] LICENÇA{Cores.RESET}")
    config["licenca_email"] = input("   >> Seu E-mail de Licença (Enter para pular): ").strip()

    print(f"\n{Cores.VERDE}✅ Configuração Concluída! Salvando...{Cores.RESET}")
    try:
        with open(ARQUIVO_CONFIG, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
        time.sleep(2)
        return config
    except Exception as e:
        print(f"Erro ao salvar: {e}")
        time.sleep(3)
        return config

def carregar_config():
    if not os.path.exists(ARQUIVO_CONFIG):
        return criar_config_interativo()

    try:
        with open(ARQUIVO_CONFIG, "r", encoding="utf-8") as f:
            user_config = json.load(f)
            # Garante chaves mínimas caso o arquivo seja antigo
            padrao = {"headless": False, "tag_email": "rag"} 
            padrao.update(user_config)
            return padrao
    except:
        return criar_config_interativo() # Se der erro lendo, recria

# --- FUNÇÕES DE AUTO UPDATE ---
def get_base_path():
    if getattr(sys, 'frozen', False): return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def get_short_path(path):
    buffer = ctypes.create_unicode_buffer(1024)
    ctypes.windll.kernel32.GetShortPathNameW(path, buffer, 1024)
    return buffer.value

def verificar_atualizacao():
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
                    # --- AVISO DE SEGURANÇA ---
                    print(f"\n{Cores.AMARELO}⚠️  ATENÇÃO - NÃO FECHE A JANELA:{Cores.RESET}")
                    print(f"   1. Esta tela irá {Cores.NEGRITO}piscar e fechar{Cores.RESET} em instantes.")
                    print(f"   2. Aguarde até que uma {Cores.NEGRITO}NOVA janela se abra sozinha{Cores.RESET}.")
                    print(f"   {Cores.CINZA}(Isso garante que a atualização foi aplicada){Cores.RESET}")
                    time.sleep(10)
                    realizar_update()
                    sys.exit()
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
        
        print(f"{Cores.VERDE}✅ Download concluído!{Cores.RESET}")
         
        print(f"\n{Cores.CIANO}🔄 Reiniciando...{Cores.RESET}")

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

# --- SISTEMA DE LOGIN E VERIFICAÇÃO ---

def verificar_licenca_online(permissao_necessaria="all"):
    """
    Função acessada pelos módulos externos para validar a licença silenciosamente.
    Lê o e-mail do arquivo local e valida no Gist.
    """
    path_licenca = "licenca.txt"
    email = ""
    
    # Tenta ler o email salvo
    if os.path.exists(path_licenca):
        try: 
            with open(path_licenca, "r") as f: email = f.read().strip()
        except: pass
    
    if not email: return False

    try:
        r = requests.get(URL_LISTA_VIP, timeout=5)
        if r.status_code == 200:
            dados = r.json()
            if isinstance(dados, list): dados = {e: ["all"] for e in dados}
            dados = {k.lower().strip(): v for k, v in dados.items()}
            
            if email.lower().strip() in dados:
                perms = dados[email.lower().strip()]
                if "all" in perms or permissao_necessaria in perms:
                    return True
    except: 
        pass 
        
    return False

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

    # 2. Verifica Update
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