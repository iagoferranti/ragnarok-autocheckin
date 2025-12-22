import os
import sys
import json
import time
import requests
import subprocess
import textwrap
import ctypes
import shutil
import re
import tempfile
import json_cleaner 
import provider_smailpro
import provider_email

from datetime import datetime

# Tenta importar premios_manager com tratamento de erro
try:
    import premios_manager
    from premios_manager import configurar_watchlist_manual
except ImportError:
    premios_manager = None

# Habilita cores no CMD
os.system('')

# --- CLASSE DE ESTILO PREMIUM ---
class Cores:
    RESET = '\033[0m'
    VERDE = '\033[92m'
    AMARELO = '\033[93m'
    VERMELHO = '\033[91m'
    CIANO = '\033[96m'
    AZUL = '\033[94m'
    MAGENTA = '\033[95m'
    CINZA = '\033[90m'
    NEGRITO = '\033[1m'
    ITALICO = '\033[3m'

# ===== CONFIGURAÇÕES GLOBAIS =====
ARQUIVO_NOVAS = "novas_contas.json"
ARQUIVO_PRINCIPAL = "accounts.json"
ARQUIVO_CONFIG = "config.json"
ARQUIVO_HISTORICO = "historico_diario.json"

# URLs DO GITHUB/GIST
URL_VERSION_TXT = "https://raw.githubusercontent.com/iagoferranti/ragnarok-autocheckin/main/version.txt"
URL_DOWNLOAD_EXE = "https://github.com/iagoferranti/ragnarok-autocheckin/releases/latest/download/RagnarokMasterTool.exe"
URL_LISTA_VIP = "https://gist.githubusercontent.com/iagoferranti/2675637690215af512e1e83e1eaf5e84/raw/emails.json"


def _download_to_file(url: str, dst: str, timeout=(5, 60)):
    with requests.get(url, stream=True, timeout=timeout) as r:
        r.raise_for_status()
        with open(dst, "wb") as f:
            for chunk in r.iter_content(65536):
                if chunk:
                    f.write(chunk)

def _norm_ver(v: str):
    nums = re.findall(r"\d+", v or "")
    return tuple(int(n) for n in nums[:4]) if nums else (0,)

def _is_newer_version(local, cloud):
    return _norm_ver(cloud) > _norm_ver(local)


# --- OBTENÇÃO DE VERSÃO ---
def obter_versao_local():
    try:
        base_path = sys._MEIPASS if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
        caminho = os.path.join(base_path, "version.txt")
        if os.path.exists(caminho):
            with open(caminho, "r", encoding="utf-8") as f: return f.read().strip()
    except: pass
    return "2.0.0"

VERSAO_ATUAL = obter_versao_local()

# --- DEFINIR TÍTULO DA JANELA (PREMIUM) ---
def definir_titulo():
    if os.name == 'nt':
        ctypes.windll.kernel32.SetConsoleTitleW(f"Ragnarok Master Tool v{VERSAO_ATUAL} | Premium Edition")

# --- IMPORTAÇÃO SEGURA (MODO BLINDADO) ---
try:
    # 1. FORÇA o PyInstaller a incluir o provider_email no pacote
    import provider_email 
    
    # 2. Importa DIRETAMENTE o módulo main, sem passar pelo __init__ do pacote
    # Isso evita o erro "cannot import name 'main'"
    from fabricador.main import executar as executar_fabricador
    
    # 3. Outros módulos
    import checkin_bot_v2
    import gerador_otp
    import uti_contas 
    import premios_manager
    # json_cleaner já foi importado no topo
    
    MODULOS_OK = True

except ImportError as e:
    MODULOS_OK = False
    ERRO_MODULO = str(e)

# --- VISUAL ---
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
    print(f"{Cores.CINZA}    Desenvolvido por: {Cores.MAGENTA}{Cores.NEGRITO}Iago Ferranti{Cores.RESET}\n")

# --- CONFIGURAÇÃO (WIZARD UNIFICADO) ---
def criar_config_interativo():
    limpar_tela()
    exibir_logo()
    print(f"{Cores.VERDE}⚙️  CONFIGURAÇÃO INICIAL{Cores.RESET}")
    print(f"{Cores.CINZA}Vamos configurar seu ambiente de trabalho.\n{Cores.RESET}")
    
    config = {
        "licenca_email": "",
        "headless": False,
        "tag_email": "rag",
        "sobrenome_padrao": "Silva",
        "telegram_token": "",
        "telegram_chat_id": ""
    }

    print(f"{Cores.AMARELO}[1] VISUALIZAÇÃO{Cores.RESET}")
    if input("   >> Ver o navegador trabalhando? (S/N) [Padrão: Sim]: ").lower() == 'n':
        print(f"   ⚠️  {Cores.CINZA}Modo Invisível (Headless) ativado.{Cores.RESET}")
        config["headless"] = True
    else:
        print(f"   ✅ {Cores.CINZA}Modo Visível ativado.{Cores.RESET}")
        config["headless"] = False
    print("")

    print(f"{Cores.AMARELO}[2] TELEGRAM (Opcional){Cores.RESET}")
    tk = input("   >> Token do Bot: ").strip()
    if tk:
        config["telegram_token"] = tk
        config["telegram_chat_id"] = input("   >> Chat ID: ").strip()
    print("")

    print(f"{Cores.AMARELO}[3] LICENÇA{Cores.RESET}")
    config["licenca_email"] = input("   >> E-mail da Licença: ").strip()

    print(f"{Cores.AMARELO}[4] SMAILPRO API (Opcional - Recomendado){Cores.RESET}")
    print(f"{Cores.CINZA}Se você tem chave da SmailPro para gerar GMAIL/OUTLOOK.{Cores.RESET}")
    sk = input("   >> API Key SmailPro: ").strip()
    if sk:
        config["smailpro_key"] = sk

    try:
        with open(ARQUIVO_CONFIG, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
        print(f"\n{Cores.VERDE}✅ Configuração salva com sucesso!{Cores.RESET}")
        time.sleep(1.5)
    except: pass
    return config

def carregar_config():
    if not os.path.exists(ARQUIVO_CONFIG):
        return criar_config_interativo()
    try:
        with open(ARQUIVO_CONFIG, "r", encoding="utf-8") as f:
            d = json.load(f)
            # Garante campos mínimos
            padrao = {"headless": False, "tag_email": "rag", "sobrenome_padrao": "Silva"}
            padrao.update(d)
            return padrao
    except:
        return criar_config_interativo()

CONF = carregar_config()

# --- UTILS ---
def get_base_path():
    if getattr(sys, 'frozen', False): return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def get_short_path(path):
    buffer = ctypes.create_unicode_buffer(1024)
    ctypes.windll.kernel32.GetShortPathNameW(path, buffer, 1024)
    return buffer.value

# --- SISTEMA DE UPDATE MELHORADO (SEM .CMD) ---
def verificar_atualizacao():
    if not getattr(sys, 'frozen', False): return # Só roda se for .exe

    print(f"{Cores.CINZA}🔄 Verificando atualizações...{Cores.RESET}")
    try:
        r = requests.get(URL_VERSION_TXT, timeout=5)
        versao_nuvem = r.text.strip()

        if _is_newer_version(VERSAO_ATUAL, versao_nuvem):
            print(f"\n{Cores.AMARELO}🚨 NOVA VERSÃO: {versao_nuvem}{Cores.RESET}")
            if input("   >> Atualizar agora? (S/N): ").lower() == 's':
                realizar_update_simples()
        else:
            # Limpeza silenciosa de arquivos .old antigos
            limpar_arquivos_antigos()
            print(f"{Cores.VERDE}✅ Sistema atualizado.{Cores.RESET}")
            time.sleep(0.5)
            
    except Exception as e:
        print(f"{Cores.CINZA}⚠️ Erro ao checar update: {e}{Cores.RESET}")


def limpar_arquivos_antigos():
    """Remove o .exe.old se existir de um update anterior"""
    try:
        exe_atual = sys.executable
        old_exe = exe_atual + ".old"
        if os.path.exists(old_exe):
            os.remove(old_exe)
    except: pass

def realizar_update_simples():
    """Atualiza renomeando o arquivo em execução"""
    print(f"\n{Cores.CIANO}📥 Baixando atualização...{Cores.RESET}")
    try:
        exe_atual = sys.executable
        dir_atual = os.path.dirname(exe_atual)
        exe_old = exe_atual + ".old"
        
        # Nome temporário para o download
        download_temp = os.path.join(dir_atual, "update_temp.tmp")

        # 1. Baixa o arquivo novo
        r = requests.get(URL_DOWNLOAD_EXE, stream=True, timeout=120)
        r.raise_for_status()
        
        with open(download_temp, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)

        # Validação básica
        if os.path.getsize(download_temp) < 200_000:
            raise Exception("Arquivo corrompido (muito pequeno).")

        print(f"{Cores.VERDE}✅ Download concluído! Aplicando...{Cores.RESET}")
        
        # 2. Renomeia o executável ATUAL para .old (Windows permite isso)
        if os.path.exists(exe_old):
            try: os.remove(exe_old)
            except: pass # Se não der, tenta sobrescrever
            
        os.rename(exe_atual, exe_old)

        # 3. Renomeia o arquivo baixado para o nome do executável original
        os.rename(download_temp, exe_atual)

        print(f"{Cores.VERDE}🚀 Reiniciando sistema...{Cores.RESET}")
        time.sleep(1)

        # 4. Inicia o novo processo
        subprocess.Popen([exe_atual])
        
        # 5. Encerra o processo atual
        sys.exit(0)

    except Exception as e:
        print(f"\n{Cores.VERMELHO}❌ Falha no update: {e}{Cores.RESET}")
        # Tenta restaurar se der erro
        try:
            if os.path.exists(exe_old) and not os.path.exists(exe_atual):
                os.rename(exe_old, exe_atual)
        except: pass
        input("Enter para continuar na versão antiga...")



# --- LICENÇA & AUTH ---
def verificar_licenca_online(permissao="all"):
    """Valida silenciosamente para uso nos módulos"""
    path = "licenca.txt"
    email = ""
    if os.path.exists(path):
        try: 
            with open(path, "r") as f: email = f.read().strip()
        except: pass
    
    if not email: return False

    try:
        r = requests.get(URL_LISTA_VIP, timeout=5)
        if r.status_code == 200:
            dados = r.json()
            if isinstance(dados, list): dados = {e: ["all"] for e in dados}
            dados = {k.lower().strip(): v for k, v in dados.items()}
            
            perms = dados.get(email.lower().strip())
            if perms and ("all" in perms or permissao in perms):
                return True
    except: pass
    return False

def autenticar_usuario():
    limpar_tela()
    exibir_logo()
    print(f"{Cores.NEGRITO}🔒 ÁREA RESTRITA{Cores.RESET}\n")

    # Tenta ler licença salva ou do config
    config = carregar_config()
    email = config.get("licenca_email", "")
    path_licenca = "licenca.txt"
    
    if not email and os.path.exists(path_licenca):
        try: 
            with open(path_licenca, "r") as f: email = f.read().strip()
        except: pass
    
    if not email:
        email = input("✉️  E-mail de Acesso: ").strip()
    else:
        print(f"👤 Usuário: {Cores.AMARELO}{email}{Cores.RESET}")
        print("⏳ Autenticando no servidor...")

    try:
        r = requests.get(URL_LISTA_VIP, timeout=10)
        if r.status_code != 200:
            print(f"\n{Cores.VERMELHO}❌ Servidor offline.{Cores.RESET}")
            return None, None

        dados = r.json()
        # Normalização para suportar lista antiga ou dict novo
        if isinstance(dados, list): dados = {e: ["all"] for e in dados}
        dados = {k.lower().strip(): v for k, v in dados.items()}
        
        email_norm = email.lower().strip()

        if email_norm in dados:
            perms = dados[email_norm]
            with open(path_licenca, "w") as f: f.write(email_norm)
            
            plano = "MASTER" if "all" in perms else "BÁSICO"
            print(f"\n{Cores.VERDE}✅ Acesso Liberado! Plano: {plano}{Cores.RESET}")
            time.sleep(1)
            return email_norm, perms
        else:
            print(f"\n{Cores.VERMELHO}⛔ Licença não encontrada ou expirada.{Cores.RESET}")
            if os.path.exists(path_licenca): os.remove(path_licenca)
            
    except Exception as e:
        print(f"\n{Cores.VERMELHO}❌ Erro de conexão: {e}{Cores.RESET}")

    return None, None

# --- FERRAMENTAS EXTRAS ---
def unificar_contas(silencioso=False):
    if not silencioso:
        limpar_tela()
        exibir_logo()
        print(f"{Cores.AMARELO}🔗 UNIFICADOR DE CONTAS{Cores.RESET}\n")

    if not os.path.exists(ARQUIVO_NOVAS):
        if not silencioso:
            print(f"⚠️  Arquivo '{ARQUIVO_NOVAS}' vazio.")
            time.sleep(2)
        return 0  # <--- RETORNA 0

    try:
        with open(ARQUIVO_NOVAS, "r", encoding="utf-8") as f: novas = json.load(f)
    except: return 0 # <--- RETORNA 0

    # Filtra apenas contas prontas
    validas = [c for c in novas if c.get('status') == 'PRONTA_PARA_FARMAR']
    
    if not validas:
        if not silencioso:
            print("⚠️  Nenhuma conta com status 'PRONTA_PARA_FARMAR' encontrada.")
            time.sleep(2)
        return 0 # <--- RETORNA 0

    if not silencioso:
        print(f"   -> Integrando {len(validas)} novas contas...")
    
    principais = []
    if os.path.exists(ARQUIVO_PRINCIPAL):
        try:
            with open(ARQUIVO_PRINCIPAL, "r") as f: principais = json.load(f)
        except: pass

    existentes = set(c['email'] for c in principais)
    count = 0

    for c in validas:
        if c['email'] not in existentes:
            principais.append({"email": c['email'], "password": c['password']})
            if "seed_otp" in c:
                principais[-1]["seed_otp"] = c["seed_otp"]
            
            existentes.add(c['email'])
            count += 1

    if count > 0:
        try:
            with open(ARQUIVO_PRINCIPAL, "w", encoding="utf-8") as f:
                json.dump(principais, f, indent=4)
            
            print(f"\n{Cores.VERDE}✅ {count} Novas contas integradas automaticamente!{Cores.RESET}")
            
            # Limpa automático no silencioso
            if silencioso or input(f"\n   >> Limpar arquivo de fabricação? (S/N): ").lower() == 's':
                with open(ARQUIVO_NOVAS, "w") as f: json.dump([], f)
                if not silencioso: print(f"   🗑️  Arquivo temporário limpo.")
            
            return count  # <--- AQUI ESTÁ A CHAVE: Retorna quantas salvou
        except: 
            print("❌ Erro ao salvar.")
            return 0
    else:
        if not silencioso:
            print("\nℹ️  Todas as contas já estavam cadastradas.")
        return 0 # <--- RETORNA 0
    
    if not silencioso:
        input("\nEnter para voltar...")
    return 0



def desligar_computador(segundos=30):
    """Agenda desligamento do Windows após X segundos."""
    try:
        if os.name == "nt":
            os.system(f"shutdown /s /t {int(segundos)}")
        else:
            os.system("shutdown -h now")
    except:
        pass

def cancelar_desligamento():
    """Cancela um desligamento agendado (Windows)."""
    try:
        if os.name == "nt":
            os.system("shutdown /a")
    except:
        pass

def confirmar_desligamento(timeout=10):
    """
    Confirma desligamento com timeout.
    Padrão: DESLIGAR (se não responder nada em X segundos).
    Para cancelar: pressione N dentro do tempo.
    """
    print(f"\n{Cores.AMARELO}🛑 Você escolheu finalizar DESLIGANDO o computador.{Cores.RESET}")
    print(f"{Cores.CINZA}   Pressione {Cores.NEGRITO}N{Cores.RESET}{Cores.CINZA} em até {timeout}s para CANCELAR.{Cores.RESET}")
    print(f"{Cores.CINZA}   (Se não fizer nada, vou assumir que é SIM){Cores.RESET}")

    inicio = time.time()

    # Windows: leitura não-bloqueante via msvcrt
    if os.name == "nt":
        try:
            import msvcrt
            while time.time() - inicio < timeout:
                if msvcrt.kbhit():
                    ch = msvcrt.getwch().lower()
                    if ch == 'n':
                        print(f"\n{Cores.AMARELO}⛔ Desligamento cancelado.{Cores.RESET}")
                        return False
                time.sleep(0.05)
        except:
            pass
    else:
        # Linux/mac: fallback simples (sem bloqueio real) -> assume SIM ao final
        while time.time() - inicio < timeout:
            time.sleep(0.2)

    print(f"\n{Cores.VERDE}✅ Nenhuma ação detectada. Desligamento CONFIRMADO.{Cores.RESET}")
    return True


def desligar_com_contagem(segundos=30):
    """Mostra contagem e permite cancelar."""
    try:
        print(f"\n{Cores.AMARELO}🛑 Desligando em {segundos}s...{Cores.RESET}")
        print(f"{Cores.CINZA}   (Digite 'c' e Enter para cancelar){Cores.RESET}")

        for i in range(segundos, 0, -1):
            # leitura simples “não-bloqueante” é chata no Windows; então fazemos um aviso + delay
            # e deixamos o cancelamento pelo shutdown /a se quiser.
            time.sleep(1)

        desligar_computador(0)
    except:
        desligar_computador(segundos)


# --- MENU PRINCIPAL ---
def main():
    definir_titulo()
    
    # 1. Checa Integridade
    if not MODULOS_OK:
        limpar_tela()
        exibir_logo()
        print(f"{Cores.VERMELHO}❌ ERRO CRÍTICO DE INTEGRIDADE{Cores.RESET}")
        print(f"Não foi possível carregar os módulos do sistema.")
        print(f"Detalhe: {ERRO_MODULO}")
        input("\nEnter para sair...")
        sys.exit()

    # 2. Login
    email_user, perms = autenticar_usuario()
    if not email_user:
        time.sleep(2); sys.exit()

    # 3. Update
    verificar_atualizacao()

    # 4. Loop Menu
    while True:
        limpar_tela()
        exibir_logo()
        print(f"👤 Licença: {Cores.CIANO}{email_user}{Cores.RESET}")
        print(f"📅 Data: {Cores.CINZA}{datetime.now().strftime('%d/%m/%Y')}{Cores.RESET}\n")
        
        print("Escolha uma ferramenta:\n")

        # Menu Dinâmico
        opcoes = []
        
        # --- FABRICADOR ---
        if "all" in perms or "fabricador" in perms:
            print(f"   {Cores.VERDE}[1]{Cores.RESET} 🏭 Fabricador de Contas")
            opcoes.append('1')
        else:
            print(f"   {Cores.CINZA}[1] 🔒 Fabricador (Bloqueado){Cores.RESET}")

        # --- AUTO FARM ---
        if "all" in perms or "checkin" in perms:
            print(f"   {Cores.VERDE}[2]{Cores.RESET} 🎰 Auto Farm (Check-in + Roleta)")
            opcoes.append('2')
        else:
            print(f"   {Cores.CINZA}[2] 🔒 Auto Farm (Bloqueado){Cores.RESET}")

        # --- AUTHENTICATOR ---
        print(f"   {Cores.VERDE}[3]{Cores.RESET} 🔐 Gerador de OTP (Authenticator)")
        opcoes.append('3')

        # --- FABRICADOR + SHUTDOWN ---
        if "all" in perms or "fabricador" in perms:
            print(f"   {Cores.VERDE}[4]{Cores.RESET} 🏭 Fabricador + Desligar")
            opcoes.append('4')
        else:
            print(f"   {Cores.CINZA}[4] 🔒 Fabricador + Desligar (Bloqueado){Cores.RESET}")

        # --- AUTO FARM + SHUTDOWN ---
        if "all" in perms or "checkin" in perms:
            print(f"   {Cores.VERDE}[5]{Cores.RESET} 🎰 Auto Farm + Desligar")
            opcoes.append('5')
        else:
            print(f"   {Cores.CINZA}[5] 🔒 Auto Farm + Desligar (Bloqueado){Cores.RESET}")
        
        # --- EXTRAS ---
        print(f"{Cores.CINZA}   {'-'*30}{Cores.RESET}") # Separador visual

        if "all" in perms or "checkin" in perms:
            print(f"   {Cores.VERDE}[6]{Cores.RESET} 🎁 Configurar Prêmios do Log")
            opcoes.append('6')

        print(f"   {Cores.VERDE}[7]{Cores.RESET} 📌 Sync Logs (Watchlist)")
        opcoes.append('7')
        
        print(f"   {Cores.VERDE}[8]{Cores.RESET} 🔗 Unificar Contas Novas")
        opcoes.append('8')

        # === NOVA OPÇÃO: UTI ===
        print(f"   {Cores.VERDE}[9]{Cores.RESET} 🚑 UTI de Contas (Reparar Falhas)")
        opcoes.append('9')

        print(f"   {Cores.VERDE}[10]{Cores.RESET} 🧹 Faxina JSON (Limpar Lixo)")
        opcoes.append('10')

        print(f"\n   {Cores.VERMELHO}[0]{Cores.RESET} Sair")
        opcoes.append('0')

        escolha = input("\n>> Opção: ").strip()

        if escolha not in opcoes:
            print(f"\n{Cores.VERMELHO}Opção inválida.{Cores.RESET}")
            time.sleep(1); continue

        # --- LÓGICA DAS OPÇÕES ---

        if escolha == '1':
            limpar_tela()
            try: 
                # 1. Fabrica
                executar_fabricador()
                
                # 2. Unifica e pega o número de sucessos
                qtd_novas = unificar_contas(silencioso=True)
                
                # 3. Lógica Automática
                if qtd_novas > 0:
                    print(f"\n{Cores.AMARELO}🚀 Detectadas {qtd_novas} novas contas! Iniciando Auto Farm...{Cores.RESET}")
                    print(f"{Cores.CINZA}(Se quiser cancelar, feche a janela agora){Cores.RESET}")
                    time.sleep(5) # Dá 5 segundos pro usuário ler, depois arranca
                    
                    checkin_bot_v2.executar()
                else:
                    print(f"\n{Cores.CINZA}⚠️ Nenhuma conta nova foi criada/unificada. Voltando ao menu...{Cores.RESET}")
                    time.sleep(3)

            except Exception as e: 
                print(f"{Cores.VERMELHO}Erro no fluxo Fabricador: {e}{Cores.RESET}")
                input()

        elif escolha == '2':
            limpar_tela()
            try: checkin_bot_v2.executar()
            except Exception as e:
                print(f"{Cores.VERMELHO}Erro no módulo Auto Farm: {e}{Cores.RESET}")
                input()

        elif escolha == '3':
            print(f"\n{Cores.CIANO}Abrindo interface segura...{Cores.RESET}")
            try:
                gerador_otp.executar()
                print(f"{Cores.VERDE}Sessão encerrada.{Cores.RESET}")
                time.sleep(1)
            except Exception as e:
                print(f"Erro ao abrir visualizador: {e}")
                input()
        
        elif escolha == '4':
            limpar_tela()
            if not confirmar_desligamento(timeout=10):
                print(f"{Cores.CINZA}Cancelado. Voltando ao menu...{Cores.RESET}")
                time.sleep(1); continue
            try:
                # 1. Fabrica
                executar_fabricador()
                
                # 2. Unifica
                qtd_novas = unificar_contas(silencioso=True)
                
                # 3. Farma SEMPRE (Para garantir o dia das contas velhas também)
                print(f"\n{Cores.AMARELO}🔄 Rodando Auto Farm completo antes de desligar...{Cores.RESET}")
                try:
                    checkin_bot_v2.executar()
                except: pass # Se o farm der erro, desliga o PC mesmo assim
                
            except Exception as e:
                print(f"{Cores.VERMELHO}Erro no módulo Fabricador: {e}{Cores.RESET}")
                input("\nEnter...")
            finally:
                desligar_computador(segundos=30)

        elif escolha == '5':
            limpar_tela()
            if not confirmar_desligamento(timeout=10):
                print(f"{Cores.CINZA}Cancelado. Voltando ao menu...{Cores.RESET}")
                time.sleep(1); continue
            try:
                checkin_bot_v2.executar()
            except Exception as e:
                print(f"{Cores.VERMELHO}Erro no módulo Auto Farm: {e}{Cores.RESET}")
                input("\nEnter...")
            finally:
                desligar_computador(segundos=30)

        elif escolha == '6':
            limpar_tela()
            try:
                if premios_manager: premios_manager.configurar_watchlist_manual()
                else: print("Módulo de prêmios não carregado.")
            except Exception as e:
                print(f"Erro ao configurar prêmios: {e}")
                input("\nEnter...")

        elif escolha == '7':
            limpar_tela()
            try:
                if premios_manager:
                    out_path, arqs, lidas, matches = premios_manager.sync_premios_filtrados_incremental()
                    print("✅ SYNC finalizado!")
                    print(f"   Arquivos: {arqs} | Linhas: {lidas} | Matches: {matches}")
                else:
                    print("Módulo de prêmios não carregado.")
                input("\nEnter...")
            except Exception as e:
                print(f"Erro: {e}")
            input("\nEnter...")

        elif escolha == '8':
            unificar_contas()

        elif escolha == '9':
            limpar_tela()
            try:
                if uti_contas:
                    uti_contas.executar()
                else:
                    print(f"{Cores.VERMELHO}Módulo UTI não carregado.{Cores.RESET}")
                    input("\nEnter...")
            except Exception as e:
                print(f"{Cores.VERMELHO}Erro na UTI: {e}{Cores.RESET}")
                input("\nEnter...")

        elif escolha == '10':
            try:
                json_cleaner.executar()
            except Exception as e:
                print(f"Erro na limpeza: {e}")
                input("\nEnter...")

        elif escolha == '0':
            print("\nEncerrando sistema...")
            time.sleep(1)
            break

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        try:
            base = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
            with open(os.path.join(base, "crash.log"), "w", encoding="utf-8") as f:
                import traceback
                f.write(traceback.format_exc())
        except:
            pass
        raise