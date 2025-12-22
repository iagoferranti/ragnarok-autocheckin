import time
from DrissionPage.common import Keys
from .logger import log_sistema, log_sucesso, log_erro, log_aviso, Cores

def fechar_cookies(page):
    """Fecha banners de cookies."""
    try:
        if page.ele('.cookieprivacy_btn__Pqz8U', timeout=0.1): 
            page.ele('.cookieprivacy_btn__Pqz8U').click()
        elif page.ele('text=concordo.', timeout=0.1): 
            page.ele('text=concordo.').click()
        elif page.ele('#onetrust-accept-btn-handler', timeout=0.1):
            page.ele('#onetrust-accept-btn-handler').click()
    except: pass

def checar_bloqueio_ip(page):
    """Verifica bloqueios explícitos."""
    try:
        msg = page.ele("text:segurança para acesso é insuficiente", timeout=0.1) or \
              page.ele("text:tente novamente em ambiente diferente", timeout=0.1)
        
        if msg and msg.states.is_displayed:
            return True
            
        if "429" in (page.title or "").lower() or "access denied" in (page.title or "").lower():
            raise Exception("IP_BLOCKED")
    except Exception as e:
        if "IP_BLOCKED" in str(e): raise e
    return False

def is_success(page):
    """
    Retorna True APENAS se houver sinais CLAROS de sucesso.
    REGRA DE OURO: Não confie na presença do campo de e-mail.
    """
    try:
        # 1. Ícones de Sucesso (Check verde)
        if page.ele("#success", timeout=0.1) and page.ele("#success").states.is_displayed: return True
        if page.ele(".page_success__gilOx", timeout=0.1) and page.ele(".page_success__gilOx").states.is_displayed: return True
        if page.ele("#success-text", timeout=0.1) and page.ele("#success-text").states.is_displayed: return True

        # 2. Textos de Sucesso (Varredura no Widget)
        # Procura textos específicos dentro do iframe ou do container
        ele_msg = page.ele(".turnstile_turnstileMessage__grLkv p", timeout=0.1) or \
                  page.ele("#verifying-text", timeout=0.1) or \
                  page.ele("text:acesso concluída", timeout=0.1)
        
        if ele_msg and ele_msg.states.is_displayed:
            txt = (ele_msg.text or "").lower()
            if "concluída" in txt or "sucesso" in txt or "success" in txt:
                return True

    except: pass
    return False

def resolver_cloudflare(page, fator_tempo=1.0):
    """
    Estratégia: "Tudo ou Nada".
    Enquanto não tiver sucesso VISUAL, aplica cliques e teclado.
    """
    log_sistema(f"{Cores.AMARELO}🛡️  Analisando Cloudflare (Fator: {fator_tempo})...{Cores.RESET}")
    
    fechar_cookies(page)
    
    # Aguarda o widget aparecer (3s a 5s)
    time.sleep(4 * fator_tempo)
    
    start_time = time.time()
    max_wait = 60 * fator_tempo
    if max_wait < 30: max_wait = 30

    while time.time() - start_time < max_wait:
        
        # 1. VERIFICA SUCESSO (Rigoroso)
        if is_success(page):
            log_sucesso("Cloudflare Validado!")
            return True

        # 2. VERIFICA BLOQUEIO
        if checar_bloqueio_ip(page):
            log_aviso("   ❌ Falso positivo (Erro IP Visível).")
            return False

        # 3. APLICA MANOBRA (Sempre que não for sucesso)
        # log_sistema("   ⚡ Tentando resolver...")
        
        try:
            # TENTATIVA 1: CLIQUE FÍSICO
            clicou = False
            # Tenta clicar no Label (mais comum)
            if page.ele(".cb-lb", timeout=0.2):
                page.ele(".cb-lb").click()
                clicou = True
            # Tenta clicar no Checkbox
            elif page.ele("input[type='checkbox']", timeout=0.2):
                page.ele("input[type='checkbox']").click()
                clicou = True
            
            # TENTATIVA 2: TECLADO (COMBINADO)
            # Mesmo se clicou, fazemos a manobra de teclado para garantir
            # caso o clique tenha falhado ou o foco tenha mudado.
            
            # Foca no email (para ter referência)
            if page.ele("#email", timeout=0.1):
                page.ele("#email").click()
            else:
                page.ele("tag:body").click()
            
            time.sleep(0.1)
            
            # 4x Shift+Tab (Sobe do email para o checkbox)
            for _ in range(4):
                page.actions.key_down(Keys.SHIFT).key_down(Keys.TAB).key_up(Keys.TAB).key_up(Keys.SHIFT)
                time.sleep(0.05)
            
            # Aperta Espaço
            page.actions.key_down(Keys.SPACE).key_up(Keys.SPACE)
            
        except: pass
        
        # 4. ESPERA PROCESSAR
        # O Cloudflare leva uns 3-5 segundos girando. Temos que respeitar isso.
        time.sleep(5 * fator_tempo) 

    log_erro(f"Timeout Cloudflare ({max_wait}s).")
    return False

vencer_cloudflare_obrigatorio = resolver_cloudflare