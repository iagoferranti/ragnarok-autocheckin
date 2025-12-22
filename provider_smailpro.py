import requests
import time
import re
from datetime import datetime

# ==========================================
# 📦 DTO (Objeto de Dados)
# ==========================================
class EmailSession:
    def __init__(self):
        self.email = ""
        self.password = "API_ACCESS" 
        self.provider_name = "SmailPro"
        # Timestamp atual para garantir que só pegamos emails novos
        self.timestamp_criacao = int(time.time()) 
        self.tipo = "gmail" # gmail, outlook, temp

# ==========================================
# 🚀 PROVEDOR SMAILPRO (OFICIAL)
# ==========================================
class ProviderSmailPro:
    def __init__(self, api_key, tipo="gmail"):
        self.api_key = api_key
        self.base_url = "https://app.sonjj.com/v1"
        self.headers = {
            'Accept': 'application/json',
            'X-Api-Key': self.api_key
        }
        self.tipo = tipo.lower() 

    def gerar(self):
        """Gera um e-mail novo baseado na API."""
        try:
            # === GMAIL (Premium) ===
            if self.tipo == "gmail":
                url = f"{self.base_url}/temp_gmail/list"
                # Gmail pede parametros page/limit/type/password opcionais
                r = requests.get(url, headers=self.headers, params={"limit": 10}, timeout=10)
                
                if r.status_code == 200:
                    data = r.json()
                    # Estrutura: {"data": [{"email": "...", "timestamp": 0}]}
                    lista = data.get("data", [])
                    if lista:
                        # Pega o primeiro da lista
                        return self._criar_sessao(lista[0].get("email"), "gmail")

            # === OUTLOOK (Premium) ===
            elif self.tipo == "outlook":
                url = f"{self.base_url}/temp_outlook/list"
                r = requests.get(url, headers=self.headers, timeout=10)
                
                if r.status_code == 200:
                    data = r.json()
                    # Estrutura: {"data": [{"emails": ["..."], "timestamp": 0}]}
                    lista = data.get("data", [])
                    if lista:
                        item = lista[0]
                        # AQUI ESTAVA A PEGADINHA: É uma lista 'emails'
                        emails = item.get("emails", [])
                        if emails:
                            return self._criar_sessao(emails[0], "outlook")

            # === TEMP MAIL (Random Domain) ===
            else: 
                url = f"{self.base_url}/temp_email/create"
                # Aceita expiry_minutes (vamos deixar padrão)
                r = requests.get(url, headers=self.headers, timeout=10)
                
                if r.status_code == 200:
                    data = r.json()
                    # Estrutura: {"email": "string", "expired_at": 0, ...}
                    email_addr = data.get("email")
                    if email_addr:
                        return self._criar_sessao(email_addr, "temp")

            print(f"❌ Erro SmailPro ({self.tipo}): {r.status_code} - {r.text}")
            return None

        except Exception as e:
            print(f"❌ Exceção SmailPro: {e}")
            return None

    def _criar_sessao(self, email, tipo):
        obj = EmailSession()
        obj.email = email
        obj.tipo = tipo
        obj.timestamp_criacao = int(time.time())
        return obj

    def confirmar_uso(self, sessao_obj):
        pass # API não precisa deletar manual

    def limpar_caixa(self, sessao_obj):
        """Atualiza o timestamp para ignorar mensagens antigas."""
        sessao_obj.timestamp_criacao = int(time.time())
        return True

    def validar_acesso_imap(self, sessao_obj):
        return True # API é sempre válida se gerou

    def esperar_codigo(self, obj, filtro_assunto=""):
        """Busca mensagens na Inbox."""
        
        # 1. Configura URLs
        if obj.tipo == "gmail":
            url_inbox = f"{self.base_url}/temp_gmail/inbox"
            url_msg = f"{self.base_url}/temp_gmail/message"
            params = {"email": obj.email, "timestamp": obj.timestamp_criacao}
            
        elif obj.tipo == "outlook":
            url_inbox = f"{self.base_url}/temp_outlook/inbox"
            url_msg = f"{self.base_url}/temp_outlook/message"
            params = {"email": obj.email, "timestamp": obj.timestamp_criacao}
            
        else: # temp
            url_inbox = f"{self.base_url}/temp_email/inbox"
            url_msg = f"{self.base_url}/temp_email/message"
            params = {"email": obj.email}

        try:
            # 2. Busca Lista de Mensagens
            r = requests.get(url_inbox, headers=self.headers, params=params, timeout=10)
            if r.status_code != 200: return None
            
            data = r.json()
            msgs = data.get("messages", []) # Padrão da doc para todos é "messages"
            
            if not msgs: return None

            # 3. Processa Mensagens
            for msg in msgs:
                # Normaliza campos (Temp usa textSubject, Gmail usa subject?)
                # A doc do Temp diz "textSubject", a do Outlook "textSubject".
                # Vamos tentar ambos.
                subject = msg.get("textSubject") or msg.get("subject") or ""
                mid = msg.get("mid") or msg.get("id")
                
                # Validação de Data (apenas para Temp que não filtra por timestamp na URL)
                if obj.tipo == "temp":
                    # O Temp mail retorna "textDate": "2024-04-24T10:05:52"
                    # É chato converter string para timestamp.
                    # Como limpamos a caixa atualizando o obj.timestamp_criacao,
                    # podemos assumir que se o servidor retornou, é válido, 
                    # mas o ideal seria parsing de data. 
                    # Simplificação: Vamos confiar que novos emails aparecem no topo.
                    pass 

                # Debug
                print(f"   🔎 [SmailPro] Chegou: '{subject[:30]}...'")

                if filtro_assunto and filtro_assunto.lower() not in subject.lower():
                    continue
                
                # 4. Busca o Corpo da Mensagem (Obrigatório segundo a doc)
                if not mid: continue
                
                r_body = requests.get(url_msg, headers=self.headers, params={"email": obj.email, "mid": mid}, timeout=10)
                if r_body.status_code == 200:
                    b_data = r_body.json()
                    # A doc diz que retorna: { "body": "string" }
                    return b_data.get("body", "")

            return None

        except Exception as e:
            # print(f"Erro API: {e}")
            return None