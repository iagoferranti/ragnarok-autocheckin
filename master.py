import os
import sys
import json
import time
import requests
import subprocess
import textwrap
import ctypes
import shutil
import hashlib
import re

from datetime import datetime

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
URL_DOWNLOAD_SHA256 = "https://github.com/iagoferranti/ragnarok-autocheckin/releases/latest/download/RagnarokMasterTool.exe.sha256"

def _parse_sha256_text(text: str) -> str:
    token = (text or "").strip().split()[0]
    return re.sub(r"[^0-9a-fA-F]", "", token).lower()

def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

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

# --- IMPORTAÇÃO SEGURA ---
try:
    import fabricador
    import checkin_bot_v2
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

# --- UPDATE SYSTEM ---
def verificar_atualizacao():
    if not getattr(sys, 'frozen', False):
        return

    print(f"{Cores.CINZA}🔄 Conectando ao servidor de atualizações...{Cores.RESET}")
    try:
        r = requests.get(URL_VERSION_TXT, timeout=(5, 10))
        r.raise_for_status()
        versao_nuvem = r.text.strip()

        if _is_newer_version(VERSAO_ATUAL, versao_nuvem):
            print(f"\n{Cores.AMARELO}🚨 NOVA VERSÃO DISPONÍVEL: {versao_nuvem}{Cores.RESET}")
            if input("   >> Atualizar agora? (S/N): ").lower() == 's':
                realizar_update()
        else:
            print(f"{Cores.VERDE}✅ Sistema atualizado.{Cores.RESET}")
            time.sleep(0.5)
    except Exception as e:
        print(f"{Cores.CINZA}⚠️ Falha ao verificar update ({e}){Cores.RESET}")

def realizar_update():
    print(f"\n{Cores.CIANO}📥 Baixando atualização...{Cores.RESET}")

    base_dir = get_base_path()
    exe_atual = os.path.abspath(sys.executable)
    nome_exe = os.path.basename(exe_atual)

    temp_exe = os.path.join(base_dir, "update_temp.exe")
    temp_sha = os.path.join(base_dir, "update_temp.sha256")
    backup = os.path.join(base_dir, f"{nome_exe}.old")

    try:
        _download_to_file(URL_DOWNLOAD_EXE, temp_exe, timeout=(5, 120))
        _download_to_file(URL_DOWNLOAD_SHA256, temp_sha, timeout=(5, 30))

        if os.path.getsize(temp_exe) < 200_000:
            raise RuntimeError("Arquivo suspeito (muito pequeno)")

        with open(temp_sha, "rb") as f:
            content = f.read().decode(errors="ignore")
            esperado = _parse_sha256_text(content)


        obtido = _sha256_file(temp_exe)
        if obtido != esperado:
            raise RuntimeError("SHA256 inválido")

        bat_script = textwrap.dedent(f"""
            @echo off
            timeout /t 2 >NUL
            copy /Y "{exe_atual}" "{backup}" >NUL
            del /F /Q "{exe_atual}" >NUL
            move /Y "{temp_exe}" "{exe_atual}" >NUL
            start "" "{exe_atual}"
            del "%~f0"
        """)

        bat_path = os.path.join(base_dir, "updater.bat")
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(bat_script)

        subprocess.Popen([bat_path], shell=True, cwd=base_dir)
        sys.exit()

    except Exception as e:
        print(f"{Cores.VERMELHO}❌ Update falhou: {e}{Cores.RESET}")
        input("Enter para continuar...")


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
def unificar_contas():
    limpar_tela()
    exibir_logo()
    print(f"{Cores.AMARELO}🔗 UNIFICADOR DE CONTAS{Cores.RESET}\n")

    if not os.path.exists(ARQUIVO_NOVAS):
        print(f"⚠️  Arquivo '{ARQUIVO_NOVAS}' vazio.")
        time.sleep(2); return

    try:
        with open(ARQUIVO_NOVAS, "r", encoding="utf-8") as f: novas = json.load(f)
    except: return

    # Filtra apenas contas prontas
    validas = [c for c in novas if c.get('status') == 'PRONTA_PARA_FARMAR']
    
    if not validas:
        print("⚠️  Nenhuma conta com status 'PRONTA_PARA_FARMAR' encontrada.")
        time.sleep(2); return

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
            existentes.add(c['email'])
            count += 1

    if count > 0:
        try:
            with open(ARQUIVO_PRINCIPAL, "w", encoding="utf-8") as f:
                json.dump(principais, f, indent=4)
            
            print(f"\n{Cores.VERDE}✅ {count} Contas integradas ao banco principal!{Cores.RESET}")
            
            if input(f"\n   >> Limpar arquivo de fabricação? (S/N): ").lower() == 's':
                with open(ARQUIVO_NOVAS, "w") as f: json.dump([], f)
                print(f"   🗑️  Arquivo temporário limpo.")
        except: print("❌ Erro ao salvar.")
    else:
        print("\nℹ️  Todas as contas já estavam cadastradas.")
    
    input("\nEnter para voltar...")

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
        
        if "all" in perms or "fabricador" in perms:
            print(f"   {Cores.VERDE}[1]{Cores.RESET} 🏭 Fabricador de Contas")
            opcoes.append('1')
        else:
            print(f"   {Cores.CINZA}[1] 🔒 Fabricador (Bloqueado){Cores.RESET}")

        if "all" in perms or "checkin" in perms:
            print(f"   {Cores.VERDE}[2]{Cores.RESET} 🎰 Auto Farm (Check-in + Roleta)")
            opcoes.append('2')
        else:
            print(f"   {Cores.CINZA}[2] 🔒 Auto Farm (Bloqueado){Cores.RESET}")

        print(f"   {Cores.VERDE}[3]{Cores.RESET} 🔗 Unificar Contas Novas")
        opcoes.append('3')
        
        print(f"\n   {Cores.VERMELHO}[0]{Cores.RESET} Sair")
        opcoes.append('0')

        escolha = input("\n>> Opção: ").strip()

        if escolha not in opcoes:
            print(f"\n{Cores.VERMELHO}Opção inválida.{Cores.RESET}")
            time.sleep(1); continue

        if escolha == '1':
            limpar_tela()
            try: fabricador.executar()
            except Exception as e: 
                print(f"{Cores.VERMELHO}Erro no módulo Fabricador: {e}{Cores.RESET}")
                input()

        elif escolha == '2':
            limpar_tela()
            try: checkin_bot_v2.executar()
            except Exception as e:
                print(f"{Cores.VERMELHO}Erro no módulo Auto Farm: {e}{Cores.RESET}")
                input()

        elif escolha == '3':
            unificar_contas()

        elif escolha == '0':
            print("\nEncerrando sistema...")
            time.sleep(1)
            break

if __name__ == "__main__":
    main()