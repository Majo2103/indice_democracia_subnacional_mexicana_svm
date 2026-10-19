#!/usr/bin/env python3
"""Descarga los informes ASF indicados en el CSV entregado junto a este script."""

from __future__ import annotations

import argparse
import csv
import re
import time
import unicodedata
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def nombre_seguro(texto: str) -> str:
    """Convierte el nombre de la entidad a minúsculas y guiones bajos ASCII."""
    texto = unicodedata.normalize("NFKD", texto)
    texto = texto.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "_", texto).strip("_")


def descargar(url: str, destino: Path, intentos: int = 3) -> None:
    temporal = destino.with_suffix(destino.suffix + ".part")
    solicitud = Request(url, headers={"User-Agent": "Mozilla/5.0 ASF-PDF-Downloader/1.0"})

    for intento in range(1, intentos + 1):
        try:
            with urlopen(solicitud, timeout=60) as respuesta, temporal.open("wb") as salida:
                primeros_bytes = respuesta.read(5)
                if primeros_bytes != b"%PDF-":
                    raise ValueError("la respuesta no comienza con la firma de un PDF")
                salida.write(primeros_bytes)
                while bloque := respuesta.read(1024 * 1024):
                    salida.write(bloque)
            temporal.replace(destino)
            return
        except (HTTPError, URLError, TimeoutError, ValueError, OSError) as error:
            temporal.unlink(missing_ok=True)
            if intento == intentos:
                raise RuntimeError(f"No se pudo descargar {url}: {error}") from error
            time.sleep(2 * intento)


def main() -> None:
    carpeta_script = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Descarga los 32 informes de recurrencia de ASF.")
    parser.add_argument(
        "--csv",
        type=Path,
        default=carpeta_script / "enlaces_asf_recurrencia_por_entidad.csv",
        help="Ruta del CSV de enlaces.",
    )
    parser.add_argument(
        "--destino",
        type=Path,
        default=carpeta_script / "pdf_asf",
        help="Carpeta donde se guardarán los PDF.",
    )
    parser.add_argument("--sobrescribir", action="store_true", help="Vuelve a descargar archivos existentes.")
    argumentos = parser.parse_args()
    argumentos.destino.mkdir(parents=True, exist_ok=True)

    exitos = 0
    errores = 0
    with argumentos.csv.open("r", encoding="utf-8-sig", newline="") as archivo:
        for fila in csv.DictReader(archivo):
            clave = fila["Clave INEGI"].strip().zfill(2)
            entidad = fila["Entidad federativa"].strip()
            url = fila["Enlace directo al PDF"].strip()
            nombre = f"{int(clave):03d}_{nombre_seguro(entidad)}_2000_2010.pdf"
            destino = argumentos.destino / nombre

            if destino.exists() and not argumentos.sobrescribir:
                print(f"OMITIDO     {nombre} (ya existe)")
                exitos += 1
                continue

            try:
                descargar(url, destino)
                print(f"DESCARGADO  {nombre}")
                exitos += 1
            except RuntimeError as error:
                print(f"ERROR       {nombre}: {error}")
                errores += 1

    print(f"\nResultado: {exitos} correctos, {errores} con error.")
    if errores:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
