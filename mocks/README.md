# /mocks
#
# Servicio FastAPI que simula los 5 sistemas externos que no se integran de verdad.
# Corre en Docker en el puerto 9000.
#
# Cada archivo finge un servicio externo con respuestas fijas:
#   pagos.py           → POST /pagos/cobrar         → {"ok": true, "auth_code": "FAKE-001"}
#   kyc.py             → POST /kyc/verificar         → {"ok": true}
#   clima.py           → GET  /clima?lat=...&lon=... → {"temp_c": 28, "humidity": 65}
#   ecu911.py          → POST /911/despacho          → {"ok": true, "dispatch_id": "D-999"}
#   channel_manager.py → POST /channel/sync          → {"reservations": [...]}
#
# El valor de este servicio es que al borrarlo o reemplazarlo con el proveedor real,
# NADA MÁS CAMBIA. Solo se modifica el adaptador correspondiente en api/adapters/.
