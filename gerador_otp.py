import json
import os
import sys
import time
import tkinter as tk
from tkinter import ttk, messagebox

# Tenta importar pyotp. Se não tiver, o programa avisa na interface depois.
try:
    import pyotp
    TEM_PYOTP = True
except ImportError:
    TEM_PYOTP = False

# === INTEGRAÇÃO COM A ARQUITETURA (O Segredo) ===
# Usamos as configs e leitor de arquivos do Fabricador
# para garantir que estamos lendo os mesmos arquivos que o resto do bot.
from fabricador import config
from fabricador.modules.files import carregar_json_seguro

# --- CONFIGURAÇÕES VISUAIS PREMIUM ---
COR_FUNDO = "#1e1e1e"       # Cinza Escuro (Fundo Janela)
COR_FUNDO_CAMPO = "#2d2d30" # Cinza Médio (Fundo Input)
COR_TEXTO = "#ffffff"       # Branco
COR_TEXTO_SEC = "#cccccc"   # Cinza Claro
COR_DESTAQUE = "#007acc"    # Azul Visual Studio
COR_BOTAO = "#3e3e42"       # Botão Padrão
COR_SUCESSO = "#28a745"     # Verde

# Caminho para o arquivo de prêmios (baseado na raiz do projeto)
PREMIOS_FILTRADOS_REL = os.path.join(config.BASE_PATH, "premios", "filtrado", "premios_filtrados.txt")

def carregar_emails_e_premios_filtrados():
    """
    Lê o arquivo de logs filtrados para mostrar histórico de prêmios na tela.
    """
    path = PREMIOS_FILTRADOS_REL
    emails = set()
    premios_map = {}
    seen_por_email = {}

    if not os.path.exists(path):
        return emails, premios_map

    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                s = line.strip()
                if not s or "]" not in s or " | " not in s: continue
                
                # Ignora linhas de cabeçalho
                if s.startswith("=====") or s.startswith("matches="): continue

                try:
                    after = s.split("] ", 1)[1]
                    email = after.split(" | ", 1)[0].strip()
                    if not email: continue

                    emails.add(email)

                    if email not in premios_map:
                        premios_map[email] = []
                        seen_por_email[email] = set()

                    # Dedup
                    if s in seen_por_email[email]: continue

                    premios_map[email].append(s)
                    seen_por_email[email].add(s)
                except: continue
    except: pass

    return emails, premios_map


class OTPManager:
    def __init__(self, root):
        self.root = root
        self.root.title("Ragnarok Login Helper | Premium")
        self.root.geometry("500x620")
        self.root.configure(bg=COR_FUNDO)
        self.root.resizable(False, False)

        if not TEM_PYOTP:
            messagebox.showwarning("Falta Dependência", "A biblioteca 'pyotp' não está instalada.\nOs códigos não serão gerados.")

        # Variáveis de Referência
        self.var_email_entry = None
        self.var_senha_entry = None
        self.var_busca = None

        # Carrega dados
        self.emails_com_premio, self.premios_map = carregar_emails_e_premios_filtrados()
        self.contas = self.carregar_todas_contas_centralizado()
        self.conta_atual = None

        self.setup_styles()
        self.criar_interface()
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


    def carregar_todas_contas_centralizado(self):
        """
        Carrega contas usando os caminhos do config.py e o leitor do fabricador.
        """
        # Se existir premios, filtrar? (Lógica mantida do original)
        usar_filtro = len(self.emails_com_premio) > 0

        contas_validas = []
        emails_processados = set()

        print(">>> Carregando contas via Módulos Centralizados...")

        # Lista de arquivos para ler (vem do config.py)
        arquivos = [config.ARQUIVO_PRINCIPAL, config.ARQUIVO_SALVAR]

        for caminho in arquivos:
            dados = carregar_json_seguro(caminho) # Usa a função robusta do fabricador
            
            count_local = 0
            for c in dados:
                email = c.get("email")
                seed = c.get("seed_otp")

                # Critério: Tem que ter Seed
                if not email or not seed or seed in ["SEM_OTP", "ERRO_SEED_NAO_APARECEU"]:
                    continue

                # Filtro de prêmios (Opcional, se a lógica pedir)
                if usar_filtro and (email not in self.emails_com_premio):
                    # Se quiser ver TODAS as contas, comente essas 2 linhas
                    # continue 
                    pass 

                # Dedup
                if email in emails_processados:
                    continue

                contas_validas.append(c)
                emails_processados.add(email)
                count_local += 1
            
            nome_arq = os.path.basename(caminho)
            print(f"   -> {nome_arq}: {count_local} seeds válidas.")

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

        # Busca
        frame_busca = tk.Frame(self.root, bg=COR_FUNDO)
        frame_busca.pack(pady=6)

        tk.Label(frame_busca, text="Pesquisar:", font=("Segoe UI", 9, "bold"),
                bg=COR_FUNDO, fg=COR_TEXTO_SEC).pack(side="left", padx=(0, 8))

        self.var_busca = tk.StringVar()
        entry_busca = tk.Entry(frame_busca, textvariable=self.var_busca, font=("Segoe UI", 10),
                               bg=COR_FUNDO_CAMPO, fg=COR_TEXTO, relief="flat",
                               highlightthickness=1, highlightbackground="#444")
        entry_busca.pack(side="left", fill="x", expand=True, ipady=4)

        btn_buscar = tk.Button(frame_busca, text="BUSCAR", font=("Segoe UI", 9, "bold"),
                            bg=COR_BOTAO, fg="white", relief="flat", width=10, cursor="hand2")
        btn_buscar.pack(side="right", padx=(8, 0))

        btn_buscar.config(command=self.aplicar_filtro_busca)
        entry_busca.bind("<KeyRelease>", lambda e: self.aplicar_filtro_busca(autoselect=True))
        entry_busca.bind("<Return>", lambda e: self.aplicar_filtro_busca(autoselect=True))
        
        emails = [c['email'] for c in self.contas]
        self.combo = ttk.Combobox(frame_select, values=emails, width=55, font=("Segoe UI", 10), state="readonly")
        self.emails_all = emails[:]
        self.combo.pack(ipady=4)
        self.combo.bind("<<ComboboxSelected>>", self.ao_selecionar)

        # --- DADOS ---
        self.frame_dados = tk.Frame(self.root, bg=COR_FUNDO)
        self.frame_dados.pack(pady=10, padx=20, fill="x")

        self.var_email_entry = self.criar_linha_copia(self.frame_dados, "E-mail:")
        self.var_senha_entry = self.criar_linha_copia(self.frame_dados, "Senha:")
        self.criar_linha_otp(self.frame_dados)

        # --- PRÊMIOS ---
        frame_premios = tk.Frame(self.root, bg=COR_FUNDO)
        frame_premios.pack(pady=8, padx=20, fill="both", expand=True)

        tk.Label(frame_premios, text="HISTÓRICO DE PRÊMIOS:", font=("Segoe UI", 9, "bold"),
                bg=COR_FUNDO, fg=COR_TEXTO_SEC).pack(anchor="w")

        self.txt_premios = tk.Text(frame_premios, height=7, font=("Consolas", 9),
                                bg=COR_FUNDO_CAMPO, fg=COR_TEXTO, relief="flat",
                                highlightthickness=1, highlightbackground="#444")
        self.txt_premios.pack(fill="both", expand=True, pady=(6, 0))
        self.txt_premios.config(state="disabled")

        # --- PROGRESSO ---
        self.progress = ttk.Progressbar(self.root, orient="horizontal", length=440, mode="determinate",
                                        style="Horizontal.TProgressbar")
        self.progress.pack(pady=15)
        
        self.lbl_status = tk.Label(self.root, text="Aguardando seleção...", font=("Segoe UI", 9), bg=COR_FUNDO, fg="#555555")
        self.lbl_status.pack(side="bottom", pady=10)

        # Auto-select
        if emails: 
            self.combo.current(0)
            self.ao_selecionar(None)

    def criar_linha_copia(self, parent, label_text):
        f = tk.Frame(parent, bg=COR_FUNDO)
        f.pack(fill="x", pady=8)
        
        tk.Label(f, text=label_text, width=8, anchor="w", font=("Segoe UI", 10, "bold"), bg=COR_FUNDO, fg=COR_TEXTO_SEC).pack(side="left")
        
        entry = tk.Entry(f, font=("Consolas", 11), bg=COR_FUNDO_CAMPO, fg=COR_TEXTO, 
                         relief="flat", highlightthickness=1, highlightbackground="#444",
                         readonlybackground=COR_FUNDO_CAMPO)
        
        entry.pack(side="left", fill="x", expand=True, padx=8, ipady=4)
        
        btn = tk.Button(f, text="COPIAR", font=("Segoe UI", 8, "bold"), bg=COR_BOTAO, fg="white", relief="flat", width=10, cursor="hand2")
        btn.pack(side="right")
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


    def aplicar_filtro_busca(self, autoselect=False):
        termo = (self.var_busca.get() or "").strip().lower()
        filtrados = [e for e in self.emails_all if termo in e.lower()] if termo else self.emails_all

        self.combo["values"] = filtrados
        if filtrados and autoselect:
            self.combo.set(filtrados[0])
            self.selecionar_por_email(filtrados[0])
        elif not filtrados:
            self.combo.set("")
            self.conta_atual = None
            self.limpar_campos()

    def limpar_campos(self):
        if self.var_email_entry:
            self.var_email_entry.config(state="normal")
            self.var_email_entry.delete(0, tk.END)
            self.var_email_entry.config(state="readonly")
        if self.var_senha_entry:
            self.var_senha_entry.config(state="normal")
            self.var_senha_entry.delete(0, tk.END)
            self.var_senha_entry.config(state="readonly")
        self.lbl_otp.config(text="--- ---", fg=COR_TEXTO)
        self.txt_premios.config(state="normal")
        self.txt_premios.delete("1.0", tk.END)
        self.txt_premios.config(state="disabled")

    def selecionar_por_email(self, email):
        for c in self.contas:
            if c.get("email") == email:
                self.combo.set(email)
                self.conta_atual = c
                self.atualizar_campos_da_conta()
                return

    def ao_selecionar(self, event):
        idx = self.combo.current()
        # Se filtrado, o indice do combo não bate com self.contas original.
        # Precisamos achar a conta pelo email selecionado.
        email_sel = self.combo.get()
        self.selecionar_por_email(email_sel)

    def atualizar_campos_da_conta(self):
        if not self.conta_atual: return

        # Email
        self.var_email_entry.config(state="normal")
        self.var_email_entry.delete(0, tk.END)
        self.var_email_entry.insert(0, self.conta_atual.get('email', ''))
        self.var_email_entry.config(state="readonly")

        # Senha
        self.var_senha_entry.config(state="normal")
        self.var_senha_entry.delete(0, tk.END)
        self.var_senha_entry.insert(0, self.conta_atual.get('password', ''))
        self.var_senha_entry.config(state="readonly")

        self.atualizar_otp()

        # Prêmios
        email = self.conta_atual.get("email", "")
        ocorrencias = (self.premios_map or {}).get(email, [])
        ultimas = ocorrencias[-10:] if ocorrencias else []
        
        self.txt_premios.config(state="normal")
        self.txt_premios.delete("1.0", tk.END)
        if not ultimas:
            self.txt_premios.insert(tk.END, "Sem registros recentes.\n")
        else:
            self.txt_premios.insert(tk.END, "Últimos registros:\n\n")
            for l in ultimas: self.txt_premios.insert(tk.END, l + "\n")
        self.txt_premios.config(state="disabled")

    def atualizar_otp(self):
        if not self.conta_atual: return
        seed = self.conta_atual.get('seed_otp', '').replace(" ", "").strip()
        
        if TEM_PYOTP:
            try:
                totp = pyotp.TOTP(seed)
                codigo = totp.now()
                self.lbl_otp.config(text=f"{codigo[:3]} {codigo[3:]}", fg=COR_TEXTO)
            except:
                self.lbl_otp.config(text="ERRO SEED", fg="red")
        else:
             self.lbl_otp.config(text="NO LIB", fg="yellow")

    def copiar_texto(self, texto, botao):
        if not texto or "---" in texto: return
        self.root.clipboard_clear()
        self.root.clipboard_append(texto)
        self.root.update()
        
        txt_orig = botao.cget("text")
        bg_orig = botao.cget("bg")
        botao.config(text="COPIADO!", bg=COR_SUCESSO)
        self.root.after(1000, lambda: botao.config(text=txt_orig, bg=bg_orig))

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
    w, h = 500, 620
    x = (root.winfo_screenwidth() // 2) - (w // 2)
    y = (root.winfo_screenheight() // 2) - (h // 2)
    root.geometry(f'{w}x{h}+{x}+{y}')
    OTPManager(root)
    root.mainloop()

if __name__ == "__main__":
    executar()