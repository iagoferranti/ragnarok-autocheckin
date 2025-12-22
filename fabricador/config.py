import os
import sys
import json

# ==========================================
# 📂 CAMINHOS HÍBRIDOS (EXE vs PYTHON)
# ==========================================
if getattr(sys, 'frozen', False):
    BASE_PATH = os.path.dirname(sys.executable)
else:
    CAMINHO_ATUAL = os.path.dirname(os.path.abspath(__file__))
    BASE_PATH = os.path.dirname(CAMINHO_ATUAL)

# ==========================================
# 📍 DEFINIÇÃO DOS ARQUIVOS
# ==========================================
ARQUIVO_CONFIG = os.path.join(BASE_PATH, "config.json")
ARQUIVO_SALVAR = os.path.join(BASE_PATH, "novas_contas.json")
ARQUIVO_PRINCIPAL = os.path.join(BASE_PATH, "accounts.json")
ARQUIVO_BLACKLIST = os.path.join(BASE_PATH, "blacklist_dominios.txt")

# URL externa
URL_LISTA_VIP = "https://gist.githubusercontent.com/iagoferranti/2675637690215af512e1e83e1eaf5e84/raw/emails.json"

# ==========================================
# ⚙️ CONFIGURAÇÕES DE EXECUÇÃO
# ==========================================
MODO_ECONOMICO = True
TIMEOUT_PADRAO = 40

# Configurações de Rede (Novada)
NOVADA_HOST = "e277525ffdbd64f5.xji.na.novada.pro"
NOVADA_PORT = "7777"
NOVADA_PASS = "Q3LnwP12GGWq"
NOVADA_USER_BASE = "novada820MJy_TR2OXd-zone-resi-region-br"

# ==========================================
# 🔧 CARREGADOR DE CONFIGURAÇÃO DE USUÁRIO
# ==========================================
CONF = {
    "owner_email": "iago.cortellini@gmail.com", # <--- SEU EMAIL AQUI
    "licenca_email": "", 
    "headless": False, 
    "tag_email": "rag",
    "sobrenome_padrao": "Silva", 
    "telegram_token": "", 
    "telegram_chat_id": "",
    "smailpro_key": "d46e88920fe2556fc400bf27091bc2f8" 
}

def carregar_user_config():
    global CONF
    if not os.path.exists(ARQUIVO_CONFIG):
        return CONF
    
    try:
        with open(ARQUIVO_CONFIG, "r", encoding="utf-8") as f:
            user_config = json.load(f)
            CONF.update(user_config)
    except Exception as e:
        print(f"Erro ao ler config.json: {e}")
        
    return CONF

# Carrega ao importar
carregar_user_config()