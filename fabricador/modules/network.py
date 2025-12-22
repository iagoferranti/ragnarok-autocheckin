import socket
import threading
import select
import base64
import random
import requests
import time
from urllib.parse import urlparse

# Tenta importar logger, senão usa print
try:
    from .logger import log_sistema, log_erro, log_info
except ImportError:
    log_sistema = print
    log_erro = print
    log_info = print

# ==========================================
# 1. OBTER DADOS
# ==========================================
def obter_proxy_novada(region="br"):
    return {
        'http': f"http://novada820MJy_TR2OXd-zone-resi-region-{region}:Q3LnwP12GGWq@e277525ffdbd64f5.xji.na.novada.pro:7777",
        'https': f"http://novada820MJy_TR2OXd-zone-resi-region-{region}:Q3LnwP12GGWq@e277525ffdbd64f5.xji.na.novada.pro:7777"
    }

# ==========================================
# 2. TESTE DE QUALIDADE (A VOLTA DO FILTRO)
# ==========================================
def testar_conexao_direta(host, port, user, password):
    """
    Testa se o proxy está vivo e rápido ANTES de abrir o navegador.
    Retorna: (Sucesso: bool, Latencia: float)
    """
    proxies = {
        "http": f"http://{user}:{password}@{host}:{port}",
        "https": f"http://{user}:{password}@{host}:{port}"
    }
    
    try:
        inicio = time.time()
        # Tenta bater no Google (leve e rápido)
        requests.get("https://www.google.com", proxies=proxies, timeout=5)
        fim = time.time()
        return True, (fim - inicio)
    except:
        return False, 0.0

# ==========================================
# 3. CLASSE DO TÚNEL
# ==========================================
class TunelAuth:
    def __init__(self, remote_host, remote_port, user, password):
        self.local_host = '127.0.0.1'
        self.local_port = random.randint(35000, 45000)
        self.remote_addr = (remote_host, int(remote_port))
        
        auth_str = f"{user}:{password}"
        self.auth_b64 = base64.b64encode(auth_str.encode()).decode()
        
        self.server = None
        self.running = False
        self.thread = None

    def start(self):
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.bind((self.local_host, self.local_port))
            self.server.listen(50)
            self.running = True
            self.thread = threading.Thread(target=self._accept_loop, daemon=True)
            self.thread.start()
            return f"{self.local_host}:{self.local_port}"
        except Exception as e:
            log_erro(f"Falha ao iniciar túnel: {e}")
            return None

    def stop(self):
        self.running = False
        if self.server:
            try: self.server.close()
            except: pass

    def _accept_loop(self):
        while self.running:
            try:
                client, addr = self.server.accept()
                threading.Thread(target=self._handle_client, args=(client,), daemon=True).start()
            except:
                if self.running: break 

    def _handle_client(self, client):
        remote = None
        try:
            request = client.recv(4096)
            if not request: client.close(); return

            remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            remote.settimeout(15)
            remote.connect(self.remote_addr)

            first_line_end = request.find(b'\r\n')
            if first_line_end != -1:
                header = f"Proxy-Authorization: Basic {self.auth_b64}\r\n"
                new_request = request[:first_line_end+2] + header.encode() + request[first_line_end+2:]
            else:
                new_request = request

            remote.sendall(new_request)

            sockets = [client, remote]
            while True:
                r, _, _ = select.select(sockets, [], [], 30)
                if not r: break
                for s in r:
                    data = s.recv(8192)
                    if not data: return
                    if s is client: remote.sendall(data)
                    else: client.sendall(data)
        except: pass 
        finally:
            try: client.close()
            except: pass
            try: 
                if remote: remote.close()
            except: pass