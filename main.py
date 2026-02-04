import time
import requests
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from webdriver_manager.chrome import ChromeDriverManager

def formatar_para_telegram(linhas):
    """
    Formata as linhas cruas em uma mensagem HTML bonita para o Telegram.
    """
    mensagem = "<b>🍽️ Cardápio RU (UFPel)</b>\n"
    mensagem += f"<i>📅 {time.strftime('%d/%m/%Y')}</i>\n\n"
    
    refeicao_atual = None
    
    # Palavras irrelevantes para filtrar
    ignorar = ["Visualizar", "Página", "Mostrando", "Cobalto", "100 gramas", "---"]

    for linha in linhas:
        texto = linha.strip()
        if not texto or any(x in texto for x in ignorar):
            continue

        # Detecta se é cabeçalho de refeição (ALMOÇO ou JANTA)
        if texto.upper() in ["ALMOÇO", "JANTA"]:
            # Adiciona quebra de linha se não for a primeira refeição
            if refeicao_atual: 
                mensagem += "\n"
            refeicao_atual = texto.upper()
            icone = "☀️" if refeicao_atual == "ALMOÇO" else "🌙"
            mensagem += f"<b>{icone} {refeicao_atual}</b>\n"
        
        # Se já temos uma refeição definida e o texto parece ser um prato
        elif refeicao_atual:
            # Remove códigos numéricos comuns no início da linha (ex: "83047 |")
            partes = texto.split("|")
            prato = partes[-1].strip() if len(partes) > 1 else texto
            
            # Formatação de lista
            mensagem += f"▪️ {prato}\n"

    mensagem += "\n<i>🤖 Enviado automaticamente pelo Bot do RU</i>"
    return mensagem

def enviar_telegram(mensagem):
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        print("Erro: Variáveis de ambiente TELEGRAM_TOKEN ou TELEGRAM_CHAT_ID não definidas.")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": mensagem,
        "parse_mode": "HTML" # HTML é mais seguro que Markdown para textos com caracteres especiais
    }
    
    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()
        print("✅ Mensagem enviada com sucesso!")
    except Exception as e:
        print(f"❌ Erro ao enviar Telegram: {e}")

def run():
    # Configurações para rodar no GitHub Actions (Headless)
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    # User-agent para evitar bloqueios simples
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 20)

    try:
        print("--- Iniciando Coleta ---")
        driver.get("https://cobalto.ufpel.edu.br/portal/cardapios/cardapioPublico")

        # Seleciona Unidade Centro
        select_element = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//select[.//option[contains(text(), 'Centro')]]")
        ))
        select = Select(select_element)
        
        # Busca a opção correta iterando (mais seguro contra mudanças de texto)
        for op in select.options:
            if "Centro" in op.text:
                select.select_by_visible_text(op.text)
                break
        
        time.sleep(4) # Espera AJAX carregar

        # Coleta a tabela
        tabela = wait.until(EC.visibility_of_element_located((By.ID, "gview_gridListaCardapios")))
        texto_bruto = tabela.text.split('\n')
        
        # Formata e Envia
        mensagem_final = formatar_para_telegram(texto_bruto)
        print("Cardápio coletado, enviando...")
        enviar_telegram(mensagem_final)

    except Exception as e:
        print(f"Erro fatal: {str(e)}")
        # Opcional: Enviar aviso de erro pro Telegram
        # enviar_telegram(f"⚠️ Falha no Bot do RU: {str(e)}")
    
    finally:
        driver.quit()

if __name__ == "__main__":
    run()
