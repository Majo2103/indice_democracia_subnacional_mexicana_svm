# Scraper — Orden Jurídico Nacional

Descarga documentos (PDFs, HTMLs, DOCs) del sitio **ordenjuridico.gob.mx**
filtrando por estado y término de búsqueda.

---

## Instalación

```bash
# 1. Crear entorno virtual (recomendado)
python -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows

# 2. Instalar dependencias
pip install -r requirements.txt
```

---

## Uso

```bash
# Probar con los 3 estados definidos en config.py (ESTADOS_PRUEBA)
python scraper.py

# Correr un solo estado (14 = Jalisco)
python scraper.py --estado 14

# Buscar un solo término en un estado
python scraper.py --estado 21 --termino "codigo penal"

# Correr los 32 estados completos (tarda varias horas)
python scraper.py --todos
```

---

## Estructura de carpetas

```
ordenjuridico_scraper/
├── scraper.py          ← Script principal, corre esto
├── config.py           ← Configuración: estados, términos, carpetas
├── parser.py           ← Extrae links de las páginas de resultados
├── descargador.py      ← Hace los requests y guarda archivos
├── requirements.txt    ← Dependencias Python
│
├── descargas/
│   ├── pdfs/           ← Aquí caen los PDFs
│   ├── htmls/          ← Páginas de resultados guardadas
│   └── docs/           ← Archivos .doc/.docx
│
├── logs/               ← Log de cada ejecución (con timestamp)
└── datos/              ← inventario.csv con todos los documentos encontrados
```

---

## Salida principal: el CSV

Cada vez que corres el scraper genera un archivo `datos/inventario_FECHA.csv` con:

| columna | descripción |
|---|---|
| estado | nombre del estado |
| id_estado | número (1-32) |
| termino | término buscado |
| titulo | texto del enlace en el sitio |
| url | URL original del documento |
| tipo | pdf / doc / html |
| ruta_local | dónde quedó guardado en tu máquina |

---

## Configuración en config.py

Para ajustar qué se descarga, edita `config.py`:

- **ESTADOS_PRUEBA** — lista de IDs para prueba rápida (ej: `[14, 21]`)
- **TERMINOS_BUSQUEDA** — qué buscar (ej: `["difamacion", "ultrajes"]`)
- **PAUSA_ENTRE_REQUESTS** — segundos de espera entre requests (default: 2)

---

## Notas importantes

- El sitio es público, sin login, pero tiene velocidad limitada.
  No bajes `PAUSA_ENTRE_REQUESTS` de 1 segundo.
- Algunos documentos son `.doc` antiguos (Word 97-2003).
  Para leerlos en Python puedes usar `python-docx` o `antiword`.
- Si un PDF está escaneado (imagen), necesitarás OCR con `pytesseract`.
  La mayoría de documentos post-2005 son texto seleccionable.
- El scraper es **reanudable**: si se interrumpe, al correrlo de nuevo
  omite los archivos que ya existen en disco.
