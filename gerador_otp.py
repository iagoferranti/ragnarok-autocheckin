import json
import os
import sys
import time
import tkinter as tk
from tkinter import ttk, messagebox
import pyotp

# --- CONFIGURAÇÕES VISUAIS PREMIUM ---
COR_FUNDO = "#1e1e1e"       # Cinza Escuro (Fundo Janela)
COR_FUNDO_CAMPO = "#2d2d30" # Cinza Médio (Fundo Input)
COR_TEXTO = "#ffffff"       # Branco
COR_TEXTO_SEC = "#cccccc"   # Cinza Claro
COR_DESTAQUE = "#007acc"    # Azul Visual Studio
COR_BOTAO = "#3e3e42"       # Botão Padrão
COR_SUCESSO = "#28a745"     # Verde

# Arquivos onde ele vai caçar as seeds
ARQUIVOS_ALVO = ["novas_contas.json", "accounts.json"]

def get_base_path():
    """Garante que encontra o arquivo mesmo compilado ou em outra pasta"""
    if getattr(sys, 'frozen', False): return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

class OTPManager:
    def __init__(self, root):
        self.root = root
        self.root.title("Ragnarok Login Helper | Premium")
        self.root.geometry("500x550") # Altura confortável
        self.root.configure(bg=COR_FUNDO)
        self.root.resizable(False, False)

        # Variáveis de Referência aos Campos (Inicializa vazio para evitar crash)
        self.var_email_entry = None
        self.var_senha_entry = None
        
        # Dados
        self.contas = self.carregar_todas_contas()
        self.conta_atual = None
        
        # Estilos Customizados
        self.setup_styles()
        
        # Interface
        self.criar_interface()
        
        # Loop do Relógio OTP
        self.atualizar_loop()

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Combobox Dark
        self.style.map('TCombobox', fieldbackground=[('readonly', COR_FUNDO_CAMPO)])
        self.style.map('TCombobox', selectbackground=[('readonly', COR_FUNDO_CAMPO)])
        self.style.map('TCombobox', selectforeground=[('readonly', COR_TEXTO)])
        self.style.configure("TCombobox", 
                        background=COR_BOTAO, 
                        foreground=COR_TEXTO, 
                        fieldbackground=COR_FUNDO_CAMPO,
                        arrowcolor=COR_TEXTO)


    def carregar_todas_contas(self):
        contas_validas = []
        emails_processados = set()
        encontrou_algum_arquivo = False

        print(">>> Iniciando varredura de Seeds...")

        for nome_arq in ARQUIVOS_ALVO:
            caminho = os.path.join(get_base_path(), nome_arq)
            if os.path.exists(caminho):
                encontrou_algum_arquivo = True
                try:
                    with open(caminho, "r", encoding="utf-8") as f:
                        dados = json.load(f)
                        count_local = 0
                        for c in dados:
                            # CRITÉRIO: Tem que ter email E seed_otp preenchidos
                            if c.get('seed_otp') and c.get('email'):
                                if c['email'] not in emails_processados:
                                    contas_validas.append(c)
                                    emails_processados.add(c['email'])
                                    count_local += 1
                        print(f"   -> {nome_arq}: {count_local} seeds novas encontradas.")
                except Exception as e:
                    print(f"   -> Erro lendo {nome_arq}: {e}")
        
        if not encontrou_algum_arquivo:
            return []
            
        return contas_validas

    def criar_interface(self):
        # --- CABEÇALHO ---
        topo = tk.Frame(self.root, bg=COR_FUNDO)
        topo.pack(pady=20)
        tk.Label(topo, text="RAGNAROK LOGIN HELPER", font=("Segoe UI", 16, "bold"), bg=COR_FUNDO, fg=COR_DESTAQUE).pack()
        
        qtd = len(self.contas)
        subtitulo = f"{qtd} Contas Carregadas" if qtd > 0 else "Nenhuma conta com seed encontrada"
        tk.Label(topo, text=subtitulo, font=("Segoe UI", 9), bg=COR_FUNDO, fg=COR_TEXTO_SEC).pack()

        # --- SELEÇÃO ---
        frame_select = tk.Frame(self.root, bg=COR_FUNDO)
        frame_select.pack(pady=5)
        
        emails = [c['email'] for c in self.contas]
        self.combo = ttk.Combobox(frame_select, values=emails, width=55, font=("Segoe UI", 10), state="readonly")
        self.combo.pack(ipady=4)
        self.combo.bind("<<ComboboxSelected>>", self.ao_selecionar)

        # --- CAMPOS DE DADOS ---
        self.frame_dados = tk.Frame(self.root, bg=COR_FUNDO)
        self.frame_dados.pack(pady=10, padx=20, fill="x")

        # Linha 1: E-mail
        self.var_email_entry = self.criar_linha_copia(self.frame_dados, "E-mail:")
        
        # Linha 2: Senha
        self.var_senha_entry = self.criar_linha_copia(self.frame_dados, "Senha:")

        # Linha 3: OTP (Destaque)
        self.criar_linha_otp(self.frame_dados)

        # --- BARRA DE TEMPO ---
        self.progress = ttk.Progressbar(self.root, orient="horizontal", length=440, mode="determinate",
                                style="Horizontal.TProgressbar")
        self.progress.pack(pady=15)
        
        # Rodapé
        self.lbl_status = tk.Label(self.root, text="Selecione uma conta para começar", font=("Segoe UI", 9), bg=COR_FUNDO, fg="#555555")
        self.lbl_status.pack(side="bottom", pady=10)

        # --- AUTO-SELECT (SÓ AGORA, QUE TUDO EXISTE) ---
        if emails: 
            self.combo.current(0)
            self.ao_selecionar(None)

    def criar_linha_copia(self, parent, label_text):
        f = tk.Frame(parent, bg=COR_FUNDO)
        f.pack(fill="x", pady=8)
        
        tk.Label(f, text=label_text, width=8, anchor="w", font=("Segoe UI", 10, "bold"), bg=COR_FUNDO, fg=COR_TEXTO_SEC).pack(side="left")
        
        # Aqui está a correção da cor de fundo (readonlybackground)
        entry = tk.Entry(f, font=("Consolas", 11), bg=COR_FUNDO_CAMPO, fg=COR_TEXTO, 
                         relief="flat", highlightthickness=1, highlightbackground="#444",
                         readonlybackground=COR_FUNDO_CAMPO) # <--- CORREÇÃO AQUI
        
        entry.pack(side="left", fill="x", expand=True, padx=8, ipady=4)
        
        btn = tk.Button(f, text="COPIAR", font=("Segoe UI", 8, "bold"), bg=COR_BOTAO, fg="white", relief="flat", width=10, cursor="hand2")
        btn.pack(side="right")
        
        # Configura o comando do botão
        btn.config(command=lambda e=entry, b=btn: self.copiar_texto(e.get(), b))
        
        return entry 

    def criar_linha_otp(self, parent):
        f = tk.Frame(parent, bg=COR_FUNDO)
        f.pack(fill="x", pady=20)
        
        tk.Label(f, text="TOKEN:", width=8, anchor="w", font=("Segoe UI", 10, "bold"), bg=COR_FUNDO, fg=COR_DESTAQUE).pack(side="left")
        
        self.lbl_otp = tk.Label(f, text="--- ---", font=("Consolas", 28, "bold"), bg=COR_FUNDO, fg=COR_TEXTO)
        self.lbl_otp.pack(side="left", fill="x", expand=True)
        
        btn = tk.Button(f, text="COPIAR", font=("Segoe UI", 9, "bold"), bg=COR_DESTAQUE, fg="white", relief="flat", width=10, cursor="hand2")
        btn.pack(side="right", ipady=2)
        btn.config(command=lambda b=btn: self.copiar_texto(self.lbl_otp.cget("text").replace(" ", ""), b))

    def ao_selecionar(self, event):
        idx = self.combo.current()
        if idx >= 0:
            self.conta_atual = self.contas[idx]
            
            # Atualiza E-mail
            if self.var_email_entry:
                self.var_email_entry.config(state="normal")
                self.var_email_entry.delete(0, tk.END)
                self.var_email_entry.insert(0, self.conta_atual.get('email', ''))
                self.var_email_entry.config(state="readonly")
            
            # Atualiza Senha
            if self.var_senha_entry:
                self.var_senha_entry.config(state="normal")
                self.var_senha_entry.delete(0, tk.END)
                self.var_senha_entry.insert(0, self.conta_atual.get('password', ''))
                self.var_senha_entry.config(state="readonly")

            
            # Atualiza OTP
            self.atualizar_otp()
            self.lbl_status.config(text="Dados carregados.", fg="#aaaaaa")


    def atualizar_otp(self):
        if not self.conta_atual: return
        # Remove espaços da seed para evitar erro de padding
        seed = self.conta_atual.get('seed_otp', '').replace(" ", "").strip()
        
        try:
            totp = pyotp.TOTP(seed)
            codigo = totp.now()
            # Formatação bonita 123 456
            codigo_fmt = f"{codigo[:3]} {codigo[3:]}"
            self.lbl_otp.config(text=codigo_fmt, fg=COR_TEXTO)
        except Exception as e:
            print(f"Erro ao gerar OTP: {e}")
            self.lbl_otp.config(text="ERRO SEED", fg="red")

    def copiar_texto(self, texto, botao):
        if not texto or "---" in texto: return
        
        self.root.clipboard_clear()
        self.root.clipboard_append(texto)
        self.root.update()
        
        # Feedback Visual
        texto_original = botao.cget("text")
        bg_original = botao.cget("bg")
        
        botao.config(text="COPIADO!", bg=COR_SUCESSO)
        self.lbl_status.config(text=f"Copiado: {texto}", fg=COR_SUCESSO)
        
        self.root.after(1000, lambda: botao.config(text=texto_original, bg=bg_original))

    def atualizar_loop(self):
        segundos = time.time() % 30
        restante = 30 - segundos
        self.progress['value'] = (restante / 30) * 100
        
        if restante < 5: self.style.configure("Horizontal.TProgressbar", background="#d9534f")
        else: self.style.configure("Horizontal.TProgressbar", background=COR_DESTAQUE)

        if int(restante) == 30 or int(restante) == 0:
            self.atualizar_otp()
            
        self.root.after(100, self.atualizar_loop)

def executar():
    root = tk.Tk()
    w, h = 500, 520
    x = (root.winfo_screenwidth() // 2) - (w // 2)
    y = (root.winfo_screenheight() // 2) - (h // 2)
    root.geometry(f'{w}x{h}+{x}+{y}')
    
    app = OTPManager(root)
    root.mainloop()

if __name__ == "__main__":
    executar()