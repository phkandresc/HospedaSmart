# /firmware
#
# Aquí irá el sketch definitivo del Arduino (el firmware de producción).
#
# El archivo sensor_diagnostics.ino que está en prueba-alexa/ es un BANCO DE PRUEBAS,
# no el firmware final. El firmware definitivo debe:
#
# 1. Ser una máquina de estados con millis() (sin delay() largos)
# 2. Leer el MQ-2 cada 200ms y activar extractor+sirena LOCALMENTE si hay gas
#    (sin depender de la laptop ni de internet)
# 3. Aceptar comandos por serie: VENT_ON, VENT_OFF, LUZ_ON, LUZ_OFF, PUERTA_ABRIR, PUERTA_CERRAR
# 4. Confirmar cada comando con OK:<comando>
# 5. Reportar eventos espontáneos: EVT:GAS_CRITICAL:<valor>
# 6. Enviar heartbeat periódico para que el gateway sepa que está vivo
#
# Mapa de pines (Keyestudio KS0085):
#   PIR        → D2
#   Buzzer     → D3
#   Botón      → D4
#   Ventilador → D5/D6 (L9110)
#   Relé       → D7
#   Servo      → D9
#   LED amar.  → D12
#   LED blanco → D13
#   LDR        → A0
#   Vapor      → A1
#   MQ-2       → A2
#   LCD I2C    → A4/A5
