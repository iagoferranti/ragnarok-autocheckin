import json
import os
import shutil
from datetime import datetime

# Configuração dos Arquivos
FILE_ACCOUNTS = "accounts.json"
FILE_NOVAS = "novas_contas.json"

def carregar_json(caminho):
    if not os.path.exists(caminho):
        print(f"⚠️ Arquivo não encontrado: {caminho}")
        return []
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Erro ao ler {caminho}: {e}")
        return []

def salvar_json(caminho, dados):
    try:
        # Cria backup antes de salvar
        if os.path.exists(caminho):
            shutil.copy(caminho, caminho + ".backup")
        
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=4, ensure_ascii=False)
        print(f"✅ {caminho} salvo com {len(dados)} contas! (Backup criado em .backup)")
    except Exception as e:
        print(f"❌ Erro ao salvar {caminho}: {e}")

def limpar_accounts(dados):
    """
    Regra: Deve ter email, password e seed_otp preenchidos.
    """
    limpos = []
    removidos = 0
    
    for conta in dados:
        # Verifica se as chaves existem e se não estão vazias
        tem_email = conta.get("email")
        tem_pass = conta.get("password")
        tem_seed = conta.get("seed_otp")
        
        # Filtro: seed_otp não pode ser None, nem vazio, nem mensagem de erro
        seed_valida = tem_seed and "ERRO" not in str(tem_seed) and "FALHA" not in str(tem_seed)

        if tem_email and tem_pass and tem_seed:
            # Se quiser ser rigoroso e remover seeds de erro, descomente a linha abaixo:
            # if not seed_valida: removidos += 1; continue
            
            limpos.append(conta)
        else:
            removidos += 1
            
    print(f"📊 Accounts: {len(dados)} originais -> {len(limpos)} finais. ({removidos} removidos)")
    return limpos

def limpar_novas(dados):
    """
    Regra: email, password, seed_otp, data_criacao, status.
    Status: qualquer um, desde que tenha seed_otp.
    """
    limpos = []
    removidos = 0
    
    for conta in dados:
        keys_obrigatorias = ["email", "password", "seed_otp", "data_criacao", "status"]
        
        # Verifica se todas chaves existem
        if all(k in conta for k in keys_obrigatorias):
            # Verifica valores críticos
            if conta["email"] and conta["password"] and conta["seed_otp"]:
                limpos.append(conta)
            else:
                removidos += 1
        else:
            removidos += 1

    print(f"📊 Novas Contas: {len(dados)} originais -> {len(limpos)} finais. ({removidos} removidos)")
    return limpos

def main():
    print("🧹 INICIANDO LIMPEZA DE JSONS...\n")

    # 1. Processa Accounts.json
    raw_accounts = carregar_json(FILE_ACCOUNTS)
    if raw_accounts:
        clean_accounts = limpar_accounts(raw_accounts)
        salvar_json(FILE_ACCOUNTS, clean_accounts)
    
    print("-" * 30)

    # 2. Processa Novas_Contas.json
    raw_novas = carregar_json(FILE_NOVAS)
    if raw_novas:
        clean_novas = limpar_novas(raw_novas)
        salvar_json(FILE_NOVAS, clean_novas)

    print("\n✨ Limpeza Concluída!")
    input("Enter para sair...")

if __name__ == "__main__":
    main()