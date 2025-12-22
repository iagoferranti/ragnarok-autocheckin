import json
import os
import shutil
import time

# Configuração dos Arquivos (Como roda via import, o caminho é relativo à execução)
FILE_ACCOUNTS = "accounts.json"
FILE_NOVAS = "novas_contas.json"

def carregar_json(caminho):
    if not os.path.exists(caminho):
        return []
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except: return []

def salvar_json(caminho, dados):
    try:
        if os.path.exists(caminho):
            shutil.copy(caminho, caminho + ".backup")
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=4, ensure_ascii=False)
        print(f"   ✅ {caminho} atualizado! ({len(dados)} contas)")
    except Exception as e:
        print(f"   ❌ Erro ao salvar {caminho}: {e}")

def limpar_accounts(dados):
    limpos = []
    removidos = 0
    for conta in dados:
        tem_email = conta.get("email")
        tem_pass = conta.get("password")
        tem_seed = conta.get("seed_otp")
        # Regra: Tem que ter os 3 campos e Seed não pode ser erro
        seed_valida = tem_seed and "ERRO" not in str(tem_seed) and "FALHA" not in str(tem_seed)
        
        if tem_email and tem_pass and seed_valida:
            limpos.append(conta)
        else:
            removidos += 1
    return limpos, removidos

def limpar_novas(dados):
    limpos = []
    removidos = 0
    for conta in dados:
        # Regra flexível: Apenas campos obrigatórios preenchidos
        if conta.get("email") and conta.get("password") and conta.get("seed_otp"):
            limpos.append(conta)
        else:
            removidos += 1
    return limpos, removidos

def executar():
    # Limpa a tela (compatível com Windows/Linux)
    os.system('cls' if os.name == 'nt' else 'clear')
    
    print("\n🧹 === FAXINA DE BANCO DE DADOS === 🧹")
    print("Este processo remove contas incompletas ou com erro de Seed.\n")

    # 1. Accounts
    print(f"📂 Processando {FILE_ACCOUNTS}...")
    accs = carregar_json(FILE_ACCOUNTS)
    if accs:
        clean_accs, rem_accs = limpar_accounts(accs)
        if rem_accs > 0:
            salvar_json(FILE_ACCOUNTS, clean_accs)
            print(f"   🗑️  Removidos: {rem_accs} lixos.")
        else:
            print("   ✨ O arquivo já está limpo.")
    else:
        print("   ⚠️ Arquivo não encontrado ou vazio.")

    print("-" * 30)

    # 2. Novas Contas
    print(f"📂 Processando {FILE_NOVAS}...")
    novas = carregar_json(FILE_NOVAS)
    if novas:
        clean_novas, rem_novas = limpar_novas(novas)
        if rem_novas > 0:
            salvar_json(FILE_NOVAS, clean_novas)
            print(f"   🗑️  Removidos: {rem_novas} lixos.")
        else:
            print("   ✨ O arquivo já está limpo.")
    else:
        print("   ⚠️ Arquivo não encontrado ou vazio.")

    print("\n✅ Faxina concluída!")
    input("Enter para voltar ao menu...")

if __name__ == "__main__":
    executar()