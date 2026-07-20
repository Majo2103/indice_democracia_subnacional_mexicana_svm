# ============================================================
# diagnostico.py — Corre esto ANTES del scraper para ver
# exactamente qué HTML y qué hrefs devuelve el sitio.
#
# Uso:
#   python diagnostico.py
# ============================================================

import requests
from bs4 import BeautifulSoup

URL_PRUEBA = "http://www.ordenjuridico.gob.mx/busqueda.php?frase=codigo+penal&edo=14&x=0&y=0"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "es-MX,es;q=0.9",
}

print(f"Consultando: {URL_PRUEBA}\n")

resp = requests.get(URL_PRUEBA, headers=HEADERS, timeout=30)
resp.encoding = "iso-8859-1"

print(f"Status:   {resp.status_code}")
print(f"Encoding: {resp.encoding}")
print(f"Tamaño:   {len(resp.text)} caracteres")
print()

# Guardar HTML completo para inspección manual
with open("diagnostico_output.html", "w", encoding="utf-8") as f:
    f.write(resp.text)
print("HTML completo guardado en: diagnostico_output.html")
print()

# Mostrar TODOS los hrefs encontrados
soup = BeautifulSoup(resp.text, "html.parser", from_encoding="iso-8859-1")
hrefs = [(a.get_text(strip=True), a["href"]) for a in soup.find_all("a", href=True)]

print(f"Total de <a href> encontrados: {len(hrefs)}")
print("-" * 60)
for texto, href in hrefs:
    print(f"  [{texto[:40]}]  →  {href}")

print()
print("Busca arriba cuáles hrefs apuntan a documentos.")
print("Si no ves ninguno relevante, abre diagnostico_output.html")
print("en tu navegador para ver el HTML real.")
