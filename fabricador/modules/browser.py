import time
from DrissionPage.common import Keys

# Imports relativos
from .. import config 
from .logger import log_erro
from .utils import delay_humano

# === CORREÇÃO AQUI ===
# Mudamos de .cloudflare para .cloudflare_solver
from .cloudflare_solver import checar_bloqueio_ip 

# Variável global para controle de dados
ACUMULADO_MB = 0

def medir_consumo(page, etapa=""):
    """Soma o peso da página atual ao contador global."""
    global ACUMULADO_MB
    try:
        js_script = """
        var total = 0;
        performance.getEntries().forEach(entry => {
            if (entry.transferSize) { total += entry.transferSize; }
        });
        return total;
        """
        bytes_pagina = page.run_js(js_script)
        mb_pagina = bytes_pagina / (1024 * 1024)
        
        ACUMULADO_MB += mb_pagina
    except:
        pass

def clicar_com_seguranca(page, seletor, nome_elemento="Elemento"):
    """Tenta clicar de várias formas (nativo, JS, scroll)."""
    for tentativa in range(3):
        try:
            btn = page.wait.ele_displayed(seletor, timeout=config.TIMEOUT_PADRAO)
            if btn:
                page.scroll.to_see(btn)
                delay_humano()
                btn.click()
                return True
        except:
            try:
                btn = page.ele(seletor)
                if btn: page.run_js("arguments[0].click()", btn); return True
            except: pass
            time.sleep(1)
            
    log_erro(f"Falha ao clicar em {nome_elemento}.")
    return False

def garantir_carregamento(page, seletor_esperado, timeout=30):
    """Aguarda um elemento aparecer, checando bloqueio de IP no processo."""
    inicio = time.time()
    while time.time() - inicio < timeout:
        if page.ele(seletor_esperado) and page.ele(seletor_esperado).states.is_displayed:
            return True
        
        # Chama a função que agora mora no cloudflare_solver.py
        try:
            checar_bloqueio_ip(page)
        except Exception as e:
            # Se a função lançar erro de IP Blocked, repassa para quem chamou
            if "IP_BLOCKED" in str(e): raise e
            
        time.sleep(1)
    return False

def garantir_logout(page):
    """Limpa cookies e tenta clicar em sair se necessário."""
    try:
        page.run_cdp('Network.clearBrowserCookies')
        page.run_cdp('Network.clearBrowserCache')
        page.run_js('localStorage.clear(); sessionStorage.clear();')
    except: pass

    try:
        btn_logout = page.ele('.header_logoutBtn__6Pv_m') or \
                     page.ele('text=Sair') or \
                     page.ele('text=Logout') or \
                     page.ele('css:a[href*="logout"]')

        if btn_logout:
            try: page.run_js("arguments[0].click()", btn_logout)
            except: btn_logout.click()
            time.sleep(2)
    except: pass

def capturar_erro_email(page):
    """Verifica mensagens de erro comuns no input de email."""
    seletores = ['.mailauth_errorMessage__Umj_A', '.input_errorMsg__hM_98']
    deadline = time.time() + 4
    while time.time() < deadline:
        textos = []
        for sel in seletores:
            try:
                el = page.ele(sel, timeout=0.2)
                if el and el.states.is_displayed: textos.append((el.text or "").strip())
            except: pass
        
        try: textos.append((page.ele('tag:body').text or "").strip())
        except: pass

        low = " | ".join(textos).lower()
        if "não pode ser utilizado" in low: return "EMAIL_INVALIDO", "Email inválido."
        if "não é possível se cadastrar" in low: return "DOMINIO_BLOQUEADO", "Domínio bloqueado."
        if "segurança" in low and "insuficiente" in low: return "SEGURANCA_INSUFICIENTE", "Erro segurança."
        if "em uso" in low: return "EMAIL_EM_USO", "Email em uso."
        time.sleep(0.2)
    return None, ""