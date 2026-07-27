# Detección de Tendencias en Datos de Producción Pesquera de Panamá (2015-2025)

Análisis estadístico de la producción pesquera panameña mediante regresión lineal, orientado a distinguir tendencias reales de declive de la variabilidad interanual, como apoyo a la priorización regulatoria de la ARAP (Autoridad de los Recursos Acuáticos de Panamá).

## Resumen del proyecto

Este trabajo propone una metodología de dos fases sobre los registros de producción pesquera de la ARAP (2015-2025):

1. **Modelo predictivo agregado (Vía A):** un modelo de Regresión Lineal Múltiple, con selección previa de variables mediante Random Forest, que predice la captura (kg) en función del año y la especie.
2. **Modelo de tendencias por especie (Vía B):** una regresión lineal independiente para cada una de las especies con al menos 8 años de historia continua, de donde se obtiene una pendiente (kg/año) y un coeficiente de determinación (R²) propios de cada recurso.

El criterio central del estudio es que la magnitud de la pendiente por sí sola no es suficiente para priorizar la atención regulatoria sobre una especie: **solo una pendiente negativa combinada con un R² alto (≥0.45)** se considera evidencia de una tendencia de declive estadísticamente consistente. Especies con pendiente negativa pronunciada pero R² bajo (como la Anchoveta) reflejan alta volatilidad interanual más que un declive real.

## Estructura de los scripts

| Script | Función |
|---|---|
| `pesca_dataset.py` | Descarga el dataset completo (332,610+ registros) desde el servicio ArcGIS de la ARAP, en paralelo. |
| `prediccion_pesca.py` | Procesa el dataset, entrena ambos modelos (Vía A y Vía B), y genera las métricas, tablas y gráficas del análisis. |

Deben ejecutarse **en este orden**: primero `pesca_dataset.py` (genera el CSV de entrada) y luego `prediccion_pesca.py` (consume ese CSV).

## Requisitos

- Python 3.9 o superior
- Conexión a internet (solo para `pesca_dataset.py`)

Instalar dependencias:

```bash
pip install requests pandas numpy matplotlib scikit-learn
```

## Uso

### 1. Descargar el dataset

```bash
python pesca_dataset.py
```

Esto descarga el histórico completo de producción pesquera desde el servicio ArcGIS de la ARAP, usando 15 solicitudes simultáneas para acelerar la descarga (de varios minutos a unos segundos). Al finalizar, genera:

- `dataset_completo_2015_2025.csv` — dataset crudo con las columnas: `Sitio_Desembarque`, `Año`, `Fecha`, `Tipo_Emb_`, `Recurso`, `kg`, `Regional`, `Litoral`.

El script imprime en consola el total de registros descargados y un resumen de registros por año.

**Nota:** si el servicio ArcGIS cambia su URL o esquema, actualizar la constante `BASE_URL` al inicio del script.

### 2. Entrenar los modelos y generar resultados

```bash
python prediccion_pesca.py
```

Requiere que `dataset_completo_2015_2025.csv` exista en el mismo directorio (generado en el paso anterior). Este script:

1. Agrupa los datos por Año y Recurso, sumando los kg capturados.
2. Filtra las especies con menos de 8 años de historia continua.
3. Entrena el modelo agregado (Vía A: Random Forest para selección de variables + Regresión Lineal Múltiple, 80/20 train/test) e imprime sus métricas (MAE, MSE, RMSE, R², R² ajustado).
4. Ajusta una regresión independiente por especie (Vía B) y calcula su pendiente y R² histórico.
5. Genera los siguientes archivos de salida:

| Archivo | Contenido |
|---|---|
| `patron_tendencia_por_especie.csv` | Pendiente, R² histórico, kg promedio y n° de años, para cada especie analizada. |
| `ranking_tendencia_especies.png` | Gráfico de barras con las 15 especies de mayor disminución y las 5 de mayor aumento. |
| `top3_especies_disminucion.png` | Dispersión de datos reales y línea de tendencia para las 3 especies con mayor disminución histórica. |

El script también imprime en consola el top 10 de especies con mayor disminución histórica (pendiente, R² y n° de años).

## Notas metodológicas importantes

- El **R² del modelo agregado (Vía A)** refleja principalmente la capacidad del modelo de distinguir el nivel característico de captura entre especies (que varían en varios órdenes de magnitud), **no** la calidad de la tendencia temporal de cada una. Para evaluar tendencias específicas por especie, usar los resultados de la **Vía B**.
- El filtro de "mínimo 8 años de historia" fue determinado empíricamente: sin él, el R² fuera de muestra del modelo agregado resulta negativo (indicio de sobreajuste, no de un ajuste real).
- El R² histórico de la Vía B se calcula **en muestra** (no hay partición de entrenamiento/prueba, dado el bajo número de observaciones por especie) y describe qué tan consistente fue la tendencia dentro del período estudiado — no constituye una predicción a futuro.

## Fuente de datos

Autoridad de los Recursos Acuáticos de Panamá (ARAP), "Estadísticas de pesca y acuicultura", disponible públicamente a través del [Dashboard de ArcGIS](https://www.arcgis.com/apps/dashboards/9744b1faba6f4a559f69d9cdaebefffc).
