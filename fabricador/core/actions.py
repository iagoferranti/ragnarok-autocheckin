import time
import random
import re
import pyotp 
from ..modules.logger import log_info, log_sucesso, log_erro, log_sistema, Cores
from ..modules.file_manager import salvar_uti, salvar_conta_nova
# Importação limpa do solver
from ..modules.cloudflare_solver import resolver_cloudflare

# URLs Oficiais
URL_CADASTRO = "https://member.gnjoylatam.com/pt/join"
URL_LOGIN = "https://login.gnjoylatam.com/pt"
URL_OTP = "https://member.gnjoylatam.com/pt/mypage/gotp"

# Mapa de Erros
ERROS_REGISTRO = [
    "atividade anormal", "bloqueado", "tente novamente", 
    "elevado de tentativas", "temporariamente indisponível", 
    "erro desconhecido", "contact support", "segurança para acesso é insuficiente"
]

# === CONTROLE DE VELOCIDADE ===
FATOR_VELOCIDADE = 1.0

def definir_velocidade(rapido=False):
    global FATOR_VELOCIDADE
    if rapido:
        FATOR_VELOCIDADE = 0.5
        log_sistema(f"⚡ MODO TURBO ATIVADO: Delays reduzidos em 50%")
    else:
        FATOR_VELOCIDADE = 1.0

def sleep_dinamico(segundos):
    time.sleep(segundos * FATOR_VELOCIDADE)
# ==============================

def preencher_formulario_cadastro(page, email, senha):
    """Preenche e envia o form. Retorna (Bool, Motivo)."""
    log_info("Acessando Cadastro...")
    
    try:
        page.get(URL_CADASTRO)
        
        # USANDO O SOLVER
        if not resolver_cloudflare(page, FATOR_VELOCIDADE): 
            return False, "CLOUDFLARE_FAIL"

        # 1. Preenche E-mail
        log_info("Cloudflare OK. Preenchendo e-mail...")
        ele_email = page.ele("#email") or page.ele("@name=email")
        if ele_email:
            ele_email.input(email)
            sleep_dinamico(random.uniform(0.5, 1.0))
        else:
            log_erro("Campo de e-mail não encontrado.")
            return False, "SELECTOR_ERROR"

        # 2. Clica em Verificar
        btn_verificar = page.ele("text:Enviar verificação") or \
                        page.ele("text:Enviar") or \
                        page.ele(".mailauth_inputBtn__Pnwoe")

        if btn_verificar:
            btn_verificar.click()
            log_sistema("⏳ Botão 'Enviar verificação' clicado! Checando alertas...")
            
            # === VALIDAÇÃO PÓS-CLIQUE ===
            sleep_dinamico(3) 
            
            body_txt = page.ele("tag:body").text.lower()
            
            # 1. Erro de Email Inválido / Bloqueado
            if "não pode ser utilizado" in body_txt or \
               "cannot be used" in body_txt or \
               "email inválido" in body_txt:
                log_erro(f"⛔ EMAIL BLOQUEADO PELO JOGO: {email}")
                return False, "EMAIL_BANNED"
            
            # 2. Erro de Email em Uso
            if "em uso" in body_txt or "already in use" in body_txt:
                log_erro(f"⛔ EMAIL JÁ CADASTRADO: {email}")
                return False, "EMAIL_EM_USO"

            # 3. Erro de IP/Segurança
            msg_erro = page.ele("text:segurança para acesso é insuficiente") or \
                       page.ele("text:tente novamente em ambiente diferente")
            if msg_erro and msg_erro.states.is_displayed:
                log_erro("⛔ Bloqueio de Segurança (IP) detectado APÓS clicar.")
                return False, "IP_BLOCKED"
                
        else:
            log_erro("Botão 'Enviar verificação' não encontrado.")
            return False, "BTN_MISSING"

        return True, "OK"

    except Exception as e:
        log_erro(f"Erro no form: {e}")
        return False, "SCRIPT_ERROR"

def inserir_codigo_e_finalizar(page, codigo, senha, nome, sobrenome):
    """Insere código, preenche dados e finaliza."""
    try:
        # 1. Insere Código
        input_cod = page.ele("#authnumber") or page.ele("@name=authnumber")
        if input_cod:
            input_cod.input(codigo)
            sleep_dinamico(1)
        else:
            log_erro("Campo '#authnumber' não encontrado.")
            return False
        
        # 2. Valida Código
        btn_validar = page.ele("text:Verificação concluída") or \
                      page.ele(".mailauth_inputBtn__Pnwoe")

        if btn_validar: 
            btn_validar.click()
            sleep_dinamico(3)
        else:
            log_erro("Botão 'Verificação concluída' não encontrado.")
        
        # 3. Preenche Senhas
        try:
            page.ele("#password").input(senha)
            sleep_dinamico(0.3)
            page.ele("#password2").input(senha)
            sleep_dinamico(0.3)
        except:
            log_erro("Erro ao preencher senhas.")
            return False

        # 4. Seleciona País
        try:
            btn_pais = page.ele('.page_selectBtn__XfETd')
            if btn_pais:
                btn_pais.click()
                sleep_dinamico(0.5)
                page.ele('text=Brasil').click()
                sleep_dinamico(0.5)
        except: pass

        # 5. Dados Pessoais
        try:
            page.ele("#firstname").input(nome)
            sleep_dinamico(0.3)
            page.ele("#lastname").input(sobrenome)
            sleep_dinamico(0.3)
            page.ele("#birthday").input("01/01/1995")
            sleep_dinamico(0.3)
        except:
            log_erro("Erro ao preencher dados pessoais.")
            return False

        # 6. Termos
        try:
            page.run_js("document.getElementById('terms1').click()")
            page.run_js("document.getElementById('terms2').click()")
        except:
            try: page.ele("#terms1").click()
            except: pass
            try: page.ele("#terms2").click()
            except: pass
        
        sleep_dinamico(1)

        # 7. Envia Cadastro
        btn_final = page.ele(".page_submitBtn__hk_C0") or \
                    page.ele("button[type='submit']") or \
                    page.ele("text:Criar conta")
                    
        if btn_final:
            btn_final.click()
            log_sucesso("Botão FINALIZAR clicado!")
            
            sleep_dinamico(4)
            html_lower = page.html.lower()
            for erro in ERROS_REGISTRO:
                if erro in html_lower and len(html_lower) < 20000:
                    log_erro(f"⛔ CADASTRO RECUSADO: '{erro}'")
                    return False
            
            for _ in range(15):
                if "register" not in page.url: return True
                if "sucesso" in page.html.lower(): return True
                sleep_dinamico(1)
            return False
        
        log_erro("Botão Finalizar não encontrado.")
        return False
        
    except Exception as e:
        log_erro(f"Erro ao finalizar: {e}")
        return False

def login_e_capturar_otp(page, email, senha):
    """Fluxo Login -> OTP (Sem Cloudflare na 2a etapa)"""
    try:
        # === ETAPA 1: LOGIN ===
        log_sistema("⏳ Acessando página de Login...")
        page.get(URL_LOGIN)
        
        # USANDO O SOLVER
        if not resolver_cloudflare(page, FATOR_VELOCIDADE): return None, "CF_FAIL_LOGIN"

        if page.ele("#email"):
            log_info("Preenchendo credenciais...")
            page.ele("#email").input(email)
            page.ele("#password").input(senha)
            sleep_dinamico(0.5)
            
            btn_login = page.ele(".page_loginBtn__JUYeS") or page.ele("button[type='submit']")
            if btn_login:
                btn_login.click()
            else:
                page.ele("#password").input("\n")
            
            log_sistema("⏳ Aguardando login...")
            sleep_dinamico(5)
            
            if page.ele(".header_logoutBtn__6Pv_m") or \
               page.ele("text:Logout") or \
               "gnjoylatam.com/pt" in page.url: 
                log_sucesso("Login realizado com sucesso!")
            else:
                if "incorretos" in page.html.lower() or "inválidos" in page.html.lower():
                     return None, "ACCOUNT_NOT_CREATED"
                if "login" in page.url:
                     return None, "LOGIN_STUCK"

        # === ETAPA 3: IR PARA OTP ===
        log_sistema("⏳ Acessando página de OTP...")
        page.get(URL_OTP)
        sleep_dinamico(3) 

        # === ETAPA 4: SOLICITAR OTP ===
        btn_solicitar = page.ele("text:Solicitação de serviço OTP") or \
                        page.ele(".page_otp_join_btn__KKBJq")

        if btn_solicitar: 
            btn_solicitar.click()
            log_sistema("   👉 Botão 'Solicitação de serviço OTP' clicado!")
            return True, "WAIT_EMAIL"
        
        if "gotp" in page.url and page.ele("text:OTP ativado"):
             return True, "ACTIVE"
             
        return None, "NO_BTN_OTP"

    except Exception as e:
        log_erro(f"Erro no Login/OTP: {e}")
        return None, "ERR_LOGIN"

def criar_conta(page, blacklist, sessao, provedor_email):
    """Fluxo Mestre"""
    email = sessao.email
    senha = sessao.password if sessao.password else "Ragna@123"
    senha_jogo = "Rag@" + str(random.randint(10000,99999)) + "A"
    
    log_info(f"Iniciando: {email}")

    try: page.get("https://google.com"); sleep_dinamico(1)
    except: pass

    if hasattr(provedor_email, 'limpar_caixa'):
        log_sistema("   🧹 Limpando caixa de entrada (marcando lidos)...")
        provedor_email.limpar_caixa(sessao)

    # 1. CADASTRO
    try:
        sucesso_form, motivo_form = preencher_formulario_cadastro(page, email, senha_jogo)
        if not sucesso_form: return False, motivo_form
    except Exception as e:
        if "IP_BLOCKED" in str(e): return False, "IP_BLOCKED"
        return False, "FAIL_FORM"

    # 2. CÓDIGO EMAIL (CADASTRO)
    log_sistema("   ⏳ Aguardando código Cadastro...")
    codigo = None
    
    for _ in range(30): 
        msg = provedor_email.esperar_codigo(sessao, "verificação")
        if msg:
            texto_limpo = re.sub('<[^<]+?>', '', msg) 
            codigos_encontrados = re.findall(r'\b[A-Za-z0-9]{6}\b', texto_limpo)
            palavras_proibidas = ["height", "width", "center", "border", "padding", "margin", "family", "gothic", "google", "gnjoy", "latam", "codigo", "verify", "mailto", "target", "strong", "styles", "bottom", "normal", "rights", "client", "button", "active"]
            
            for c in codigos_encontrados:
                if c.lower() not in palavras_proibidas and not c.isnumeric(): 
                     codigo = c; break
                if c.isnumeric(): 
                    codigo = c; break
            if codigo: break
        sleep_dinamico(4)
    
    if not codigo: return False, "NO_CODE"
    log_sistema(f"   🔥 Código: {codigo}")

    # 3. FINALIZA CADASTRO
    if not inserir_codigo_e_finalizar(page, codigo, senha_jogo, "Player", email[:5]):
        return False, "FAIL_SUBMIT"

    log_sistema("⏳ Verificando sucesso...")
    sleep_dinamico(5)
    if "register" in page.url: return False, "STUCK"

    # 4. LOGIN E SOLICITAÇÃO OTP
    ok, status = login_e_capturar_otp(page, email, senha_jogo)
    if not ok: 
        if status == "ACCOUNT_NOT_CREATED": return False, status
        salvar_uti(email, senha_jogo, "LOGIN_FAIL")
        return True, "UTI"

    # 5. EMAIL OTP
    log_sistema("   ⏳ Aguardando Código OTP...")
    if hasattr(provedor_email, 'limpar_caixa'):
        provedor_email.limpar_caixa(sessao)
        
    otp = None
    for _ in range(25): 
        msg = provedor_email.esperar_codigo(sessao, "autenticação") 
        if msg:
            texto_limpo = re.sub('<[^<]+?>', '', msg) 
            codigos_encontrados = re.findall(r'\b[A-Za-z0-9]{6}\b', texto_limpo)
            for c in codigos_encontrados:
                if c.isnumeric(): otp = c; break
                elif c.lower() not in ["height", "width", "border", "styles", "google"]: otp = c; break
            if otp: break
        sleep_dinamico(4)

    if not otp:
        salvar_uti(email, senha_jogo, "NO_OTP_EMAIL")
        return True, "UTI_OTP"
    
    log_sistema(f"   🔥 Código OTP: {otp}")

    # 6. INSERIR OTP E ATIVAR SEED
    try:
        # A) Insere Código Email
        page.ele("#authnumber").input(otp)
        sleep_dinamico(1)
        
        # B) Clica Verificação
        btn_otp_ok = page.ele("text:Verificação concluída") or \
                     page.ele(".mailauth_noinput_email_cert_btn__bAOxr")
        
        if btn_otp_ok:
            btn_otp_ok.click()
            sleep_dinamico(3)
            
            # C) Pega a Seed
            ele_seed = page.wait.ele_displayed('.page_otp_key__nk3eO', timeout=15)
            
            if ele_seed:
                seed_final = ele_seed.text
                log_sistema(f"   💎 Seed Encontrada: {Cores.AMARELO}{seed_final}{Cores.RESET}")
                
                try:
                    # D) Gera Token TOTP
                    totp = pyotp.TOTP(seed_final.replace(" ", ""))
                    token_gerado = totp.now()
                    log_sistema(f"   🔢 Token Gerado: {token_gerado}")
                    
                    # E) Insere Token (TARGETING CIRÚRGICO)
                    sleep_dinamico(1) 
                    
                    # Busca DIRETA pelo input correto usando o name="otpNumber"
                    ele_input_otp = page.ele('@name=otpNumber') or \
                                    page.ele('css:input[name="otpNumber"]') or \
                                    page.ele('css:input[placeholder*="código de verificação OTP"]')

                    if ele_input_otp:
                        # Limpa se tiver algo (boa prática) e insere
                        ele_input_otp.clear()
                        ele_input_otp.input(token_gerado)
                    else:
                        log_erro("Campo de input OTP não encontrado (name=otpNumber).")
                        return False, "FAIL_TOKEN_INPUT"

                    # F) Clica em CONFIRME
                    btn_confirme = page.ele("text:Confirme") or page.ele("button:has-text('Confirme')")
                    if btn_confirme:
                        btn_confirme.click()
                        sleep_dinamico(3)
                        
                        # G) Verifica Pop-up Final
                        body_fim = page.ele("tag:body").text.lower()
                        if "atividade anormal" in body_fim:
                            log_erro("⛔ Bloqueio FINAL: Atividade Anormal.")
                            salvar_uti(email, senha_jogo, "ERRO_FINAL_ATIVIDADE")
                            return True, "FAIL_FINAL" 
                        
                        # H) Clica no OK final (Pop-up de sucesso)
                        try:
                            if page.ele("text:OK"): page.ele("text:OK").click()
                            elif page.ele(".swal2-confirm"): page.ele(".swal2-confirm").click()
                        except: pass
                        
                        salvar_conta_nova(email, senha_jogo, seed_final)
                        log_sucesso(f"🚀 CONTA FINALIZADA E SEED VINCULADA!")
                        return True, "SUCCESS"

                except Exception as e:
                    log_erro(f"Erro TOTP: {e}"); return False, "FAIL_TOTP"
            else: 
                log_erro("Seed não encontrada (Elemento não apareceu).")
                return True, "NO_SEED"
        else: log_erro("Botão confirmar OTP não encontrado.")

    except Exception as e: log_erro(f"Erro final seed: {e}")
    
    salvar_uti(email, senha_jogo, "SEED_FAIL")
    return True, "UTI_SEED"