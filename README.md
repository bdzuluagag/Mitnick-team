# Escudo Yuma 360 v2.0

Motor experimental de evaluación antifraude en Python. `prueba_escudo_yuma.py`
usa las reglas del código suministrado. Se adaptó la búsqueda del CSV de eventos
a la carpeta del caso de estudio; se normalizaron los saltos de línea a LF.
Solo requiere Python 3.9 o posterior y su biblioteca estándar.

## Ejecutar con los datos del caso de estudio

El paquete aportado está en `Caso_de_estudio_Yuma_Pay`. Contiene 120.972
transacciones y 48.281 eventos de sesión. Su README aclara que son datos
ficticios de la hackatón. Esta ejecución usa esos CSV, sin generar transacciones.

Desde la raíz del repositorio, abrir dos terminales. En CMD de Windows:

Primera terminal (mantener abierta):

```cmd
py Caso_de_estudio_Yuma_Pay/04_Sandbox_API/mock_api.py
```

Segunda terminal:

```cmd
py prueba_escudo_yuma.py 120972
```

En macOS/Linux reemplazar `py` por `python3`. Para una prueba parcial,
reemplazar `120972` por la cantidad deseada. Cada ejecución reinicia el sandbox.
El motor carga automáticamente los eventos desde la carpeta del caso y,
si no existe allí el archivo, busca en `03_Datos/eventos_app.csv`.

El sandbox oculta las etiquetas de fraude al motor y las usa para calcular
las métricas. Detectado significa desafiar, retener o rechazar una operación
fraudulenta. Falso positivo significa retener o rechazar una operación legítima;
los desafíos a operaciones legítimas no cuentan como falsos positivos en esa API.
La latencia se mide desde la entrega del lote hasta la recepción de las decisiones.

`demo_local.py` es la demo artificial inicial, conservada como referencia; no
se usa en la ejecución del caso de estudio. Los generadores de `00_Organizadores`
se excluyen de Git según la indicación del paquete de no compartirlos con equipos.

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
