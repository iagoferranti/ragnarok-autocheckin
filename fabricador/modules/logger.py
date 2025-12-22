import sys
import time
from datetime import datetime

# --- STYLE CLASS ---
class Cores:
    RESET = '\033[0m'
    VERDE = '\033[92m'
    AMARELO = '\033[93m'
    VERMELHO = '\033[91m'
    CIANO = '\033[96m'
    AZUL = '\033[94m'
    MAGENTA = '\033[95m'
    CINZA = '\033[90m'
    NEGRITO = '\033[1m'
    ITALICO = '\033[3m'

# --- PREMIUM LOGGING FUNCTIONS ---
def exibir_banner():
    print(f"""{Cores.CIANO}
    ╔══════════════════════════════════════════════════════════════╗
    ║      🏭   R A G N A R O K   A C C O U N T   F A C T O R Y    ║
    ╚══════════════════════════════════════════════════════════════╝
    {Cores.RESET}""")

def log_info(msg): 
    print(f"{Cores.CIANO} ℹ️  {Cores.NEGRITO}INFO:{Cores.RESET} {msg}")

def log_sucesso(msg): 
    print(f"{Cores.VERDE} ✅ {Cores.NEGRITO}SUCESSO:{Cores.RESET} {msg}")

def log_aviso(msg): 
    print(f"{Cores.AMARELO} ⚠️  {Cores.NEGRITO}ALERTA:{Cores.RESET} {msg}")

def log_erro(msg): 
    print(f"{Cores.VERMELHO} ❌ {Cores.NEGRITO}ERRO:{Cores.RESET} {msg}")

def log_sistema(msg): 
    print(f"{Cores.CINZA}    └── {msg}{Cores.RESET}")

def log_debug(msg): 
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"{Cores.CINZA}    [DEBUG {ts}] {msg}{Cores.RESET}")

def barra_progresso(tempo_total, prefixo='', sufixo='', comprimento=30, preenchimento='█'):
    """Exibe uma barra de progresso visual no terminal."""
    start_time = time.time()
    while True:
        elapsed_time = time.time() - start_time
        if elapsed_time > tempo_total:
            break
        percent = 100 * (elapsed_time / float(tempo_total))
        filled_length = int(comprimento * elapsed_time // tempo_total)
        bar = preenchimento * filled_length + '-' * (comprimento - filled_length)
        sys.stdout.write(f'\r{prefixo} |{Cores.CIANO}{bar}{Cores.RESET}| {percent:.1f}% {sufixo}')
        sys.stdout.flush()
        time.sleep(0.1)
    sys.stdout.write('\n')