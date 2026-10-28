# -*- coding: utf-8 -*-
"""
Prueba directa PC ↔ Arduino por USB, sin API ni Alexa.

Usa el mismo puente serie que el gateway (serial_bridge) y exige hardware real:
si no encuentra el Arduino, falla en vez de pasar al simulador.

Uso (desde la raíz del repo, con el venv activado):
  python -m gateway.test_serial            → secuencia automática de todas las órdenes
  python -m gateway.test_serial -i         → modo interactivo (escribes VENT_ON, LUZ_OFF, ...)
  python -m gateway.test_serial -p COM3    → puerto explícito
"""
import os
import sys
import time
import argparse

# Debe fijarse antes de importar serial_bridge, que lee la variable al cargar
os.environ["SIMULACION"] = "false"

from gateway.serial_bridge import ArduinoBridge, HardwareNoDisponible, SERIAL_PORT, BAUDRATE  # noqa: E402

SECUENCIA = [
    ("LUZ_ON", "¿Se encendió el LED blanco (D13)?"),
    ("LUZ_OFF", "¿Se apagó el LED blanco?"),
    ("VENT_ON", "¿Gira el ventilador?"),
    ("VENT_OFF", "¿Se detuvo el ventilador?"),
    ("PUERTA_ABRIR", "¿El servo (D9) giró a 90°?"),
    ("PUERTA_CERRAR", "¿El servo volvió a 0°?"),
]


def prueba_automatica(bridge: ArduinoBridge, pausa: float) -> bool:
    resultados = []
    for orden, pregunta in SECUENCIA:
        inicio = time.monotonic()
        ok = bridge.enviar(orden)
        ms = (time.monotonic() - inicio) * 1000
        marca = "✅" if ok else "❌"
        print(f"{marca} {orden:<14} {ms:6.0f} ms   {pregunta if ok else 'sin OK del Arduino'}\n", flush=True)
        resultados.append(ok)
        time.sleep(pausa)

    total_ok = sum(resultados)
    print("==================================================")
    print(f"Resultado: {total_ok}/{len(resultados)} órdenes confirmadas por el Arduino.")
    if total_ok < len(resultados):
        print("Revisa que el sketch cargado responda OK:<orden> y use Serial.begin(115200).")
    return total_ok == len(resultados)


def prueba_interactiva(bridge: ArduinoBridge) -> None:
    print("Escribe una orden (VENT_ON, VENT_OFF, LUZ_ON, LUZ_OFF, PUERTA_ABRIR, PUERTA_CERRAR).")
    print("Línea vacía o Ctrl+C para salir.\n")
    while True:
        try:
            orden = input("orden> ").strip().upper()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not orden:
            return
        ok = bridge.enviar(orden)
        print("✅ confirmada\n" if ok else "❌ sin confirmación\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Prueba directa PC ↔ Arduino (sin API ni Alexa)")
    parser.add_argument("-p", "--puerto", default=SERIAL_PORT, help="Puerto serie (ej. COM3). Por defecto se detecta.")
    parser.add_argument("-i", "--interactivo", action="store_true", help="Enviar órdenes a mano")
    parser.add_argument("--pausa", type=float, default=1.5, help="Segundos entre órdenes en modo automático")
    args = parser.parse_args()

    print("==================================================")
    print("   HospedaSmart - Prueba directa PC ↔ Arduino     ")
    print("==================================================")

    bridge = ArduinoBridge(args.puerto, BAUDRATE)
    try:
        bridge.conectar()
    except HardwareNoDisponible:
        sys.exit(1)

    try:
        if args.interactivo:
            prueba_interactiva(bridge)
        else:
            sys.exit(0 if prueba_automatica(bridge, args.pausa) else 1)
    finally:
        bridge._cerrar()


if __name__ == "__main__":
    main()
