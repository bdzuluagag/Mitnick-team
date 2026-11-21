#!/usr/bin/env python3
"""
Sandbox de Yuma Pay (organización ficticia): API simulada para el reto antifraude.

Entrega transacciones sin la etiqueta de fraude, recibe la decisión de tu sistema
y calcula los indicadores contra la etiqueta real.

Uso:
    python mock_api.py                      # puerto 8080, datos en ../03_Datos
    python mock_api.py --puerto 9000 --datos ruta/a/03_Datos

Solo usa la biblioteca estándar de Python 3.9 o superior.
"""
import argparse
import csv
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from urllib.parse import parse_qs, urlparse

OCULTAS = {"es_fraude", "modalidad_fraude"}
ENTEROS = {"monto_cop", "saldo_antes_cop", "destino_nuevo", "dispositivo_nuevo", "cambio_clave_24h",
           "cambio_sim_48h", "ip_departamento_distinto", "antiguedad_cuenta_dias"}
DECISIONES = {"aprobar", "desafiar", "retener", "rechazar"}
BLOQUEAN = {"retener", "rechazar"}          # el dinero no sale
MAX_LOTE = 500


class Estado:
    def __init__(self, carpeta: Path):
        self.candado = Lock()
        self.transacciones, self.etiquetas, self.montos = [], {}, {}
        with open(carpeta / "transacciones.csv", encoding="utf-8-sig", newline="") as f:
            for fila in csv.DictReader(f):
                self.etiquetas[fila["id_transaccion"]] = int(fila["es_fraude"])
                self.montos[fila["id_transaccion"]] = int(fila["monto_cop"])
                self.transacciones.append({k: (int(v) if k in ENTEROS else v) for k, v in fila.items() if k not in OCULTAS})
        self.eventos = {}
        with open(carpeta / "eventos_app.csv", encoding="utf-8-sig", newline="") as f:
            for fila in csv.DictReader(f):
                self.eventos.setdefault(fila["id_cliente"], []).append(fila)
        self.reiniciar()

    def reiniciar(self):
        self.cursor, self.entregadas, self.decisiones = 0, {}, {}

    def siguiente(self, cantidad):
        with self.candado:
            lote = self.transacciones[self.cursor:self.cursor + cantidad]
            self.cursor += len(lote)
            ahora = time.perf_counter()
            for t in lote:
                self.entregadas[t["id_transaccion"]] = ahora
            return lote, len(self.transacciones) - self.cursor

    def decidir(self, d):
        idt = d["id_transaccion"]
        with self.candado:
            entregada = self.entregadas.get(idt)
            latencia = round(1000 * (time.perf_counter() - entregada), 1) if entregada else None
            self.decisiones[idt] = dict(decision=d["decision"], puntaje=d.get("puntaje"), latencia_ms=latencia)
            return latencia

    def metricas(self):
        with self.candado:
            vp = fp = fn = vn = desafios = 0
            monto_fraude = monto_protegido = 0
            latencias = []
            for idt, d in self.decisiones.items():
                fraude, bloquea = self.etiquetas[idt] == 1, d["decision"] in BLOQUEAN
                desafios += d["decision"] == "desafiar"
                if d["latencia_ms"] is not None:
                    latencias.append(d["latencia_ms"])
                if fraude:
                    monto_fraude += self.montos[idt]
                    if bloquea or d["decision"] == "desafiar":
                        vp += 1
                        monto_protegido += self.montos[idt]
                    else:
                        fn += 1
                elif bloquea:
                    fp += 1
                else:
                    vn += 1
            latencias.sort()
            pct = lambda a, b: round(100 * a / b, 2) if b else None  # noqa: E731
            return {
                "transacciones_decididas": len(self.decisiones),
                "transacciones_pendientes": len(self.transacciones) - len(self.decisiones),
                "fraudes_en_lo_decidido": vp + fn,
                "fraude_detectado_pct": pct(vp, vp + fn),
                "monto_fraude_protegido_pct": pct(monto_protegido, monto_fraude),
                "falsos_positivos_pct": pct(fp, vp + fp),
                "clientes_legitimos_bloqueados_pct": pct(fp, fp + vn),
                "desafios": desafios,
                "latencia_ms_p50": latencias[len(latencias) // 2] if latencias else None,
                "latencia_ms_p99": latencias[min(len(latencias) - 1, int(len(latencias) * 0.99))] if latencias else None,
                "nota": "Detectado = fraude con decisión desafiar, retener o rechazar. "
                        "Falso positivo = operación legítima retenida o rechazada. "
                        "La latencia se mide desde la entrega de la transacción hasta la decisión.",
            }


class Manejador(BaseHTTPRequestHandler):
    estado: Estado = None
    server_version = "YumaPaySandbox/1.0"

    def _json(self, codigo, cuerpo):
        datos = json.dumps(cuerpo, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(datos)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(datos)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        url = urlparse(self.path)
        q = parse_qs(url.query)
        partes = [p for p in url.path.split("/") if p]
        if partes == ["v1", "salud"]:
            return self._json(200, {"estado": "ok", "transacciones": len(self.estado.transacciones)})
        if partes == ["v1", "transacciones", "siguiente"]:
            try:
                cantidad = max(1, min(MAX_LOTE, int(q.get("cantidad", ["1"])[0])))
            except ValueError:
                return self._json(400, {"error": "cantidad debe ser un número entero"})
            lote, restantes = self.estado.siguiente(cantidad)
            return self._json(200, {"transacciones": lote, "restantes": restantes})
        if len(partes) == 4 and partes[:2] == ["v1", "clientes"] and partes[3] == "eventos":
            eventos = self.estado.eventos.get(partes[2], [])
            hasta = q.get("hasta", [None])[0]
            if hasta:
                eventos = [e for e in eventos if e["fecha_hora"] <= hasta]
            return self._json(200, {"id_cliente": partes[2], "eventos": eventos})
        if partes == ["v1", "metricas"]:
            return self._json(200, self.estado.metricas())
        self._json(404, {"error": "ruta no encontrada"})

    def do_POST(self):
        partes = [p for p in urlparse(self.path).path.split("/") if p]
        if partes == ["v1", "reiniciar"]:
            with self.estado.candado:
                self.estado.reiniciar()
            return self._json(200, {"reiniciado": True})
        if partes != ["v1", "decisiones"]:
            return self._json(404, {"error": "ruta no encontrada"})
        try:
            largo = int(self.headers.get("Content-Length", "0"))
            cuerpo = json.loads(self.rfile.read(largo) or b"{}")
        except (ValueError, json.JSONDecodeError):
            return self._json(400, {"error": "el cuerpo debe ser JSON válido"})
        lista = cuerpo if isinstance(cuerpo, list) else [cuerpo]
        respuestas = []
        for d in lista:
            if not isinstance(d, dict) or d.get("id_transaccion") not in self.estado.etiquetas:
                return self._json(400, {"error": "id_transaccion desconocido o ausente"})
            if d.get("decision") not in DECISIONES:
                return self._json(400, {"error": f"decision debe ser una de {sorted(DECISIONES)}"})
            p = d.get("puntaje")
            if p is not None and not (isinstance(p, (int, float)) and 0 <= p <= 1):
                return self._json(400, {"error": "puntaje debe estar entre 0 y 1"})
        for d in lista:
            respuestas.append({"id_transaccion": d["id_transaccion"], "recibida": True, "latencia_ms": self.estado.decidir(d)})
        self._json(201, respuestas if isinstance(cuerpo, list) else respuestas[0])

    def log_message(self, *args):  # silencio en consola
        pass


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Sandbox de la API antifraude de Yuma Pay (ficticia)")
    ap.add_argument("--puerto", type=int, default=8080)
    ap.add_argument("--datos", type=Path, default=Path(__file__).resolve().parent.parent / "03_Datos")
    args = ap.parse_args()
    Manejador.estado = Estado(args.datos)
    print(f"Sandbox Yuma Pay en http://localhost:{args.puerto}/v1/salud  ({len(Manejador.estado.transacciones)} transacciones)")
    ThreadingHTTPServer(("127.0.0.1", args.puerto), Manejador).serve_forever()
