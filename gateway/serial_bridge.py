# -*- coding: utf-8 -*-
"""
Puente de comunicación serial con el Arduino (pyserial).

Soporta dos modos:
1. Modo Hardware Real: detecta el Arduino por USB y se comunica a 115200 baudios.
2. Modo Simulación: se activa automáticamente si no hay Arduino físico conectado
   o si la variable de entorno SIMULACION=true está activa.

Variable SIMULACION:
  - sin definir → automático (hardware si hay Arduino; si no, simulación)
  - true        → siempre simulación
  - false       → exige hardware real; si no se puede abrir el puerto, el gateway se detiene
                  (evita creer que el Arduino responde cuando en realidad es el simulador)
"""
import os
import time
import threading
import serial
from serial.tools import list_ports

BAUDRATE = int(os.getenv("BAUDRATE", "115200"))
SERIAL_PORT = os.getenv("SERIAL_PORT", None)
_SIMULACION = os.getenv("SIMULACION", "").lower()
FORZAR_SIMULACION = _SIMULACION in ("true", "1")
EXIGIR_HARDWARE = _SIMULACION in ("false", "0")
# Espera del OK:<orden>; debe ser menor que el timeout de la API (2,5 s) para que el ack llegue a tiempo
ESPERA_ACK_S = float(os.getenv("ESPERA_ACK_S", "2.0"))


class HardwareNoDisponible(RuntimeError):
    """El modo SIMULACION=false exige un Arduino real y no se pudo abrir el puerto."""


def detectar_puerto_usb() -> str | None:
    """Busca el puerto serie USB del Arduino. Retorna None si no hay o si falla."""
    try:
        # En Windows los COM por Bluetooth no tienen "USB" en el hwid, así que quedan fuera
        puertos_usb = [p.device for p in list_ports.comports() if "USB" in (p.hwid or "").upper() or "ACM" in p.device or "USB" in p.device]
        if len(puertos_usb) == 1:
            return puertos_usb[0]
        elif len(puertos_usb) > 1:
            print(f"[SERIAL] Múltiples puertos USB detectados ({puertos_usb}). Usando el primero: {puertos_usb[0]}", flush=True)
            return puertos_usb[0]
    except Exception as e:
        print(f"[SERIAL] Error al listar puertos: {e}", flush=True)
    return None


class ArduinoBridge:
    """Maneja el envío de comandos al Arduino físico o al simulador."""

    def __init__(self, puerto: str | None = None, baudios: int = BAUDRATE):
        self._puerto_configurado = puerto
        self._baudios = baudios
        self._serial: serial.Serial | None = None
        # RLock: _enviar_hardware reconecta llamando a conectar() con el lock ya tomado
        self._lock = threading.RLock()
        self.modo_simulacion = False
        self._estado_simulado = {
            "ventilador": False,
            "luz": False,
            "puerta_abierta": False
        }

    def conectar(self) -> None:
        """Intenta abrir el puerto serie real; si no es posible, activa la simulación."""
        if FORZAR_SIMULACION:
            self._activar_modo_simulacion("Variable SIMULACION=true activa.")
            return

        puerto = self._puerto_configurado or detectar_puerto_usb()
        if not puerto:
            self._activar_modo_simulacion("No se detectó ningún Arduino conectado por USB.")
            return

        try:
            with self._lock:
                print(f"[SERIAL] Conectando a {puerto} a {self._baudios} baudios...", flush=True)
                self._serial = serial.Serial(puerto, self._baudios, timeout=0.5)
                # Abrir el puerto reinicia el Arduino; esperar a que termine su arranque
                self._esperar_arranque()
                print(f"[SERIAL] ✅ Conectado exitosamente con hardware real en {puerto}.", flush=True)
                self.modo_simulacion = False
        except Exception as e:
            self._activar_modo_simulacion(f"Fallo al abrir puerto {puerto}: {e}")

    def _esperar_arranque(self, silencio: float = 0.6, maximo: float = 6.0) -> None:
        """
        Espera a que el Arduino termine de arrancar: el bootloader tarda ~1,5 s, el sketch
        puede iniciar la LCD (~1 s más) y luego imprime su menú. Se considera listo cuando
        ya llegó el texto de arranque y pasan `silencio` segundos sin datos; si el sketch no
        imprime nada, se espera `maximo`. Con una espera fija de 2,5 s la primera orden
        llegaba mientras la placa aún arrancaba y se perdía.
        """
        assert self._serial is not None
        inicio = time.monotonic()
        ultimo_dato: float | None = None
        while time.monotonic() - inicio < maximo:
            if self._serial.in_waiting:
                self._serial.read(self._serial.in_waiting)
                ultimo_dato = time.monotonic()
            elif ultimo_dato is not None and time.monotonic() - ultimo_dato >= silencio:
                break
            time.sleep(0.05)
        self._serial.reset_input_buffer()

    def _activar_modo_simulacion(self, motivo: str) -> None:
        if EXIGIR_HARDWARE:
            print(f"[SERIAL] ❌ {motivo}", flush=True)
            print("[SERIAL] SIMULACION=false exige hardware real. Revisa el cable, el puerto (SERIAL_PORT) "
                  "y que el Monitor Serial del Arduino IDE esté cerrado.", flush=True)
            raise HardwareNoDisponible(motivo)
        self.modo_simulacion = True
        print(f"[SERIAL] ⚠️ {motivo}", flush=True)
        print("[SERIAL] 🤖 ACTIVANDO MODO SIMULACIÓN: Las órdenes serán emuladas por software.", flush=True)

    def enviar(self, orden: str, espera: float = ESPERA_ACK_S) -> bool:
        """
        Envía una orden ('VENT_ON', etc.) y espera confirmación ('OK:VENT_ON').
        Retorna True si fue confirmada.
        """
        if self.modo_simulacion:
            return self._enviar_simulado(orden)
        else:
            return self._enviar_hardware(orden, espera)

    def _enviar_simulado(self, orden: str) -> bool:
        """Emula la respuesta inmediata del Arduino en memoria."""
        print(f"[SIMULADOR-HARDWARE] -> Recibida orden: '{orden}'", flush=True)
        time.sleep(0.1)  # Simular latencia física mínima

        if orden == "VENT_ON":
            self._estado_simulado["ventilador"] = True
            print("[SIMULADOR-HARDWARE] 🌀 Ventilador encendido (simulado).", flush=True)
        elif orden == "VENT_OFF":
            self._estado_simulado["ventilador"] = False
            print("[SIMULADOR-HARDWARE] ⏹️ Ventilador apagado (simulado).", flush=True)
        elif orden == "LUZ_ON":
            self._estado_simulado["luz"] = True
            print("[SIMULADOR-HARDWARE] 💡 Luz encendida (simulado).", flush=True)
        elif orden == "LUZ_OFF":
            self._estado_simulado["luz"] = False
            print("[SIMULADOR-HARDWARE] 🌑 Luz apagada (simulado).", flush=True)
        elif orden == "PUERTA_ABRIR":
            self._estado_simulado["puerta_abierta"] = True
            print("[SIMULADOR-HARDWARE] 🔓 Cerrojo abierto (simulado).", flush=True)
        elif orden == "PUERTA_CERRAR":
            self._estado_simulado["puerta_abierta"] = False
            print("[SIMULADOR-HARDWARE] 🔒 Cerrojo cerrado (simulado).", flush=True)

        print(f"[SIMULADOR-HARDWARE] <- Acuse generado: 'OK:{orden}'", flush=True)
        return True

    def _enviar_hardware(self, orden: str, espera: float) -> bool:
        """Escribe al puerto serie USB real y espera la respuesta OK:<orden>."""
        with self._lock:
            try:
                if self._serial is None or not self._serial.is_open:
                    print("[SERIAL] Reintentando conexión con puerto...", flush=True)
                    self.conectar()
                    if self.modo_simulacion:
                        return self._enviar_simulado(orden)

                assert self._serial is not None
                self._serial.reset_input_buffer()
                self._serial.write((orden + "\n").encode("ascii"))
                print(f"[SERIAL] -> Enviado a Arduino: {orden}", flush=True)

                limite = time.monotonic() + espera
                while time.monotonic() < limite:
                    linea = self._serial.readline().decode("utf-8", "replace").strip()
                    if not linea:
                        continue
                    print(f"[ARDUINO] {linea}", flush=True)
                    if linea == f"OK:{orden}":
                        return True

                print(f"[SERIAL] ❌ Timeout: No se recibió 'OK:{orden}' en {espera}s", flush=True)
                return False
            except HardwareNoDisponible:
                return False
            except serial.SerialException as e:
                print(f"[SERIAL-ERROR] Error en comunicación serie: {e}", flush=True)
                self._cerrar()
                return False

    def _cerrar(self) -> None:
        if self._serial is not None:
            try:
                self._serial.close()
            except Exception:
                pass
            self._serial = None


bridge = ArduinoBridge(SERIAL_PORT, BAUDRATE)
