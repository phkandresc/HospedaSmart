# Paso 3 — Módulos internos del backend (`api`)

> Este documento describe **cómo se organiza el código dentro del contenedor `api`**.
> No es código todavía: es el mapa de carpetas, la responsabilidad de cada módulo y
> cómo se hablan entre sí. El objetivo es que cada persona del equipo sepa dónde poner
> lo que le toca y no pise el trabajo de los demás.

---

## 1. ¿Por qué importa cómo se organiza el código?

Cuando 4 personas trabajan en el mismo programa, la primera pelea no es técnica:
es que alguien pone la lógica de "abrir puerta" en un lugar y otro la pone en otro,
y a la hora de unir todo explota.

La solución es simple: **cada tipo de cosa va en un lugar fijo**.

| Tipo de cosa | ¿Dónde va? | Ejemplo |
|---|---|---|
| Lo que recibe peticiones del exterior | `routers/` | "Alexa me mandó un intent", "alguien abrió el panel web" |
| Lo que **decide** qué hacer (la lógica) | `usecases/` | "Si el PIN es correcto Y la reserva está vigente → abrir puerta" |
| Los objetos del negocio (tablas, datos) | `models/` y `schemas/` | "¿Qué campos tiene una reserva? ¿Qué estados puede tener una habitación?" |
| Lo que habla con cosas externas | `adapters/` | "Llamar al servicio de pagos", "mandar un comando al gateway" |
| Configuración, arranque, utilidades | `core/` | "Datos de conexión a la base de datos", "cómo se hashea un PIN" |

Eso es todo. No hay más capas.

---

## 2. Estructura de carpetas propuesta

```
api/
├── main.py                    ← arranca FastAPI, registra todo
├── core/
│   ├── config.py              ← variables de entorno (DB_URL, SECRET_KEY, etc.)
│   ├── database.py            ← conexión a PostgreSQL (SQLAlchemy)
│   ├── security.py            ← hashear PINs, verificar contraseñas, crear tokens
│   └── dependencies.py        ← inyección de dependencias (get_db, get_current_user)
│
├── models/                    ← las tablas de la base de datos
│   ├── property.py            ← Property
│   ├── room.py                ← Room (con estado: disponible/ocupada/limpieza/mantenimiento)
│   ├── device.py              ← Device (ventilador, cerrojo, sensor de gas…)
│   ├── reservation.py         ← Reservation
│   ├── credential.py          ← Credential (PIN hasheado, ventana de validez)
│   ├── staff.py               ← Staff (personal con rol y código)
│   ├── user.py                ← User (usuarios del panel: anfitrión, mantenimiento)
│   ├── task.py                ← Task (tarea de limpieza/mantenimiento)
│   ├── access_event.py        ← AccessEvent (quién entró, cuándo, cómo)
│   └── alert.py               ← Alert (alerta de gas, valor, severidad, escalada)
│
├── schemas/                   ← la forma de los datos que entran y salen (Pydantic)
│   ├── room.py
│   ├── device.py
│   ├── reservation.py
│   ├── task.py
│   ├── alert.py
│   ├── auth.py                ← LoginRequest, TokenResponse
│   └── gateway.py             ← Command, Ack, Event (el contrato WebSocket)
│
├── routers/                   ← los "puntos de entrada" (cada archivo = un grupo de URLs)
│   ├── alexa.py               ← POST /alexa → recibe intents de la skill
│   ├── auth.py                ← POST /login, GET /me
│   ├── panel.py               ← GET / (dashboard), GET /rooms, etc. (Jinja + HTMX)
│   ├── rooms.py               ← CRUD de habitaciones (API JSON)
│   ├── devices.py             ← estado de dispositivos (API JSON)
│   ├── tasks.py               ← crear/cerrar tareas (API JSON)
│   ├── alerts.py              ← consultar alertas (API JSON)
│   └── ws_gateway.py          ← WebSocket /ws/gateway (conexión con el gateway)
│
├── usecases/                  ← la lógica de negocio (un archivo por flujo o grupo)
│   ├── confort.py             ← controlar_ventilador(), controlar_luz()         [F1]
│   ├── emergencia.py          ← procesar_alerta_gas(), escalar_911()            [F2]
│   ├── acceso.py              ← verificar_pin(), abrir_puerta(), registrar()    [F3]
│   └── tareas.py              ← crear_tarea(), cerrar_tarea(), cambiar_estado() [F4]
│
├── adapters/                  ← lo que habla con el mundo exterior
│   ├── gateway_client.py      ← enviar comandos por WebSocket al gateway y esperar ack
│   ├── mock_pagos.py          ← llamar al servicio simulado de pagos
│   ├── mock_kyc.py            ← llamar al servicio simulado de verificación de identidad
│   ├── mock_clima.py          ← llamar al servicio simulado de clima
│   ├── mock_911.py            ← llamar al servicio simulado de ECU 911
│   └── mock_channel.py        ← llamar al servicio simulado de channel manager
│
├── templates/                 ← HTML del panel (Jinja2)
│   ├── base.html              ← layout general (navbar, CSS, scripts)
│   ├── login.html
│   ├── dashboard.html         ← vista principal del anfitrión
│   ├── rooms.html             ← lista de habitaciones con estado en vivo
│   ├── tasks.html             ← lista de tareas pendientes
│   └── alerts.html            ← historial de alertas
│
└── static/                    ← CSS, JS, imágenes
    └── styles.css
```

> **Regla de oro:** un archivo en `routers/` **nunca** habla directo con la base de datos
> ni con el Arduino. Siempre llama a algo en `usecases/`, que a su vez usa `models/` y
> `adapters/`. Esa cadena es la que mantiene el orden.

---

## 3. Cómo se conectan las capas (para cada flujo)

### F1: Confort por voz ("enciende el ventilador")

```
routers/alexa.py                    → recibe el intent EncenderVentiladorIntent
  └── usecases/confort.py           → controlar_ventilador(room_id, on=True)
        ├── models/device.py        → busca el dispositivo room101.fan
        ├── adapters/gateway_client  → manda comando WebSocket, espera ack
        └── models/device.py        → actualiza estado en la BD
```

### F2: Emergencia de gas

```
routers/ws_gateway.py               → recibe evento {"type":"event","event":"gas_critical"}
  └── usecases/emergencia.py        → procesar_alerta_gas(room_id, valor)
        ├── models/alert.py         → guarda la alerta en la BD
        ├── adapters/mock_911.py    → llama al mock del ECU 911
        └── routers/ws_gateway.py   → empuja la alerta al panel por WebSocket (HTMX)
```

### F3: Acceso con PIN por voz

```
routers/alexa.py                    → recibe VerificarPinIntent con el slot {pin}
  └── usecases/acceso.py            → verificar_pin(room_id, pin_dictado)
        ├── models/credential.py    → busca credenciales activas + vigentes
        ├── core/security.py        → compara hash del PIN
        ├── adapters/gateway_client  → manda comando abrir cerrojo, espera ack
        └── models/access_event.py  → registra quién entró y cuándo (auditoría)
```

### F4: Limpieza y panel

```
routers/panel.py                    → anfitrión crea tarea desde el dashboard
  └── usecases/tareas.py            → crear_tarea(room_id, tipo, descripción)
        └── models/task.py          → guarda tarea con estado "pendiente"

routers/alexa.py                    → limpieza dice "limpieza finalizada" + código
  └── usecases/tareas.py            → cerrar_tarea(room_id, código_staff)
        ├── models/staff.py         → verifica código del personal
        ├── models/task.py          → marca tarea como "completada"
        ├── models/room.py          → cambia estado de habitación a "disponible"
        └── routers/ws_gateway.py   → empuja actualización al panel (HTMX)
```

---

## 4. Reglas para evitar problemas cuando trabajan en paralelo

| Regla | Por qué |
|---|---|
| **Cada persona trabaja en un flujo distinto** (F1, F2, F3, F4) | Así cada quien toca archivos diferentes la mayor parte del tiempo |
| Los archivos **compartidos** (`models/`, `core/`) se definen al inicio y se tocan poco | Son el "contrato" entre todos; si alguien necesita un campo nuevo, lo dice al grupo |
| Los `usecases/` **nunca** se importan entre sí | Si confort necesita algo de acceso, se saca a una función compartida en `core/` |
| Los `adapters/` devuelven datos simples (diccionarios, True/False) | No devuelven objetos de SQLAlchemy ni de Pydantic: eso acopla capas |
| Los `routers/` solo validan formato y llaman a `usecases/` | Si alguien mete un `if` de negocio en un router, hay que moverlo |

---

## 5. Organización del servicio `mocks`

El servicio `mocks` es mucho más simple: **solo finge respuestas**.

```
mocks/
├── main.py              ← arranca FastAPI en :9000
├── pagos.py             ← POST /pagos/cobrar → {"ok": true, "auth_code": "FAKE-001"}
├── kyc.py               ← POST /kyc/verificar → {"ok": true} (con delay de 1s)
├── clima.py             ← GET  /clima?lat=...  → {"temp_c": 28, "humidity": 65}
├── ecu911.py            ← POST /911/despacho   → {"ok": true, "dispatch_id": "D-999"}
└── channel_manager.py   ← POST /channel/sync   → {"reservations": [...]}
```

No hay lógica, no hay base de datos: un `return` con datos fijos. El valor de este
servicio es que al borrarlo (o reemplazarlo con el proveedor real), **nada más cambia**.
Solo se modifica el adaptador correspondiente en `api/adapters/`.

---

## 6. Organización del `gateway`

El gateway también es un programa simple. Corre **fuera de Docker** (acceso al puerto serie).

```
gateway/
├── main.py              ← abre WebSocket hacia ws://localhost:8000/ws/gateway
│                           abre puerto serie hacia el Arduino
│                           traduce entre los dos mundos
├── serial_bridge.py     ← leer/escribir al puerto serie con reconexión
├── protocol.py          ← traducir "VENT_ON\n" ↔ {"type":"command","action":"set_power"}
└── requirements.txt     ← websockets, pyserial
```

---

## 7. Qué NO se define aquí (y está bien)

- **Cómo se ve el panel** (eso es diseño visual, no arquitectura — se resuelve con templates HTML y CSS).
- **Los queries SQL exactos** (se resuelven al codificar; SQLAlchemy los genera).
- **Los nombres exactos de funciones** (estos son orientativos; pueden cambiar al implementar).

Lo que sí queda fijo y **no debería cambiar** es:
- La estructura de carpetas.
- La regla de que `routers → usecases → models/adapters` (nunca al revés).
- El contrato WebSocket del Paso 2.
- Las tablas de la base de datos del Paso 2.
