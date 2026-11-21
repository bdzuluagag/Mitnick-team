#!/usr/bin/env python3
"""Sandbox HTTP de demostración con datos ficticios; no mide precisión antifraude."""
import argparse
from collections import Counter
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import subprocess
import sys
from threading import Thread
from urllib.parse import parse_qs, urlparse


def transaccion(indice):
    escenario = indice % 5
    return {
        "id_transaccion": f"DEMO-{indice + 1:06d}",
        "id_cliente": f"cliente_ficticio_{indice}",
        "id_destino": f"destino_ficticio_{indice}",
        "id_dispositivo": f"dispositivo_ficticio_{indice}",
        "tipo_operacion": "pago_qr" if escenario == 4 else "transferencia_inmediata",
        "tipo_destino": "comercio" if escenario == 4 else "cuenta_yuma",
        "monto_cop": 800_000 if escenario == 2 else 150_000,
        "saldo_antes_cop": 1_000_000,
        "destino_nuevo": 1,
        "dispositivo_nuevo": int(escenario == 3),
        "cambio_clave_24h": int(escenario == 3),
        "cambio_sim_48h": int(escenario in (1, 3)),
        "ip_departamento_distinto": int(escenario == 3),
        "antiguedad_cuenta_dias": 10 if escenario == 2 else 365,
        "fecha_hora": (datetime(2026, 1, 1, 12) + timedelta(seconds=indice)).strftime("%Y-%m-%d %H:%M:%S"),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cantidad", nargs="?", type=int, default=2000)
    args = parser.parse_args()
    if args.cantidad <= 0:
        parser.error("cantidad debe ser mayor que cero")
    estado = {"cursor": 0, "decisiones": []}

    class Sandbox(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def responder(self, datos, status=200):
            cuerpo = json.dumps(datos).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(cuerpo)))
            self.end_headers()
            self.wfile.write(cuerpo)

        def do_GET(self):
            url = urlparse(self.path)
            if url.path == "/v1/transacciones/siguiente":
                cantidad = int(parse_qs(url.query).get("cantidad", [50])[0])
                fin = min(estado["cursor"] + max(0, cantidad), args.cantidad)
                lote = [transaccion(i) for i in range(estado["cursor"], fin)]
                estado["cursor"] = fin
                self.responder({"transacciones": lote})
            elif url.path == "/v1/metricas":
                conteos = Counter(d["decision"] for d in estado["decisiones"])
                self.responder({
                    "fuente": "DEMO LOCAL: datos sinteticos",
                    "transacciones_evaluadas": len(estado["decisiones"]),
                    **{k: conteos[k] for k in ("aprobar", "desafiar", "retener", "rechazar")},
                    "precision_antifraude": "No medida: no hay etiquetas reales",
                })
            else:
                self.responder({"error": "Ruta desconocida"}, 404)

        def do_POST(self):
            datos = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            if self.path == "/v1/reiniciar":
                estado.update(cursor=0, decisiones=[])
            elif self.path == "/v1/decisiones":
                estado["decisiones"].extend(datos)
            else:
                self.responder({"error": "Ruta desconocida"}, 404)
                return
            self.responder({"ok": True})

    # Un puerto efímero evita reiniciar accidentalmente un sandbox existente.
    servidor = HTTPServer(("127.0.0.1", 0), Sandbox)
    hilo = Thread(target=servidor.serve_forever, daemon=True)
    hilo.start()
    print("DEMO LOCAL — transacciones sinteticas, sin operaciones bancarias reales.", flush=True)
    codigo = (
        "import runpy, sys; "
        "from unittest.mock import patch; "
        "import urllib.request; "
        "original = urllib.request.urlopen; "
        f"puerto = {servidor.server_port}; "
        "\ndef abrir(req, *a, **kw):\n"
        "    req.full_url = req.full_url.replace('127.0.0.1:8080', f'127.0.0.1:{puerto}');\n"
        "    return original(req, *a, **kw)\n"
        "with patch('urllib.request.urlopen', abrir):\n"
        "    runpy.run_path('prueba_escudo_yuma.py', run_name='__main__')\n"
    )
    try:
        resultado = subprocess.run(
            [sys.executable, "-u", "-c", codigo, str(args.cantidad)],
            cwd=Path(__file__).resolve().parent,
        )
        return resultado.returncode
    finally:
        servidor.shutdown()
        servidor.server_close()
        hilo.join()


if __name__ == "__main__":
    sys.exit(main())
