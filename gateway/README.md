# /gateway
#
# Proceso NATIVO (fuera de Docker) que traduce entre la API y el Arduino.
# - Se conecta al backend por WebSocket (ws://localhost:8000/ws/gateway)
# - Se conecta al Arduino por puerto serie USB (pyserial, 115200 baudios)
# - Traduce comandos JSON ↔ órdenes de texto (VENT_ON, LUZ_OFF, etc.)
# - Reporta eventos espontáneos del Arduino (gas_critical, etc.)
#
# Corre fuera de Docker porque Docker en Windows no pasa puertos COM/USB.
#
# Archivos previstos:
#   main.py          → arranca WebSocket + serie, orquesta la comunicación
#   serial_bridge.py → leer/escribir al puerto serie con reconexión automática
#   protocol.py      → traducir entre el protocolo JSON y los comandos de texto
