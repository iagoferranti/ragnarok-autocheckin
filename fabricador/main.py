import time
import os
import random
import shutil
import requests
from urllib.parse import urlparse
from DrissionPage import ChromiumPage, ChromiumOptions

# Imports Internos
from . import config
from .core.actions import criar_conta, definir_velocidade
from .modules.network import obter_proxy_novada, TunelAuth, testar_conexao_direta
from .modules.logger import exibir_banner, log_info, log_sucesso, log_erro, log_sistema, log_aviso, Cores, barra_progresso
from .modules.browser import medir_consumo, ACUMULADO_MB

try:
    import sys
    sys.path.append(config.BASE_PATH)
    from provider_email import ProviderLista
    from provider_smailpro import ProviderSmailPro
except ImportError:
    log_erro("Arquivos de provedor não encontrados na raiz!")
    sys.exit()

def executar():
    os.system('cls' if os.name == 'nt' else 'clear')
    exibir_banner()
    
    if not config.CONF: config.carregar_user_config()
    
    # === 1. CONFIGURAÇÃO DE QUANTIDADE E LOTES ===
    try:
        qtd_str = input(f"{Cores.CIANO}Quantas contas deseja criar?: {Cores.RESET}").strip()
        qtd_alvo = int(qtd_str)
    except: qtd_alvo = 1

    # Pergunta sobre Lotes (Cool Down)
    tamanho_lote = qtd_alvo # Padrão: faz tudo direto
    tempo_descanso = 0
    
    if qtd_alvo > 5: # Só pergunta se for fazer muitas
        try:
            print(f"\n{Cores.AMARELO}📦 CONFIGURAÇÃO DE LOTES (Proteção Anti-Ban){Cores.RESET}")
            lote_input = input(f"   >> Tamanho do Lote (0 = sem pausa) [10]: ").strip()
            if lote_input and int(lote_input) > 0:
                tamanho_lote = int(lote_input)
                descanso_min = float(input(f"   >> Minutos de descanso entre lotes [2.0]: ").strip() or "2")
                tempo_descanso = int(descanso_min * 60)
        except: pass

    print(f"\n{Cores.AMARELO}Configuração de Rede:{Cores.RESET}")
    
    # === LÓGICA DO OWNER / PROXY ===
    owner = config.CONF.get("owner_email", "").lower().strip()
    
    # Só pergunta se for o Iago, caso contrário, FORÇA o proxy
    if owner == "iago.cortellini@gmail.com":
        usar_proxy = input(f"   >> Usar Proxy Rotativo (Novada)? (S/N) [Padrão: S]: ").lower() != 'n'
    else:
        usar_proxy = True
        log_sistema(f"🛡️  Modo: TÚNEL AUTH ATIVADO (Padrão de Segurança)")

    # === LÓGICA DE VELOCIDADE (TURBO) ===
    if not usar_proxy:
        log_sistema(f"{Cores.VERMELHO}🚀 Modo: CONEXÃO DIRETA (Alta Velocidade){Cores.RESET}")
        definir_velocidade(rapido=True) # Ativa o Turbo no actions.py
    else:
        log_sistema(f"🛡️  Modo: TÚNEL AUTH ATIVADO")
        definir_velocidade(rapido=False) # Velocidade normal

    # === MENU DE ESCOLHA DE EMAIL ===
    prov = None
    api_key = config.CONF.get("smailpro_key", "")
    tem_txt = os.path.exists(os.path.join(config.BASE_PATH, "emails.txt"))
    
    modo = "1"
    if api_key and tem_txt:
        print(f"\n{Cores.AMARELO}Fonte de E-mails:{Cores.RESET}\n   [1] Lista Local (emails.txt)\n   [2] SmailPro API")
        escolha = input("   >> Escolha: ").strip()
        if escolha == "2": modo = "2"
    elif api_key: modo = "2"
    
    if modo == "2":
        # Menu expandido para incluir opção Temp/Random
        print(f"\n{Cores.CIANO}Tipos SmailPro:{Cores.RESET}")
        print("   [1] Gmail (Recomendado)")
        print("   [2] Outlook")
        print("   [3] Random/Temp (Domínios aleatórios)")
        tipo = input("   >> Escolha: ").strip()
        
        t_str = "gmail"
        if tipo == "2": t_str = "outlook"
        elif tipo == "3": t_str = "temp"
        
        prov = ProviderSmailPro(api_key, tipo=t_str)
    else:
        if not tem_txt:
            log_erro("Sem emails.txt e sem API Key."); return
        prov = ProviderLista()

    blacklist_global = set()
    if os.path.exists(config.ARQUIVO_BLACKLIST):
        with open(config.ARQUIVO_BLACKLIST, "r") as f:
            for l in f: blacklist_global.add(l.strip())

    sucessos = 0

    # === LOOP PRINCIPAL ===
    for i in range(qtd_alvo):
        conta_num = i + 1
        print(f"\n{Cores.AZUL}=== CONTA {conta_num} DE {qtd_alvo} ==={Cores.RESET}")
        
        tunel_ativo = None
        proxy_local = None

        if usar_proxy:
            proxy_encontrado = False
            for _ in range(10):
                print(f"   🔍 Buscando proxy estável...")
                try:
                    dados = obter_proxy_novada(region="br")
                    u = urlparse(dados["http"])
                    ok, ping = testar_conexao_direta(u.hostname, u.port, u.username, u.password)
                    if ok:
                        print(f"   🚀 Proxy Rápido Encontrado! Latência: {ping:.2f}s")
                        tunel_ativo = TunelAuth(u.hostname, u.port, u.username, u.password)
                        proxy_local = tunel_ativo.start()
                        if proxy_local:
                            print(f"   🚇 Túnel estabilizado em: {Cores.VERDE}{proxy_local}{Cores.RESET}")
                            proxy_encontrado = True
                            break
                    time.sleep(1)
                except: pass
            
            if not proxy_encontrado:
                log_erro("Sem proxy estável. Pulando."); continue

        co = ChromiumOptions()
        temp_user_data = os.path.join(config.BASE_PATH, "temp_profile", f"p_{i}_{random.randint(1000,9999)}")
        co.set_user_data_path(temp_user_data)
        co.set_argument('--no-first-run')
        co.set_argument('--disable-ipv6') 
        co.set_argument('--ignore-certificate-errors')
        if proxy_local: co.set_argument(f'--proxy-server={proxy_local}')
        if config.CONF.get("headless"): co.headless(True)
        else: co.headless(False)

        page = None
        try:
            page = ChromiumPage(addr_or_opts=co)
            
            if usar_proxy:
                print(f"{Cores.CINZA}   🕵️‍♂️ Auditando IP final...{Cores.RESET}")
                try:
                    page.get("https://api.ipify.org?format=json", timeout=10)
                    if "ip" in page.html:
                        import json as _json
                        ip_site = _json.loads(page.ele("tag:body").text)["ip"]
                        ip_real = requests.get("https://api.ipify.org?format=json", timeout=3).json()['ip']
                        print(f"   🌍 Real: {ip_real} | 🎭 Proxy: {Cores.VERDE}{ip_site}{Cores.RESET}")
                        if ip_site == ip_real: raise Exception("VAZAMENTO DE IP")
                except Exception as e:
                    if "VAZAMENTO" in str(e): raise e

            tentativas_email = 0
            conta_feita = False
            
            while tentativas_email < 3 and not conta_feita:
                
                sessao = prov.gerar() 
                if not sessao: log_erro("Fim dos e-mails (ou erro na API)."); break
                
                if tentativas_email > 0:
                    log_sistema(f"   🔄 Tentativa {tentativas_email+1}/3 com novo e-mail...")
                
                print(f"   ✉️  Testando E-mail: {Cores.MAGENTA}{sessao.email}{Cores.RESET}")
                
                # Validação IMAP (Só para lista local)
                if hasattr(prov, 'validar_acesso_imap') and modo == "1":
                    if not prov.validar_acesso_imap(sessao):
                        log_aviso("   ❌ Login IMAP falhou. Pulando...")
                        prov.confirmar_uso(sessao)
                        continue 
                
                resultado, motivo = criar_conta(page, blacklist_global, sessao, prov)
                
                if resultado:
                    sucessos += 1
                    prov.confirmar_uso(sessao)
                    conta_feita = True
                else:
                    # Erros "soft" que permitem tentar outro email na mesma sessão do navegador
                    if motivo in ["EMAIL_BANNED", "EMAIL_EM_USO", "NO_CODE", "NO_OTP_EMAIL"]:
                        log_aviso(f"   🗑️  Falha ({motivo}). Trocando e-mail...")
                        prov.confirmar_uso(sessao)
                        try:
                            page.run_cdp('Network.clearBrowserCookies')
                            page.run_cdp('Network.clearBrowserCache')
                        except: pass
                        tentativas_email += 1
                        time.sleep(2)
                        continue
                    else:
                        # Erros "hard" (IP, Proxy, Crash) matam a tentativa
                        log_erro(f"Falha fatal ({motivo}). Pulando conta.")
                        break

        except Exception as e:
            log_erro(f"Erro na execução: {e}")
        
        finally:
            if page: 
                medir_consumo(page, "Fim")
                try: page.quit()
                except: pass
            if tunel_ativo: tunel_ativo.stop()
            try: shutil.rmtree(temp_user_data, ignore_errors=True)
            except: pass

        # === LÓGICA DE LOTES E PAUSA ===
        if conta_num < qtd_alvo:
            # Se atingiu o tamanho do lote, faz pausa longa
            if tamanho_lote > 0 and (conta_num % tamanho_lote == 0):
                lote_atual = conta_num // tamanho_lote
                print(f"\n{Cores.AMARELO}💤 LOTE {lote_atual} FINALIZADO!{Cores.RESET}")
                barra_progresso(tempo_descanso, prefixo='   Resfriando Lote', sufixo='')
                print(f"{Cores.VERDE}   ❄️  Resfriamento concluído. Voltando ao trabalho!{Cores.RESET}")
            else:
                # Delay normal entre contas
                tempo = random.randint(15, 25)
                if not usar_proxy: tempo = int(tempo / 2) # Delay menor no modo turbo
                barra_progresso(tempo, prefixo='   Próxima conta em', sufixo='s')

    print(f"\n{Cores.AZUL}=== Fim. Sucessos: {sucessos}/{qtd_alvo} ==={Cores.RESET}")
    print(f"Consumo estimado: {ACUMULADO_MB:.2f} MB")
    
    if blacklist_global:
        with open(config.ARQUIVO_BLACKLIST, "w") as f:
            for d in blacklist_global: f.write(f"{d}\n")
    
    input("\nEnter para voltar...")

if __name__ == "__main__":
    executar()