# -*- coding: utf-8 -*-
"""
Prueba de la cadena PC → API → Gateway → Arduino, sin Alexa.

Requiere la API (python -m api.main) y el gateway (python -m gateway.main) corriendo.
Llama al endpoint /dispositivos, que usa el mismo caso de uso de confort que Alexa.

Uso (desde la raíz del repo, con el venv activado):
  python -m api.test_hardware_local
"""
import sys
import time
import httpx

API_URL = "http://localhost:8000"

SECUENCIA = [
    ("luz", "encender"),
    ("ventilador", "encender"),
    ("ventilador", "apagar"),
    ("luz", "apagar"),
]


def main() -> None:
    print("==================================================")
    print("  HospedaSmart - Prueba PC → API → Gateway → Arduino")
    print("==================================================")

    with httpx.Client(base_url=API_URL, timeout=6.0) as client:
        try:
            estado = client.get("/dispositivos/estado").json()
        except httpx.ConnectError:
            print("❌ No se pudo conectar a la API. ¿Está corriendo python -m api.main?")
            sys.exit(1)

        if not estado.get("gateway_conectado"):
            print("❌ La API está viva pero el gateway no está conectado. Arranca python -m gateway.main.")
            sys.exit(1)
        print("✅ API y gateway conectados.\n")

        fallos = 0
        for dispositivo, accion in SECUENCIA:
            inicio = time.monotonic()
            resp = client.post(f"/dispositivos/{dispositivo}/{accion}")
            ms = (time.monotonic() - inicio) * 1000
            if resp.status_code == 200:
                print(f"✅ {accion + ' ' + dispositivo:<20} {ms:6.0f} ms  → {resp.json()['mensaje']}")
            else:
                fallos += 1
                print(f"❌ {accion + ' ' + dispositivo:<20} {ms:6.0f} ms  → HTTP {resp.status_code}: {resp.json().get('detail')}")
            time.sleep(1.5)

    print("\n==================================================")
    print(f"Resultado: {len(SECUENCIA) - fallos}/{len(SECUENCIA)} órdenes confirmadas.")
    sys.exit(1 if fallos else 0)


if __name__ == "__main__":
    main()
