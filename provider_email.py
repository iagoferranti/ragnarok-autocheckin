import os
import sys
import imaplib
import email
from email.header import decode_header

# ==========================================
# 🛠️ UTILITÁRIOS
# ==========================================
def get_base_path():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

# ==========================================
# 📦 DTO
# ==========================================
class EmailSession:
    def __init__(self):
        self.email = ""
        self.password = "" 
        self.provider_name = ""

# ==========================================
# 🏭 CLASSE PROVEDOR LISTA
# ==========================================
class ProviderLista:
    def __init__(self):
        self.base_dir = get_base_path()
        self.arquivo_entrada = os.path.join(self.base_dir, "emails.txt")
        self.arquivo_saida = os.path.join(self.base_dir, "emails_usados.txt")

    def gerar(self):
        """Lê a primeira linha do arquivo."""
        if not os.path.exists(self.arquivo_entrada): return None
        try:
            with open(self.arquivo_entrada, "r", encoding="utf-8") as f:
                linhas = f.readlines()
        except: return None
        
        linhas_uteis = [l for l in linhas if l.strip()]
        if not linhas_uteis: return None

        conta_atual = linhas_uteis[0].strip()
        if ":" not in conta_atual:
            self.confirmar_uso_string(conta_atual)
            return self.gerar()

        partes = conta_atual.split(":", 1)
        obj = EmailSession()
        obj.email = partes[0].strip()
        obj.password = partes[1].strip()
        obj.provider_name = "ListaFile"
        return obj

    def confirmar_uso(self, sessao_obj):
        if not sessao_obj: return
        self.confirmar_uso_string(f"{sessao_obj.email}:{sessao_obj.password}")

    def confirmar_uso_string(self, linha_raw):
        try:
            with open(self.arquivo_saida, "a", encoding="utf-8") as f:
                f.write(linha_raw.strip() + "\n")
            with open(self.arquivo_entrada, "r", encoding="utf-8") as f:
                linhas = f.readlines()
            novas = [l for l in linhas if l.strip() != linha_raw.strip() and l.strip()]
            with open(self.arquivo_entrada, "w", encoding="utf-8") as f:
                f.writelines(novas)
        except: pass

    # ==========================================
    # 🕵️‍♂️ FUNÇÕES IMAP
    # ==========================================
    
    def _get_imap_config(self, email_addr):
        imap_db = {
            "outlook": ("outlook.office365.com", ["INBOX", "Junk"]),
            "hotmail": ("outlook.office365.com", ["INBOX", "Junk"]),
            "rambler": ("imap.rambler.ru", ["INBOX", "Spam"]),
            "yandex":  ("imap.yandex.com", ["INBOX", "Spam", "Junk"]),
            "gmail":   ("imap.gmail.com", ["INBOX", "[Gmail]/Spam"]),
            "mail.ru": ("imap.mail.ru", ["INBOX", "Spam"]),
        }
        domain = email_addr.split("@")[1].lower()
        for key, val in imap_db.items():
            if key in domain or key in email_addr.lower(): return val
        
        if any(x in domain for x in ["lenta.ru", "ro.ru", "autorambler", "myrambler"]):
             return imap_db["rambler"]
        if "bk.ru" in domain or "list.ru" in domain or "inbox.ru" in domain:
             return imap_db["mail.ru"]
        return ("outlook.office365.com", ["INBOX", "Junk"]) 

    def limpar_caixa(self, obj):
        """Marca todos os emails como LIDOS."""
        server, pastas = self._get_imap_config(obj.email)
        try:
            mail = imaplib.IMAP4_SSL(server, timeout=10)
            mail.login(obj.email, obj.password)
            for pasta in pastas:
                try:
                    mail.select(pasta)
                    status, messages = mail.search(None, 'UNSEEN')
                    if status == "OK":
                        for num in messages[0].split():
                            mail.store(num, '+FLAGS', '\\Seen')
                except: pass
            mail.logout()
            return True
        except: return False

    def validar_acesso_imap(self, obj):
        server, _ = self._get_imap_config(obj.email)
        try:
            mail = imaplib.IMAP4_SSL(server, timeout=10)
            mail.login(obj.email, obj.password)
            mail.logout()
            return True
        except: return False

    def esperar_codigo(self, obj, filtro_assunto=""):
        server, pastas = self._get_imap_config(obj.email)
        try:
            mail = imaplib.IMAP4_SSL(server)
            mail.login(obj.email, obj.password)
            
            for pasta in pastas:
                try:
                    status, _ = mail.select(pasta)
                    if status != "OK": continue
                except: continue

                # Busca UNSEEN (novos)
                status, messages = mail.search(None, 'UNSEEN')
                
                if status != "OK" or not messages[0]: continue 
                
                email_ids = messages[0].split()
                for num in reversed(email_ids[-3:]):
                    try:
                        _, data = mail.fetch(num, "(RFC822)")
                        msg = email.message_from_bytes(data[0][1])
                        subject = self._decodificar_header(msg["Subject"])
                        
                        print(f"   🔎 [IMAP] Chegou: '{subject[:30]}...'")

                        if filtro_assunto and filtro_assunto.lower() not in subject.lower():
                            continue

                        body = self._extrair_corpo(msg)
                        # =========================================

                        mail.logout()
                        return body 
                    except: continue
            mail.logout()
            return None
        except: return None

    def _decodificar_header(self, header_raw):
        if not header_raw: return ""
        try:
            decoded_list = decode_header(header_raw)
            texto = ""
            for bytes_part, encoding in decoded_list:
                if isinstance(bytes_part, bytes):
                    texto += bytes_part.decode(encoding or "utf-8", errors="ignore")
                else: texto += str(bytes_part)
            return texto
        except: return str(header_raw)

    def _extrair_corpo(self, msg):
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/html":
                    try: return part.get_payload(decode=True).decode(errors="ignore")
                    except: pass
        else:
            try: return msg.get_payload(decode=True).decode(errors="ignore")
            except: pass
        return body