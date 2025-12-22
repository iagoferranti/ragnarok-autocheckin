import json
import os
import sys
from datetime import datetime

# === IMPORTS RELATIVOS ===
from .. import config 
from .logger import log_aviso, log_erro, log_sucesso, log_sistema

# === DEFINIÇÃO DE ARQUIVOS ===
# Garante que usamos o caminho base definido no config
ARQUIVO_UTI_JSON = os.path.join(config.BASE_PATH, "uti_contas.json")
ARQUIVO_SUCESSO = os.path.join(config.BASE_PATH, "novas_contas.json")
ARQUIVO_PRINCIPAL = config.ARQUIVO_PRINCIPAL # accounts.json

def carregar_json_seguro(caminho):
    """Lê um arquivo JSON e retorna uma lista, lidando com erros."""
    if not os.path.exists(caminho): 
        return []
    try: 
        with open(caminho, "r", encoding="utf-8") as f: 
            dados = json.load(f)
            return dados if isinstance(dados, list) else []
    except: 
        return []

def salvar_json_seguro(caminho, dados):
    """Salva dados em JSON com indentação e utf-8."""
    try:
        with open(caminho, "w", encoding="utf-8") as f: 
            json.dump(dados, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e: 
        log_erro(f"Erro ao salvar JSON {caminho}: {e}")
        return False

# ==============================================================================
# FUNÇÕES DE SALVAMENTO (MODERNIZADAS)
# ==============================================================================

def salvar_uti(email, senha, motivo):
    """
    [NOVO] Salva conta falha no uti_contas.json com motivo detalhado.
    Substitui o antigo salvar_para_uti (TXT).
    """
    try:
        lista_uti = carregar_json_seguro(ARQUIVO_UTI_JSON)
        
        # Se já existe, atualiza o motivo e data
        for conta in lista_uti:
            if conta.get("email") == email:
                conta["motivo"] = motivo
                conta["data"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                salvar_json_seguro(ARQUIVO_UTI_JSON, lista_uti)
                return

        # Cria nova entrada
        nova_entrada = {
            "email": email,
            "password": senha,
            "motivo": motivo,
            "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        lista_uti.append(nova_entrada)
        salvar_json_seguro(ARQUIVO_UTI_JSON, lista_uti)
        
        # log_sistema(f"   🚑 Conta enviada para UTI ({motivo})")
        
    except Exception as e:
        log_erro(f"Falha ao salvar na UTI: {e}")

def salvar_conta_nova(email, senha, seed, status="SUCESSO"):
    """
    [NOVO] Função central que salva em TODOS os lugares necessários.
    1. accounts.json (Banco de dados principal)
    2. novas_contas.json (Sessão atual)
    """
    data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1. Salva no Principal (Para o Check-in usar depois)
    try:
        contas = carregar_json_seguro(ARQUIVO_PRINCIPAL)
        # Evita duplicatas
        if not any(c.get('email') == email for c in contas):
            nova_conta = {
                "email": email, 
                "password": senha, 
                "seed_otp": seed,
                "data_criacao": data_atual
            }
            contas.append(nova_conta)
            salvar_json_seguro(ARQUIVO_PRINCIPAL, contas)
    except Exception as e:
        log_erro(f"Erro ao salvar no principal: {e}")

    # 2. Salva na Sessão (Backup/Relatório)
    try:
        lista_sucesso = carregar_json_seguro(ARQUIVO_SUCESSO)
        # Evita duplicatas
        if not any(c.get('email') == email for c in lista_sucesso):
            nova = {
                "email": email,
                "password": senha,
                "seed_otp": seed,
                "status": status,
                "data_criacao": data_atual
            }
            lista_sucesso.append(nova)
            salvar_json_seguro(ARQUIVO_SUCESSO, lista_sucesso)
    except Exception as e:
        log_erro(f"Erro ao salvar backup de sessão: {e}")

# Mantemos por compatibilidade (se o uti_contas.py antigo chamar)
salvar_conta_backup = salvar_conta_nova

# ==============================================================================
# HELPERS
# ==============================================================================

def extrair_senha_email(sessao):
    """Tenta achar a senha do e-mail dentro do objeto 'sessao'."""
    if not sessao: return None

    # Procura atributos
    for attr in ("password", "senha", "pass", "pwd"):
        try:
            val = getattr(sessao, attr, None)
            if isinstance(val, str) and val.strip(): return val.strip()
        except: pass

    # Procura chaves de dicionário
    if isinstance(sessao, dict):
        for k in ("password", "senha", "pass", "pwd"):
            v = sessao.get(k)
            if isinstance(v, str) and v.strip(): return v.strip()

    return None

def verificar_licenca_online(tipo):
    """Stub para verificar licença."""
    try: 
        sys.path.append(os.path.dirname(config.BASE_PATH))
        from master import verificar_licenca_online as v
        return v(tipo)
    except: 
        return True