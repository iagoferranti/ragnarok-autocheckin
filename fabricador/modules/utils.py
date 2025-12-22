import re
import unicodedata
import time
import random

def gerar_senha_ragnarok():
    """Retorna a senha padrão forte para o jogo."""
    return "Ragnarok@2025"

def delay_humano(): 
    """Pausa aleatória para simular comportamento humano."""
    time.sleep(random.uniform(0.8, 1.5))

def limpar_html(texto_html): 
    """Remove todas as tags HTML de um texto."""
    if not texto_html: return ""
    return re.sub(re.compile('<.*?>'), ' ', texto_html)

def extrair_codigo_seguro(texto_bruto):
    """
    Tenta extrair o código de 6 dígitos do e-mail usando 3 táticas:
    1. Busca por cor (estilo específico do GNJOY).
    2. Regex contextual ("Código de verificação: XXXXXX").
    3. Varredura bruta ignorando headers de e-mail.
    """
    if not texto_bruto: return None
    
    # --- TÁTICA 1: SNIPER (Busca pela cor vermelha no HTML bruto) ---
    # Só funciona se o 'texto_bruto' ainda tiver as tags HTML.
    # O código do GNJOY vem estilizado com color:#da0c0c
    match_cor = re.search(r'color:#da0c0c[^>]*>\s*([A-Za-z0-9]{6})\s*<', texto_bruto)
    if match_cor:
        cod = match_cor.group(1).strip()
        return cod

    # --- PREPARAÇÃO PARA TÁTICA 2 (Texto Limpo) ---
    # Se não achou pela cor, limpa o HTML para procurar no texto
    texto = limpar_html(texto_bruto).replace('&nbsp;', ' ')
    texto = unicodedata.normalize("NFKC", texto)
    
    # Compacta espaços
    texto_body = re.sub(r"[ \t]+", " ", texto).strip()

    # --- LISTA NEGRA ATUALIZADA (Igual da UTI) ---
    BLACKLIST = {
        'abaixo','assets','height','width','style','script','border',
        'verifi','cation','segura','access','bottom','center','family',
        'follow','format','ground','header','online','public','select',
        'server','sign','simple','source','strong','target','title',
        'window','yellow','codigo','device','member','system','please',
        'active','gnjoy','latam','guide','guia','serviço','service',
        'email','styles','weight'
    }

    # --- TÁTICA 2: REGEX CONTEXTUAL ("Código de verificação: XXXXXX") ---
    m = re.search(r'c[oó]digo\s+de\s+verifica[cç][aã]o\s*[:\-]?\s*[\r\n]*\s*([A-Za-z0-9]{6})\b', texto_body, re.IGNORECASE)
    if m:
        cod = m.group(1).strip()
        if cod.lower() not in BLACKLIST:
            return cod

    # --- TÁTICA 3: VARREDURA DE PALAVRAS (Fallback) ---
    # Remove linhas de cabeçalho de email (From, To, etc) para evitar falso positivo
    linhas = [ln.strip() for ln in re.split(r"\r?\n", texto_body) if ln.strip()]
    texto_sem_headers = ""
    for ln in linhas:
        low = ln.lower()
        if not low.startswith(("message-id:", "date:", "feedback-id:", "from:", "to:", "subject:", "mime-version:", "content-")):
            texto_sem_headers += ln + "\n"

    # Procura qualquer coisa de 6 digitos alfanuméricos
    candidates = re.findall(r'\b[A-Za-z0-9]{6}\b', texto_sem_headers)
    for cand in candidates:
        if cand.lower() not in BLACKLIST:
            return cand

    return None