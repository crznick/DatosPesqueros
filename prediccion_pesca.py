import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
plt.style.use('fivethirtyeight')

from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder

from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression

from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

datos = pd.read_csv("dataset_completo_2015_2025.csv")
datos = datos.dropna(subset=["kg", "Recurso", "Año"])
datos = datos.groupby(["Año", "Recurso"])["kg"].sum().reset_index()

# ===========================================================
# FILTRO: excluir especies con muy pocos años de historia.
# Con <8 años, el modelo no tiene suficiente evidencia para
# estimar su coeficiente de forma estable (se comprobó que sin
# este filtro el R2 fuera de muestra es negativo: memorización, no ajuste real)
# ===========================================================

conteo_anios = datos.groupby("Recurso")["Año"].count()
especies_validas = conteo_anios[conteo_anios >= 8].index
datos = datos[datos["Recurso"].isin(especies_validas)]

print(f"Especies con >=8 años de historia: {len(especies_validas)} de {conteo_anios.shape[0]}")
print(f"Filas finales: {len(datos)}")

X = datos.drop(columns=["kg"])
y = datos["kg"]
cat_cols = X.select_dtypes(include=["object","string"]).columns.tolist()

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.20, random_state=123)

preprocessor = ColumnTransformer(
    transformers=[("categoricas", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat_cols)],
    remainder="passthrough",
    verbose_feature_names_out=False
).set_output(transform="pandas")

X_train_prep = preprocessor.fit_transform(X_train)
X_test_prep = preprocessor.transform(X_test)

rf = RandomForestRegressor(n_estimators=300, random_state=123, n_jobs=-1)
rf.fit(X_train_prep, y_train)

importancia = pd.DataFrame({"Variable": X_train_prep.columns, "Importancia": rf.feature_importances_}).sort_values("Importancia", ascending=False)
variables_seleccionadas = importancia[importancia["Importancia"] > 0]["Variable"].tolist()
print(f"N variables seleccionadas: {len(variables_seleccionadas)} de {len(importancia)}")

X_train_sel = X_train_prep[variables_seleccionadas]
X_test_sel = X_test_prep[variables_seleccionadas]

modelo = LinearRegression()
modelo.fit(X_train_sel, y_train)
predicciones = modelo.predict(X_test_sel)

mae = mean_absolute_error(y_test, predicciones)
mse = mean_squared_error(y_test, predicciones)
rmse = np.sqrt(mse)
r2 = r2_score(y_test, predicciones)
n = len(y_test); p = X_train_sel.shape[1]
r2_ajustado = 1 - ((1-r2)*(n-1))/(n-p-1)

print("\n==============================")
print("RESULTADOS (Año x Recurso, especies con >=8 años)")
print("==============================")
print(f"MAE           : {mae:.2f}")
print(f"MSE           : {mse:.2f}")
print(f"RMSE          : {rmse:.2f}")
print(f"R2            : {r2:.4f}")
print(f"R2 Ajustado   : {r2_ajustado:.4f}")

# ===========================================================
# PATRÓN POR ESPECIE: interacción Año x Recurso
#
# El modelo anterior usa UNA sola pendiente de Año compartida por
# las 90 especies. Para conocer cómo se comportó CADA especie por
# separado dentro de 2015-2025 (sin proyectar a futuro), se ajusta
# una regresión lineal simple de Año -> kg para cada especie de forma
# individual. Esto equivale matemáticamente a darle a cada especie su
# propia pendiente e intercepto (interacción Año x Recurso).
# ===========================================================

resultados_especie = []

for especie in datos["Recurso"].unique():
    sub = datos[datos["Recurso"] == especie].sort_values("Año")

    X_esp = sub[["Año"]].values
    y_esp = sub["kg"].values

    m = LinearRegression()
    m.fit(X_esp, y_esp)
    pred_esp = m.predict(X_esp)

    pendiente = m.coef_[0]
    r2_esp = r2_score(y_esp, pred_esp)  # en muestra: describe el ajuste histórico, no una validación a futuro

    resultados_especie.append({
        "Recurso": especie,
        "Pendiente_kg_por_anio": pendiente,
        "R2_historico": r2_esp,
        "kg_promedio": y_esp.mean(),
        "n_anios": len(sub),
    })

patron_df = pd.DataFrame(resultados_especie).sort_values("Pendiente_kg_por_anio")
patron_df.to_csv("patron_tendencia_por_especie.csv", index=False)
print(f"\nArchivo generado: patron_tendencia_por_especie.csv ({len(patron_df)} especies)")

# ===========================================================
# GRÁFICA 1: Ranking de pendientes (top 15 en disminución, top 5 en aumento)
# ===========================================================

top_disminucion = patron_df.head(15)
top_aumento = patron_df.tail(5)
ranking = pd.concat([top_disminucion, top_aumento]).sort_values("Pendiente_kg_por_anio")

colores = ["#d62728" if p < 0 else "#2ca02c" for p in ranking["Pendiente_kg_por_anio"]]

plt.figure(figsize=(11, 8))
plt.barh(ranking["Recurso"], ranking["Pendiente_kg_por_anio"], color=colores)
plt.axvline(0, color="black", linewidth=1)
plt.title("Patrón de tendencia por especie (2015-2025)\nRojo = disminución histórica | Verde = aumento histórico")
plt.xlabel("Pendiente (kg por año, dentro del período conocido)")
plt.tight_layout()
plt.savefig("ranking_tendencia_especies.png", dpi=150)
plt.show()
print("Gráfica guardada: ranking_tendencia_especies.png")

# ===========================================================
# GRÁFICA 2: Serie real + tendencia ajustada, para las 3 especies
# con mayor disminución histórica
# ===========================================================

top3_disminucion = patron_df.head(3)["Recurso"].tolist()

fig, axes = plt.subplots(1, len(top3_disminucion), figsize=(15, 4.5))
if len(top3_disminucion) == 1:
    axes = [axes]

for ax, especie in zip(axes, top3_disminucion):
    sub = datos[datos["Recurso"] == especie].sort_values("Año")
    X_esp = sub[["Año"]].values
    y_esp = sub["kg"].values

    m = LinearRegression().fit(X_esp, y_esp)
    pred_esp = m.predict(X_esp)

    ax.scatter(sub["Año"], y_esp, color="black", label="Datos reales")
    ax.plot(sub["Año"], pred_esp, color="red", linewidth=2.5, label="Tendencia histórica")
    ax.set_title(especie, fontsize=10)
    ax.set_xlabel("Año")
    ax.set_ylabel("kg")

axes[0].legend(fontsize=8)
plt.suptitle("Especies con mayor disminución histórica (2015-2025)")
plt.tight_layout()
plt.savefig("top3_especies_disminucion.png", dpi=150)
plt.show()
print("Gráfica guardada: top3_especies_disminucion.png")

print("\nTop 10 especies con mayor disminución histórica:")
print(patron_df.head(10)[["Recurso","Pendiente_kg_por_anio","R2_historico","n_anios"]])