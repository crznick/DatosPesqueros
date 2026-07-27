"""
Descarga el histórico COMPLETO (332,610+ registros) del servicio ArcGIS de forma
EFICIENTE, usando solicitudes en PARALELO en lugar de una por una.

Con ~167 páginas de 2000 registros, lanzar 15 solicitudes simultáneas reduce
el tiempo de varios minutos a unos pocos segundos.

Uso:
    pip install requests pandas
    python descargar_dataset_paralelo.py
"""

import requests
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
import math
import time

BASE_URL = "https://services5.arcgis.com/nYv9mABVJUOjGQ6L/arcgis/rest/services/3/FeatureServer/0/query"

OUT_FIELDS = "Sitio_Desembarque,Año,Fecha,Tipo_Emb_,Recurso,kg,Regional,Litoral"

PAGE_SIZE = 2000        # máximo permitido por el servicio (maxRecordCount)
MAX_WORKERS = 15        # solicitudes simultáneas (ajustable; no lo subas demasiado
                         # para no saturar el servicio ni que empiece a rechazar peticiones)


def get_total_count():
    params = {"f": "json", "where": "1=1", "returnCountOnly": "true"}
    r = requests.get(BASE_URL, params=params, timeout=60)
    r.raise_for_status()
    return r.json().get("count", 0)


def fetch_page(offset, session, retries=3):
    params = {
        "f": "json",
        "where": "1=1",
        "outFields": OUT_FIELDS,
        "returnGeometry": "false",
        "resultRecordCount": PAGE_SIZE,
        "resultOffset": offset,
        "orderByFields": "Año ASC, Fecha ASC",
    }

    for attempt in range(1, retries + 1):
        try:
            r = session.get(BASE_URL, params=params, timeout=60)
            r.raise_for_status()
            data = r.json()

            if "error" in data:
                raise RuntimeError(f"Error ArcGIS en offset {offset}: {data['error']}")

            features = data.get("features", [])
            return offset, [f["attributes"] for f in features]

        except Exception as e:
            print(f"  [offset {offset}] intento {attempt} falló: {e}")
            time.sleep(1.5 * attempt)  # backoff progresivo

    raise RuntimeError(f"No se pudo descargar el offset {offset} tras {retries} intentos")


def main():
    total = get_total_count()
    print(f"Total de registros reportados por el servicio: {total}")

    num_pages = math.ceil(total / PAGE_SIZE)
    offsets = [i * PAGE_SIZE for i in range(num_pages)]
    print(f"Se descargarán {num_pages} páginas de {PAGE_SIZE} registros, "
          f"con {MAX_WORKERS} solicitudes simultáneas...\n")

    results = {}
    session = requests.Session()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(fetch_page, off, session): off for off in offsets}

        completed = 0
        for future in as_completed(futures):
            offset, rows = future.result()
            results[offset] = rows
            completed += 1
            print(f"  Página offset={offset} descargada ({len(rows)} registros) "
                  f"[{completed}/{num_pages}]")

    # Reordenar por offset para mantener el orden original
    all_rows = []
    for off in sorted(results.keys()):
        all_rows.extend(results[off])

    print(f"\nTotal de registros descargados: {len(all_rows)} (esperados: {total})")

    df = pd.DataFrame(all_rows)

    if "Fecha" in df.columns:
        df["Fecha"] = pd.to_datetime(df["Fecha"], unit="ms", errors="coerce")

    df.to_csv("dataset_completo_2015_2025.csv", index=False, encoding="utf-8-sig")
    print("Archivo guardado como: dataset_completo_2015_2025.csv")

    if "Año" in df.columns:
        print("\nRegistros por año:")
        print(df["Año"].value_counts().sort_index())


if __name__ == "__main__":
    main()