import json
import os
import sys
from datetime import datetime

# === IMPORTS CORRIGIDOS (Relativos) ===
# Sobe um nível para pegar o config
from .. import config 

# Pega o logger da mesma pasta
from .logger import log_aviso, log_erro

def carregar_json_seguro(caminho):
    """Lê um arquivo JSON e retorna uma lista, lidando com erros/arquivo inexistente."""
    if not os.path.exists(caminho): 
        return []
    try: 
        with open(caminho, "r", encoding="utf-8") as f: 
            return json.load(f)
    except: 
        return []

def salvar_json_seguro(caminho, dados):
    """Salva dados em JSON com indentação e utf-8."""
    try:
        with open(caminho, "w", encoding="utf-8") as f: 
            json.dump(dados, f, indent=4, ensure_ascii=False)
        return True
    except: 
        return False

def consolidar_conta_no_principal(email, senha, seed=None):
    """
    Adiciona ou atualiza a conta no arquivo principal (accounts.json).
    Evita duplicatas checando o e-mail.
    """
    contas = carregar_json_seguro(config.ARQUIVO_PRINCIPAL)
    
    # Se já existe, não adiciona de novo
    for c in contas:
        if c.get('email') == email: 
            return

    nova_conta = {"email": email, "password": senha}
    if seed: 
        nova_conta["seed_otp"] = seed
    
    contas.append(nova_conta)
    salvar_json_seguro(config.ARQUIVO_PRINCIPAL, contas)

def salvar_conta_backup(email, senha, seed, status="PRONTA_PARA_FARMAR"):
    """
    Salva no arquivo de sessão atual (novas_contas.json).
    Atualiza se o e-mail já estiver lá.
    """
    dados = carregar_json_seguro(config.ARQUIVO_SALVAR)
    
    # Remove entrada antiga desse email se existir
    dados = [c for c in dados if c.get('email') != email]
    
    nova = {
        "email": email, 
        "password": senha, 
        "seed_otp": seed,
        "data_criacao": datetime.now().strftime("%Y-%m-%d %H:%M"), 
        "status": status
    }
    dados.append(nova)
    salvar_json_seguro(config.ARQUIVO_SALVAR, dados)

def salvar_para_uti(email, senha_email):
    """
    Salva contas que falharam (mas existem) em um arquivo TXT para recuperação manual.
    Lida com quebras de linha para não encavalar os dados.
    """
    # Usa caminho absoluto baseado no config
    arquivo_uti = config.ARQUIVO_BLACKLIST.replace("blacklist_dominios.txt", "contas_para_uti.txt")
    
    try:
        # 1) Sanitiza
        email = (email or "").replace("\r", "").replace("\n", "").strip()
        senha_email = (senha_email or "").replace("\r", "").replace("\n", "").strip()

        if not email or not senha_email:
            log_aviso("UTI: email ou senha_email vazios. Ignorando save.")
            return

        linha = f"{email}:{senha_email}"

        # 2) Garante quebra de linha
        precisa_quebra = False
        if os.path.exists(arquivo_uti):
            try:
                with open(arquivo_uti, "rb") as f:
                    if f.tell() == 0:
                        precisa_quebra = False
                    else:
                        f.seek(-1, os.SEEK_END)
                        ultimo = f.read(1)
                        precisa_quebra = (ultimo != b"\n")
            except: pass

        with open(arquivo_uti, "a", encoding="utf-8", newline="\n") as f:
            if precisa_quebra: f.write("\n")
            f.write(linha + "\n")

        log_aviso("Conta salva na UTI para reparo posterior.")

    except Exception as e:
        log_erro(f"Falha ao salvar na UTI: {e}")

def extrair_senha_email(sessao):
    """
    Tenta achar a senha do e-mail dentro do objeto 'sessao'.
    """
    if not sessao: return None

    for attr in ("password", "senha", "pass", "pwd"):
        try:
            val = getattr(sessao, attr, None)
            if isinstance(val, str) and val.strip(): return val.strip()
        except: pass

    if isinstance(sessao, dict):
        for k in ("password", "senha", "pass", "pwd"):
            v = sessao.get(k)
            if isinstance(v, str) and v.strip(): return v.strip()

    return None

def verificar_licenca_online(tipo):
    """Stub para verificar licença. Tenta importar do master, senão bypass."""
    try: 
        # Tenta importar do master que está na raiz
        # Adiciona raiz ao path se necessário
        sys.path.append(os.path.dirname(config.BASE_PATH))
        from master import verificar_licenca_online as v
        return v(tipo)
    except: 
        return True