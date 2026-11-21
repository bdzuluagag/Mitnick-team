#!/usr/bin/env python3
"""
Línea base del motor de reglas actual de Yuma Pay (organización ficticia).

Aplica las 12 reglas del archivo reglas_vigentes.csv sobre transacciones.csv
e imprime los indicadores que el reto busca superar.

Uso:
    python linea_base.py                 # lee transacciones.csv de esta carpeta
    python linea_base.py ruta/al/archivo.csv

Requiere: pandas
"""
import sys
from pathlib import Path

import pandas as pd

SALIDAS = {"transferencia_inmediata", "retiro_corresponsal", "retiro_cajero"}
RETIROS = {"retiro_corresponsal", "retiro_cajero"}

SEVERIDAD = {
    "R001": "media", "R002": "alta", "R003": "media", "R004": "media",
    "R005": "alta", "R006": "alta", "R007": "alta", "R008": "media",
    "R009": "baja", "R010": "media", "R011": "baja", "R012": "media",
}
ORDEN = {"baja": 0, "media": 1, "alta": 2}


def agregar_variables(tx: pd.DataFrame) -> pd.DataFrame:
    """Calcula hora, número de salidas en 60 minutos y acumulado diario por cliente."""
    tx = tx.sort_values(["fecha_hora", "id_transaccion"]).reset_index(drop=True)
    tx["fecha_hora"] = pd.to_datetime(tx["fecha_hora"])
    tx["hora"] = tx["fecha_hora"].dt.hour
    tx["es_salida"] = tx["tipo_operacion"].isin(SALIDAS)

    # Salidas del mismo cliente en los 60 minutos anteriores (incluye la actual)
    tx["n_salidas_60min"] = 0
    sal = tx[tx["es_salida"]]
    conteo = (
        sal.set_index("fecha_hora")
        .groupby("id_cliente")["monto_cop"]
        .rolling("60min")
        .count()
    )
    # El rolling agrupado devuelve los valores ordenados por cliente y luego por tiempo;
    # se reasignan a las filas originales con ese mismo orden.
    orden = sal.sort_values("id_cliente", kind="stable").index
    tx.loc[orden, "n_salidas_60min"] = conteo.values.astype(int)

    # Monto acumulado de salidas del cliente en el día calendario (incluye la actual)
    tx["dia"] = tx["fecha_hora"].dt.date
    tx["acumulado_dia_cop"] = 0
    acum = sal.groupby(["id_cliente", sal["fecha_hora"].dt.date])["monto_cop"].cumsum()
    tx.loc[sal.index, "acumulado_dia_cop"] = acum
    return tx


def aplicar_reglas(tx: pd.DataFrame) -> pd.DataFrame:
    """Devuelve un DataFrame booleano con una columna por regla."""
    m = tx["monto_cop"]
    transf = tx["tipo_operacion"] == "transferencia_inmediata"
    retiro = tx["tipo_operacion"].isin(RETIROS)
    salida = tx["es_salida"]
    r = pd.DataFrame(index=tx.index)
    r["R001"] = transf & (m >= 1_000_000)
    r["R002"] = salida & (tx["dispositivo_nuevo"] == 1) & (m >= 150_000)
    r["R003"] = salida & (tx["hora"] <= 4) & (m >= 150_000)
    r["R004"] = salida & (tx["n_salidas_60min"] >= 4)
    r["R005"] = transf & (tx["destino_nuevo"] == 1) & (m >= 0.9 * tx["saldo_antes_cop"]) & (m >= 100_000)
    r["R006"] = transf & (tx["cambio_clave_24h"] == 1) & (m >= 200_000)
    r["R007"] = salida & (tx["cambio_sim_48h"] == 1) & (m >= 200_000)
    r["R008"] = retiro & (tx["antiguedad_cuenta_dias"] < 15) & (m >= 300_000)
    r["R009"] = salida & (tx["ip_departamento_distinto"] == 1) & (m >= 250_000)
    r["R010"] = salida & (tx["acumulado_dia_cop"] >= 1_500_000)
    r["R011"] = (tx["tipo_operacion"] == "pago_qr") & (m >= 200_000)
    r["R012"] = retiro & (m >= 600_000)
    return r


def evaluar(tx: pd.DataFrame):
    tx = agregar_variables(tx)
    reglas = aplicar_reglas(tx)
    tx["alertada"] = reglas.any(axis=1)
    tx["reglas_activadas"] = reglas.apply(lambda f: "|".join(f.index[f.values]), axis=1)
    return tx, reglas


def imprimir_indicadores(tx: pd.DataFrame, reglas: pd.DataFrame) -> dict:
    fraude = tx["es_fraude"] == 1
    alerta = tx["alertada"]
    vp = int((alerta & fraude).sum())
    fp = int((alerta & ~fraude).sum())
    fn = int((~alerta & fraude).sum())
    ind = {
        "transacciones": len(tx),
        "fraudes": int(fraude.sum()),
        "tasa_fraude_pct": round(100 * fraude.mean(), 2),
        "alertas": int(alerta.sum()),
        "falsos_positivos_pct": round(100 * fp / max(vp + fp, 1), 1),
        "precision_pct": round(100 * vp / max(vp + fp, 1), 1),
        "fraude_detectado_pct": round(100 * vp / max(vp + fn, 1), 1),
        "monto_fraude_cop": int(tx.loc[fraude, "monto_cop"].sum()),
        "monto_fraude_detectado_pct": round(
            100 * tx.loc[fraude & alerta, "monto_cop"].sum() / max(tx.loc[fraude, "monto_cop"].sum(), 1), 1
        ),
    }
    print("Indicadores de la línea base (motor de reglas actual)")
    print("-" * 56)
    for k, v in ind.items():
        print(f"{k:32s} {v:>20,}".replace(",", "."))
    print("\nDetección por modalidad de fraude")
    print("-" * 56)
    por_mod = tx[fraude].groupby("modalidad_fraude")["alertada"].agg(["size", "mean"])
    for mod, fila in por_mod.iterrows():
        print(f"{mod:32s} casos {int(fila['size']):>6}   detectado {100 * fila['mean']:5.1f} %")
    print("\nAlertas por regla (una transacción puede activar varias)")
    print("-" * 56)
    for regla in reglas.columns:
        n = int(reglas[regla].sum())
        aciertos = int((reglas[regla] & fraude).sum())
        print(f"{regla}  alertas {n:>6}   fraude real {aciertos:>5}   precisión {100 * aciertos / max(n, 1):5.1f} %")
    return ind


if __name__ == "__main__":
    ruta = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("transacciones.csv")
    datos = pd.read_csv(ruta)
    datos, reglas_df = evaluar(datos)
    imprimir_indicadores(datos, reglas_df)
