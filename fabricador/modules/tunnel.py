import socket
import threading
import select
import base64
import random
import time

# Tenta importar logger, senão usa print
try:
    from .logger import log_sistema, log_erro, log_info
except ImportError:
    log_sistema = print
    log_erro = print
    log_info = print

class TunelAuth:
    def __init__(self, remote_host, remote_port, user, password):
        self.local_host = '127.0.0.1'
        self.local_port = random.randint(35000, 45000) # Porta aleatória segura
        self.remote_addr = (remote_host, int(remote_port))
        
        # Prepara a autenticação em Base64 antecipadamente
        auth_str = f"{user}:{password}"
        self.auth_b64 = base64.b64encode(auth_str.encode()).decode()
        
        self.server = None
        self.running = False
        self.thread = None

    def start(self):
        """Inicia o servidor de túnel e retorna o endereço 'IP:PORTA'"""
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.bind((self.local_host, self.local_port))
            self.server.listen(50)
            self.running = True
            
            # Roda o loop de aceitar conexões em outra thread para não travar o bot
            self.thread = threading.Thread(target=self._accept_loop, daemon=True)
            self.thread.start()
            
            return f"{self.local_host}:{self.local_port}"
        except Exception as e:
            log_erro(f"Falha ao iniciar túnel: {e}")
            return None

    def stop(self):
        """Para o túnel e libera a porta"""
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
            # 1. Recebe a requisição do Chrome
            request = client.recv(4096)
            if not request:
                client.close()
                return

            # 2. Conecta na Novada
            remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            remote.settimeout(15)
            remote.connect(self.remote_addr)

            # 3. INJEÇÃO DE AUTH (Aqui a mágica acontece) 🪄
            # O Chrome manda: CONNECT google.com HTTP/1.1
            # Nós injetamos: Proxy-Authorization: Basic ...
            first_line_end = request.find(b'\r\n')
            
            if first_line_end != -1:
                header = f"Proxy-Authorization: Basic {self.auth_b64}\r\n"
                # Insere o header logo depois da primeira linha
                new_request = request[:first_line_end+2] + header.encode() + request[first_line_end+2:]
            else:
                new_request = request

            # 4. Envia para a Novada
            remote.sendall(new_request)

            # 5. Ponte de Dados (Bidirecional)
            sockets = [client, remote]
            while True:
                r, _, _ = select.select(sockets, [], [], 30)
                if not r: break
                
                for s in r:
                    data = s.recv(8192)
                    if not data: return
                    
                    if s is client:
                        remote.sendall(data)
                    else:
                        client.sendall(data)

        except Exception:
            pass 
        finally:
            try: client.close()
            except: pass
            try: 
                if remote: remote.close()
            except: pass