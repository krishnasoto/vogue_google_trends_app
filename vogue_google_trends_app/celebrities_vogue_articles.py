import pandas as pd
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import spacy
import time
import re

# ---------- Limpieza de fecha ----------
meses = {
    'enero':'01','febrero':'02','marzo':'03','abril':'04','mayo':'05',
    'junio':'06','julio':'07','agosto':'08','septiembre':'09',
    'octubre':'10','noviembre':'11','diciembre':'12'
}

def parse_fecha_es(fecha):
    if isinstance(fecha, str):
        fecha = fecha.lower().strip()
        m = re.match(r"(\d{1,2}) de ([a-záéíóúñ]+) de (\d{4})", fecha)
        if m:
            dia, mes, año = m.groups()
            if mes in meses:
                return pd.to_datetime(f"{año}-{meses[mes]}-{dia}")
    return pd.NaT

# -------------------
# Cargar spaCy
# -------------------
try:
    nlp = spacy.load('es_core_news_sm')
    print("Modelo spaCy (es_core_news_sm) cargado correctamente.")
except OSError:
    print("\n[ERROR SPACY] Modelo 'es_core_news_sm' no encontrado.")
    print("Ejecuta: python -m spacy download es_core_news_sm")
    nlp = None

# -------------------
# Funciones auxiliares
# -------------------
def process_string(text):
    """Limpia y normaliza el texto."""
    if not text:
        return 'N/A'
    return ' '.join(text.strip().replace('\n', ' ').split())

def extract_article_details(browser, article_url, nlp_model):
    """Extrae cuerpo y artistas del artículo en nueva pestaña."""
    original_window = browser.current_window_handle
    browser.execute_script("window.open(arguments[0]);", article_url)
    WebDriverWait(browser, 10).until(EC.number_of_windows_to_be(2))
    browser.switch_to.window(browser.window_handles[-1])

    cuerpo_completo = ""
    try:
        BODY_CONTAINER_SELECTORS = [
            '.body__container p',
            '.GalleryPageTextBlock-vtnP p',
            '[class*="GalleryPageTextBlock"] p'
        ]
        for selector in BODY_CONTAINER_SELECTORS:
            paragraphs = browser.find_elements(By.CSS_SELECTOR, selector)
            if paragraphs:
                cuerpo_completo = " ".join(p.text for p in paragraphs if p.text.strip())
                if cuerpo_completo.strip():
                    break

        cuerpo_completo = 'N/A' if not cuerpo_completo else process_string(cuerpo_completo)

        artists = []
        if nlp_model and cuerpo_completo != 'N/A':
            doc = nlp_model(cuerpo_completo)
            artists = list({ent.text for ent in doc.ents if ent.label_ == "PER" and len(ent.text.split()) > 1})

    finally:
        browser.close()
        browser.switch_to.window(original_window)

    return {'cuerpo_articulo': cuerpo_completo, 'artistas_en_articulo': artists}

# -------------------
# Función principal de scraping
# -------------------
def scrape_vogue_celebrities(num_pages=5):
    options = webdriver.ChromeOptions()
    prefs = {"profile.managed_default_content_settings.images": 2}  # Desactivar imágenes
    options.add_experimental_option("prefs", prefs)
    browser = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    browser.maximize_window()

    BASE_URL = 'https://www.vogue.es/celebrities'
    ARTICLE_SELECTOR = 'div.summary-item__content'

    all_articles = []
    processed_keys = set()

    try:
        browser.get(BASE_URL)
        # Aceptar cookies si aparecen
        try:
            cookies_btn = WebDriverWait(browser, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '#fides-accept-all-button'))
            )
            browser.execute_script("arguments[0].click();", cookies_btn)
            print("Cookies aceptadas.")
        except:
            print("No se mostró el banner de cookies.")

        # Recorrer páginas
        for page in range(1, num_pages + 1):
            page_url = f"{BASE_URL}?page={page}"
            print(f"\n--- Página {page} ---")
            browser.get(page_url)

            try:
                WebDriverWait(browser, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ARTICLE_SELECTOR))
                )
            except TimeoutException:
                print("No se encontraron artículos en esta página.")
                break

            articles = browser.find_elements(By.CSS_SELECTOR, ARTICLE_SELECTOR)
            print(f"Artículos encontrados: {len(articles)}")

            for article in articles:
                try:
                    titulo = process_string(article.find_element(By.CSS_SELECTOR, '.SummaryItemHedBase-hnYOxl').text)
                    fecha = process_string(article.find_element(By.CSS_SELECTOR, '.summary-item__publish-date').text)
                    link = article.find_element(By.TAG_NAME, 'a').get_attribute('href')
                    article_key = (titulo, fecha)
                except:
                    continue

                if article_key in processed_keys:
                    continue

                print(f" > Procesando: {titulo[:60]}")

                # Extraer detalles en nueva pestaña
                details = extract_article_details(browser, link, nlp)

                data = {
                    'titulo': titulo,
                    'fecha': fecha,
                    'link': link,
                    'cuerpo_articulo': details['cuerpo_articulo'],
                    'artistas_en_articulo': details['artistas_en_articulo']
                }

                try:
                    data['tag'] = process_string(article.find_element(By.CSS_SELECTOR, '.RubricName-gkORYq').text)
                except:
                    data['tag'] = 'N/A'

                try:
                    data['autor'] = process_string(article.find_element(By.CSS_SELECTOR, '.byline__name').text)
                except:
                    data['autor'] = 'N/A'

                all_articles.append(data)
                processed_keys.add(article_key)
                print("   > Artículo agregado.")

    finally:
        browser.quit()
        print("\nWebDriver cerrado.")

    return pd.DataFrame(all_articles)

# Limpiamos y preparamos el DataFrame final
def prepare_dataframe(df):
    df = pd.DataFrame(df)
    df['fecha'] = df['fecha'].apply(parse_fecha_es)
    #df['titulo_limpio'] = df['titulo'].str.lower().str.replace(r"[^a-záéíóúñ\s]","",regex=True)
    df = df[(df['cuerpo_articulo'] != 'N/A') & (df['cuerpo_articulo'].notna())]
    df['artistas_en_articulo'] = df['artistas_en_articulo'].apply(lambda x: x if isinstance(x,list) else [])
    df['link'] = df['link'].fillna('')
    return df



# -------------------
# EJECUCIÓN
# -------------------
if __name__ == "__main__":
    pages_to_scrape = 20  # Cambia según necesites
    df = scrape_vogue_celebrities(pages_to_scrape)
    df = prepare_dataframe(df)

    print("\nPrimeros artículos:")
    print(df.head())
    print(f"\nTotal extraído: {len(df)}")

    df.to_csv('data/vogue_celebrities_data.csv', index=False)
    df.to_json('data/vogue_celebrities_data.json', orient='records', indent=4, force_ascii=False)
