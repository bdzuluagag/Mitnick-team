# Yuma Pay · Paquete del caso de estudio «Escudo Yuma»

Yuma Pay S.A. es una **organización ficticia** creada para una hackatón. Su nombre, sus cifras,
sus clientes y sus datos son inventados; ningún registro corresponde a una persona real.

Contacto del reto: John Mazo, CISO · Jmazo@yumapay.online · www.yumapay.online

## Qué hay en cada carpeta

| Carpeta o archivo | Contenido |
| --- | --- |
| `Caso_de_estudio_Yuma_Pay.docx` | El caso para los equipos: problema, modalidades de fraude, arquitectura, datos, línea base, entregables y criterios. |
| `01_Formulario/` | Formulario del reto empresarial diligenciado (Word). |
| `02_Arquitectura/` | `Yuma_Pay_Arquitectura.drawio` con cuatro páginas editables y su vista previa en PNG. |
| `03_Datos/` | Datos sintéticos en CSV, reglas vigentes, diccionario de datos y `linea_base.py`. |
| `04_Sandbox_API/` | `openapi.yaml` y `mock_api.py`, una API simulada que entrega transacciones y califica las decisiones. |
| `05_Marca/` | Logo e ícono de Yuma Pay en SVG y PNG. |
| `06_Sitio_web/` | `index.html`: sitio de demostración con ingreso, panel del cliente, panel del analista y 10 clientes de prueba. |
| `00_Organizadores/` | Programas que generan los datos, los diagramas y los documentos. **No lo compartas con los equipos**: muestra cómo se simuló el fraude. |

## Arquitectura (draw.io)

Abre `02_Arquitectura/Yuma_Pay_Arquitectura.drawio` en <https://app.diagrams.net> (Archivo → Abrir desde → Dispositivo)
o en draw.io de escritorio. Páginas:

1. Arquitectura actual: el fraude se evalúa después de autorizar.
2. Arquitectura objetivo: Escudo Yuma decide antes de autorizar.
3. Flujo de autorización de una transferencia.
4. Proceso actual de gestión de alertas y reclamaciones.

Las imágenes de `vista_previa/` son una referencia rápida; el archivo editable es el `.drawio`.

## Datos

Periodo: 1 de mayo a 31 de octubre de 2026. CSV en UTF-8 separados por comas.
En Excel en español usa Datos → Desde texto/CSV y elige la coma como delimitador.

| Archivo | Filas | Contenido |
| --- | ---: | --- |
| `transacciones.csv` | 120.972 | Operaciones con la etiqueta `es_fraude` y su modalidad |
| `clientes.csv` | 6.000 | Datos anónimos del cliente y marca de cuenta mula |
| `eventos_app.csv` | 48.281 | Inicios de sesión, dispositivos, cambios de clave y de SIM |
| `alertas.csv` | 9.687 | Alertas del motor actual y decisión del analista |
| `reglas_vigentes.csv` | 12 | Reglas del motor actual |
| `diccionario_de_datos.csv` | 51 | Descripción de cada campo |

La muestra está enriquecida: el 1,41 % de las operaciones son fraude (1.704), mucho más que en la operación real.

### Línea base

```bash
pip install pandas
python 03_Datos/linea_base.py
```

Resultado en la muestra: 9.687 alertas, 89,0 % de falsos positivos, 62,6 % de las operaciones de fraude alertadas
(después de autorizadas) y 85,4 % del monto de fraude alertado.

## Sandbox de la API

```bash
python 04_Sandbox_API/mock_api.py            # http://localhost:8080
curl "http://localhost:8080/v1/transacciones/siguiente?cantidad=5"
curl -X POST http://localhost:8080/v1/decisiones -H "Content-Type: application/json" \
     -d '{"id_transaccion":"T00000001","decision":"aprobar","puntaje":0.03,"razones":["operación habitual"]}'
curl http://localhost:8080/v1/metricas
```

Solo necesita Python 3.9 o superior. La especificación completa está en `openapi.yaml`.

## Sitio de demostración

Abre `06_Sitio_web/index.html` en el navegador o súbelo a tu alojamiento. Es un solo archivo, sin dependencias.
Todo ocurre en el navegador: no envía ni guarda datos, y al recargar vuelve al estado inicial.

- **Clientes de prueba:** celulares 300 000 0001 a 300 000 0010; la clave de cada uno aparece en la pantalla de ingreso.
- **Analista:** usuario `analista`, clave `2026`.
- **Para provocar una retención:** envía plata a la llave reportada 300 999 0000, o activa las señales en «Seguridad».

La franja amarilla «Simulación para hackatón» y el aviso del pie de página deben quedarse: evitan que alguien
confunda la demostración con un servicio financiero real o escriba en ella datos verdaderos.

## Regenerar todo (organizadores)

```bash
pip install pandas numpy && npm install docx
python 00_Organizadores/generar_datos.py          # datos (semilla fija, resultado reproducible)
python 00_Organizadores/generar_diagramas.py      # draw.io
node 00_Organizadores/construir_formulario.js 01_Formulario/Reto_empresarial_Yuma_Pay.docx
node 00_Organizadores/construir_caso.js           # caso de estudio
```
