import json
import os
import datetime
from .logger import log_sistema, log_erro, log_sucesso

# Caminhos dos arquivos
BASE_DIR = os.getcwd()
ARQUIVO_UTI = os.path.join(BASE_DIR, "uti_contas.json")
ARQUIVO_SUCESSO = os.path.join(BASE_DIR, "novas_contas.json")

def carregar_json(caminho):
    """Carrega um JSON de forma segura, retornando lista vazia se der erro."""
    if not os.path.exists(caminho):
        return []
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def salvar_json(caminho, dados):
    """Salva dados no JSON."""
    try:
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        log_erro(f"Erro ao salvar JSON {caminho}: {e}")
        return False

def salvar_uti(email, senha, motivo):
    """
    Salva uma conta falha na UTI (JSON) com o motivo do erro.
    Substitui o antigo contas_para_uti.txt.
    """
    try:
        # Carrega a UTI atual
        lista_uti = carregar_json(ARQUIVO_UTI)
        
        # Verifica se já está na UTI para não duplicar
        for conta in lista_uti:
            if conta.get("email") == email:
                conta["motivo"] = motivo # Atualiza o motivo
                conta["data"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                salvar_json(ARQUIVO_UTI, lista_uti)
                return

        # Cria nova entrada
        nova_entrada = {
            "email": email,
            "password": senha,
            "motivo": motivo,
            "data": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        lista_uti.append(nova_entrada)
        salvar_json(ARQUIVO_UTI, lista_uti)
        
        log_sistema(f"   🚑 Conta enviada para UTI ({motivo})")
        
    except Exception as e:
        log_erro(f"Falha ao salvar na UTI: {e}")

def salvar_conta_nova(email, senha, seed):
    """
    Salva uma conta criada com sucesso.
    """
    try:
        lista_sucesso = carregar_json(ARQUIVO_SUCESSO)
        
        # Evita duplicatas
        for conta in lista_sucesso:
            if conta.get("email") == email:
                return

        nova = {
            "email": email,
            "password": senha,
            "seed_otp": seed,
            "data_criacao": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        lista_sucesso.append(nova)
        salvar_json(ARQUIVO_SUCESSO, lista_sucesso)
        
    except Exception as e:
        log_erro(f"Erro crítico ao salvar conta nova: {e}")

# Função para converter o TXT antigo para JSON (Opcional, para migração)
def migrar_txt_para_json():
    arquivo_txt = "contas_para_uti.txt"
    if os.path.exists(arquivo_txt):
        log_sistema("♻️  Migrando contas_para_uti.txt antigo para JSON...")
        try:
            with open(arquivo_txt, "r", encoding="utf-8") as f:
                linhas = f.readlines()
            
            for linha in linhas:
                if ":" in linha:
                    parts = linha.strip().split(":")
                    if len(parts) >= 2:
                        salvar_uti(parts[0], parts[1], "MIGRACAO_LEGADO")
            
            # Renomeia o antigo para não processar de novo
            os.rename(arquivo_txt, "contas_para_uti.txt.backup")
            log_sucesso("Migração concluída!")
        except: pass