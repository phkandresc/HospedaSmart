# Paso 2 — Vista de contenedores

> Un **contenedor** (en el sentido C4) es una unidad que se ejecuta por separado: un proceso,
> un servicio, una base de datos. No confundir con "contenedor Docker", aunque aquí coinciden.

---

## 1. La decisión central

**Cuatro procesos, no veinte.** Con una habitación y 4 flujos, agregar servicios es la forma
más rápida de no terminar. Cada contenedor existe porque resuelve un problema real:

```
┌──────────────────────────── LAPTOP (demo) ─────────────────────────────┐
│                                                                        │
│   ngrok  ──https──▶  ┌──────────────────────────┐                      │
│                      │  api  (FastAPI) :8000    │                      │
│   Echo Dot ─voz─▶    │  · webhooks de Alexa     │                      │
│   Nube Alexa         │  · núcleo de negocio     │                      │
│                      │  · panel web (Jinja)     │                      │
│                      │  · WebSocket del gateway │                      │
│                      └────┬──────────────┬──────┘                      │
│                           │              │                             │
│                  ┌────────▼───────┐  ┌───▼─────────────────┐           │
│                  │ db PostgreSQL  │  │ mocks (FastAPI)     │           │
│                  │ :5432          │  │ :9000               │           │
│                  │                │  │ 5 externos falsos   │           │
│                  └────────────────┘  └─────────────────────┘           │
│                                                                        │
│   ┌────────────────────────────────────────┐                          │
│   │ gateway (proceso NATIVO, no Docker)    │                          │
│   │ · pyserial  · reconexión  · heartbeat  │                          │
│   └───────────────────┬────────────────────┘                          │
└───────────────────────┼────────────────────────────────────────────────┘
                        │ USB serie (115200)
                 ┌──────▼──────────────────┐
                 │ Arduino + kit KS0085    │
                 │ seguridad local (F2)    │
                 └─────────────────────────┘
```

---

## 2. Responsabilidad de cada contenedor

| Contenedor | Responsabilidad **única** | Tecnología | Por qué así |
|---|---|---|---|
| **api** | Recibir canales, ejecutar casos de uso, servir el panel | FastAPI + Pydantic + SQLAlchemy + Jinja2/HTMX | Un solo despliegue para la demo; async para webhooks y WebSocket |
| **db** | Estado verdadero del sistema | PostgreSQL 16 | Concurrencia real, tipos JSONB, un solo contenedor en compose |
| **gateway** | Traducir entre el protocolo de la API y el puerto serie | Python + pyserial + `websockets` | **Nativo** por el acceso al puerto COM (ver ADR-002) |
| **mocks** | Fingir los 5 sistemas externos | FastAPI | Aísla lo simulado; borrarlo no rompe nada real |
| **ngrok** | Exponer la API a Alexa por HTTPS | ngrok | Requisito de Alexa; ya probado |

**Lo que NO es un contenedor:** los módulos internos (`accesos`, `confort`, `tareas`,
`alertas`) viven dentro de `api` como paquetes de Python. Se separan en el Paso 3.

---

## 3. El contrato API ↔ gateway

Esta es la pieza más importante de todo el diseño: **el contrato**. Si se define bien, el
gateway se puede reescribir en otro lenguaje o mover a otra habitación sin tocar el backend.

El **gateway inicia la conexión** (WebSocket saliente hacia `api`). Consecuencia enorme:
no hay que abrir puertos ni tocar el router, y mañana una habitación remota funciona igual.

**Comando (api → gateway):**

```json
{
  "type": "command",
  "id": "cmd_7f3a91",
  "device": "room101.fan",
  "action": "set_power",
  "params": { "on": true },
  "timeout_ms": 2500
}
```

**Confirmación (gateway → api):**

```json
{ "type": "ack", "id": "cmd_7f3a91", "ok": true,
  "state": { "on": true }, "ts": "2026-10-27T15:04:05Z" }
```

**Evento espontáneo (gateway → api):**

```json
{ "type": "event", "id": "evt_91", "device": "room101.gas",
  "event": "gas_critical", "value": 612, "source": "edge",
  "ts": "2026-10-27T15:04:06Z" }
```

**Reglas del contrato:**

1. Todo comando lleva `id`; el `ack` repite el `id` → **idempotencia** (si se reenvía, no se
   ejecuta dos veces).
2. `source: "edge"` significa que el dispositivo actuó por su cuenta (seguridad local).
3. `heartbeat` cada 5 s; sin heartbeat por 15 s → el dispositivo se marca *offline* en el panel.
4. Nombres de dispositivo estables: `room101.fan`, `room101.light`, `room101.lock`,
   `room101.gas`, `room101.pir`, `room101.ldr`.
5. Si no llega `ack` en `timeout_ms`, el caso de uso responde con honestidad ("no pude
   confirmar"), **nunca** finge éxito.

---

## 4. Cómo viaja un flujo completo (F1: confort por voz)

1. El huésped dice "Alexa, enciende el ventilador".
2. Alexa (nube) hace `POST https://xxx.ngrok-free.dev/alexa` con un JSON firmado.
3. `api` verifica **firma y timestamp** con `WebserviceSkillHandler` (el mismo de la prueba).
4. El handler de Alexa **no** habla con el hardware: llama al caso de uso `controlar_confort`.
5. El caso de uso valida permisos, crea un comando con `id` y lo envía por WebSocket.
6. `gateway` recibe el comando, escribe `VENT_ON\n` al puerto serie.
7. El Arduino ejecuta y responde `OK:VENT_ON`.
8. `gateway` manda el `ack`; el caso de uso actualiza el estado del dispositivo en `db`.
9. `api` devuelve la frase "Listo, ventilador encendido" a Alexa.

**Detalle crítico:** los pasos 5–8 deben caber en ~2,5 s, porque Alexa corta a los 8 s.
Por eso el caso de uso espera el `ack` con timeout corto y no hace trabajo pesado.

---

## 5. Cómo viaja la seguridad (F2: gas)

1. El `loop()` del Arduino lee el MQ-2 cada 200 ms — **sin `delay()` largos**.
2. Si supera el umbral durante N lecturas seguidas: enciende extractor, sirena y LED
   **localmente**. No consulta a nadie.
3. Avisa al gateway por serie: `EVT:GAS_CRITICAL:612`.
4. `gateway` lo reenvía como `event` con `source: "edge"`.
5. `api` guarda la alerta, avisa al panel por WebSocket y pide escalamiento a `mocks/911`.

**Si en el paso 2 se apaga la laptop o se cae internet, los pasos 1–2 igual ocurren.**
Ese es el argumento arquitectónico de todo el proyecto: la nube coordina, el edge protege.

---

## 6. Despliegue

```
docker compose up        # api + db + mocks
python gateway/main.py   # nativo, en otra terminal
ngrok http 8000          # nativo, en otra terminal
```

> ⚠️ **Docker Desktop en Windows no pasa puertos COM.** Por eso el gateway corre nativo con
> su `venv`. Alternativa en Linux: `--device=/dev/ttyUSB0` y todo dentro de Docker. No vale
> la pena pelear con `usbipd-win` para un proyecto de curso.

El gateway se conecta **hacia** `ws://localhost:8000/ws/gateway`, así que no necesita puerto
de entrada ni configuración de red.

---

## 7. Modelo de datos mínimo

| Tabla | Campos clave | Para qué CU |
|---|---|---|
| `property` | id, nombre | Base multi-propiedad (aunque haya 1) |
| `room` | id, property_id, nombre, estado (`disponible`/`ocupada`/`limpieza`/`mantenimiento`) | F4 |
| `device` | id, room_id, tipo, estado (JSONB), last_seen | F1, F2 |
| `reservation` | id, room_id, huésped, check_in, check_out | F3 |
| `credential` | id, reservation_id, `pin_hash`, válido_desde/hasta, activo | F3 |
| `staff` | id, nombre, rol, `code_hash` | F3, F4 |
| `access_event` | id, room_id, credential_id/staff_id, método, resultado, ts | F3, F4 |
| `task` | id, room_id, tipo, descripción, estado, asignado_a, cerrada_en | F4 |
| `alert` | id, room_id, código, valor, severidad, ts, escalada | F2 |

Reglas: **nunca** se guarda un PIN en claro (solo hash), y todo evento de acceso es
inmutable (no se edita ni se borra: es la auditoría).

---

## 8. Decisiones registradas (ADR cortos)

| # | Decisión | Alternativa descartada | Motivo |
|---|---|---|---|
| 001 | **FastAPI** | Flask (el de la prueba) | Validación con Pydantic, async, documentación automática de la API |
| 002 | **Gateway nativo, fuera de Docker** | Todo en Docker | Docker en Windows no pasa puertos COM; ahorra días de dolor |
| 003 | **WebSocket** como transporte | MQTT / HTTP polling | Un solo proceso y un solo socket; el contrato permite migrar a MQTT después |
| 004 | **PostgreSQL** en compose | SQLite | Concurrencia y JSONB; migrar después cuesta más que empezar bien |
| 005 | **Reusar `ask-sdk-core`** y quitar `flask-ask-sdk` | Reescribir la skill desde cero | `WebserviceSkillHandler` ya hace firma + timestamp; solo cambia el adaptador |
| 006 | **Un servicio `mocks`** para los 5 externos | Simular dentro de `api` | Borrar lo falso debe ser trivial; y demuestra el patrón adaptador |
| 007 | **Lógica de seguridad en el firmware** | Lógica de gas en el backend | Es el requisito D1: no puede depender de red ni de la laptop |
| 008 | **Panel con Jinja + HTMX** | SPA en React | 4 pantallas no justifican un build aparte; se puede extraer después |

### Cómo queda el adaptador de Alexa con FastAPI

```python
# api/alexa/router.py
from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.concurrency import run_in_threadpool
from ask_sdk_webservice_support.webservice_handler import WebserviceSkillHandler

router = APIRouter()
handler = WebserviceSkillHandler(skill=skill, verify_signature=True, verify_timestamp=True)

@router.post("/alexa")
async def alexa(request: Request):
    body = (await request.body()).decode("utf-8")
    try:
        # es síncrono y descarga certificados: no bloquear el event loop
        respuesta = await run_in_threadpool(
            handler.verify_request_and_dispatch, dict(request.headers), body
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Petición no válida")
    return Response(content=respuesta, media_type="application/json")
```

Los **handlers** (`LaunchRequest`, `EncenderVentiladorIntent`, etc.) se copian casi tal cual
de `prueba-alexa`. Lo único que cambia es que en vez de `arduino.enviar(...)` llaman a un
caso de uso. **Esa es la prueba de que la arquitectura funcionó:** el canal de voz no sabe
que existe un Arduino.

---

## 9. Riesgos técnicos y mitigación

| Riesgo | Probabilidad | Mitigación |
|---|---|---|
| El gateway pierde el puerto serie al desconectar el cable | Alta | Reconexión automática con backoff + heartbeat |
| El `loop()` del Arduino se bloquea y no detecta gas | **Crítica** | Firmware como máquina de estados con `millis()`, sin `delay()` largos |
| Alexa corta por timeout | Media | Timeout de 2,5 s + respuesta honesta |
| La URL de ngrok cambia antes de la demo | Alta | Actualizar endpoint; o dominio fijo de la cuenta |
| El grupo se pisa el código | Media | Reparto por contenedor (ver Paso 5) |
| Se intenta cubrir más CUs de los acordados | **Muy alta** | Este documento es el contrato de alcance |

---

## 10. Qué sigue

- **Paso 3:** módulos internos de `api` (dónde va cada caso de uso) y contrato de datos.
- **Paso 4:** seguridad, modo degradado y observabilidad.
- **Paso 5:** reparto por persona y milestones.
