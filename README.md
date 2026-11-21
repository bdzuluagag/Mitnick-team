# Escudo Yuma 360 v2.0

Motor experimental de evaluación antifraude en Python. `prueba_escudo_yuma.py`
conserva el código suministrado, normalizando los saltos de línea a LF.
Solo requiere Python 3.9 o posterior y su biblioteca estándar.

## Ejecutar la demo

Desde CMD en Windows:

```cmd
git clone https://github.com/bdzuluagag/Mitnick-team.git
cd Mitnick-team
py demo_local.py 2000
```

Desde Terminal en macOS/Linux:

```sh
python3 demo_local.py 2000
```

La demo levanta un servidor HTTP en un puerto local libre, ejecuta el motor
original en un proceso separado y cierra el servidor al terminar. Usa datos
sintéticos de cinco escenarios: operación normal, cambio de SIM, cuenta
reciente que vacía saldo, múltiples señales de toma de cuenta y pago QR nuevo.
Las métricas son conteos de decisiones; no representan precisión con datos reales.

## Usar el sandbox original

Iniciar el sandbox externo en `http://127.0.0.1:8080` y ejecutar:

```cmd
py prueba_escudo_yuma.py 2000
```

En macOS/Linux usar `python3` en lugar de `py`. El sandbox debe implementar
`POST /v1/reiniciar`, `GET /v1/transacciones/siguiente?cantidad=N`,
`POST /v1/decisiones` y `GET /v1/metricas`. El script reinicia ese sandbox.
El servicio y sus datos originales no están incluidos. Opcionalmente, colocar
`03_Datos/eventos_app.csv` con columnas `fecha_hora`, `id_cliente`,
`tipo_evento`, `resultado`, `id_dispositivo`, ordenado cronológicamente.
Sin ese CSV, la demo carga cero eventos de sesión.

## Salida y alcance

Se muestran decisiones, razones y hashes. Cada ejecución sobrescribe
`auditoria_inmutable_sha256.jsonl` con **hasta las primeras 500 decisiones**;
el último hash impreso corresponde a todas las transacciones evaluadas.
El archivo generado se excluye de Git.

El nombre del archivo no garantiza inmutabilidad: es un archivo local editable.
Los HMAC usan una clave de demostración incluida en el código; no hay un HSM
ni una verificación real de hardware. Los sellos son hashes de datos calculados
por el motor. La latencia indicada en el encabezado original no está validada
por esta demo. Este repositorio contiene un prototipo, no una integración bancaria.
