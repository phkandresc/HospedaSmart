# Guía de Arquitectura — HospedaSmart

> **Léeme primero.** Este documento explica toda la arquitectura del proyecto en un solo
> lugar. Está pensado para que cualquier miembro del equipo lo lea en 15 minutos y sepa
> qué estamos construyendo, cómo funciona y dónde poner su código.
>
> Si quieres más detalle, al final hay enlaces a los documentos técnicos completos.

---

## 1. ¿Qué estamos construyendo?

Un sistema de automatización de hospedajes que permite:

- **Controlar la habitación con la voz** (a través de Alexa)
- **Detectar emergencias de gas** y actuar automáticamente (sin internet)
- **Gestionar accesos con PIN** dictado por voz
- **Coordinar tareas de limpieza** entre el anfitrión y el personal

No estamos construyendo los 21 casos de uso de la propuesta. Estamos construyendo
**4 flujos completos** que demuestran que la arquitectura funciona de punta a punta.

---

## 2. Los 4 flujos que vamos a demostrar

| # | Flujo | Qué se ve en la demo |
|---|---|---|
| **F1** | Confort por voz | "Alexa, enciende el ventilador" → el ventilador gira → el panel web se actualiza |
| **F2** | Emergencia de gas | El sensor detecta gas → extractor + sirena se activan SOLOS → el panel muestra la alerta |
| **F3** | Acceso con PIN | "Alexa, abre la puerta" → "Dime tu PIN" → "1234" → el servo abre → queda registrado |
| **F4** | Limpieza y panel | El anfitrión crea tarea en el panel → limpieza dice "finalizada" por voz → el panel se actualiza |

---

## 3. El diagrama grande — cómo se conecta todo

```
                        ┌───────────────┐
                        │   Echo Dot    │ ← el huésped o personal habla aquí
                        └──────┬────────┘
                               │ voz
                        ┌──────▼────────┐
                        │  Nube Alexa   │ ← Amazon transcribe y clasifica
                        └──────┬────────┘
                               │ HTTPS + JSON (firmado)
                        ┌──────▼────────┐
                        │    ngrok      │ ← túnel para que Alexa llegue a nuestra PC
                        └──────┬────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│                         LAPTOP (demo)                               │
│                                                                     │
│   ┌──────────────────────────────────────┐    ┌──────────────────┐  │
│   │          api  (FastAPI) :8000        │    │ mocks  :9000     │  │
│   │                                      │    │                  │  │
│   │  routers/     ← recibe peticiones    │    │ Finge ser:       │  │
│   │  usecases/    ← decide qué hacer    ├───▶│ · pagos          │  │
│   │  models/      ← lee/escribe en BD   │    │ · KYC            │  │
│   │  adapters/    ← habla con exterior  │    │ · clima          │  │
│   │  templates/   ← panel web (HTML)     │    │ · ECU 911        │  │
│   │                                      │    │ · channel mgr    │  │
│   └───────┬──────────────┬───────────────┘    └──────────────────┘  │
│           │              │                                          │
│   ┌───────▼───────┐  ┌──▼───────────────────┐                      │
│   │ PostgreSQL    │  │ gateway (NATIVO)      │                      │
│   │ :5432         │  │ WebSocket ← → serie   │                      │
│   │ (las tablas)  │  └──────────┬────────────┘                      │
│   └───────────────┘             │                                   │
└─────────────────────────────────┼───────────────────────────────────┘
                                  │ USB serie (115200 baudios)
                         ┌────────▼───────────┐
                         │  Arduino UNO       │
                         │  + Kit KS0085      │
                         │                    │
                         │  · ventilador      │
                         │  · servo (cerrojo) │
                         │  · LEDs            │
                         │  · buzzer/sirena   │
                         │  · sensor MQ-2     │
                         │  · sensor PIR      │
                         │  · LCD             │
                         └────────────────────┘
```

### Los 5 componentes, explicados en una oración cada uno

| Componente | Qué hace | Dónde corre |
|---|---|---|
| **api** | Recibe órdenes (de Alexa o del panel), ejecuta la lógica, guarda datos | Docker, puerto 8000 |
| **db** | Guarda todo: reservas, dispositivos, alertas, quién entró | Docker, puerto 5432 |
| **mocks** | Finge ser los servicios externos (pagos, 911, etc.) con respuestas fijas | Docker, puerto 9000 |
| **gateway** | Traduce entre el backend (JSON por WebSocket) y el Arduino (texto por USB) | Nativo en la PC (fuera de Docker) |
| **firmware** | Ejecuta órdenes físicas y detecta emergencias de gas **sin depender de nada** | Arduino UNO |

---

## 4. La regla más importante del proyecto

> **La detección de gas y la activación de extractores/sirena funciona AUNQUE se apague
> la laptop, se caiga internet o explote todo lo demás.**
>
> Eso vive en el firmware del Arduino. No pasa por la nube ni por el backend. Es la
> decisión arquitectónica más fuerte del proyecto y lo más importante para la defensa.

---

## 5. ¿Cómo fluye una orden? (ejemplo paso a paso)

### Ejemplo: "Alexa, enciende el ventilador"

```
 1. El huésped habla al Echo Dot
 2. Amazon transcribe y reconoce: EncenderVentiladorIntent
 3. Amazon hace POST al endpoint de ngrok con un JSON firmado
 4. ngrok reenvía a localhost:8000
 5. routers/alexa.py recibe el intent
 6. Llama a usecases/confort.py → controlar_ventilador(room_id, on=True)
 7. El caso de uso llama a adapters/gateway_client.py → envía comando por WebSocket
 8. El gateway recibe el comando, escribe "VENT_ON\n" al puerto serie
 9. El Arduino lee "VENT_ON", activa el ventilador, responde "OK:VENT_ON"
10. El gateway manda el ack de vuelta por WebSocket
11. El caso de uso actualiza el estado en la BD (ventilador = encendido)
12. routers/alexa.py devuelve: "Listo, ventilador encendido"
13. Alexa lo dice en voz alta
```

**Todo eso debe ocurrir en menos de 2.5 segundos** (Alexa corta la conexión a los 8s).

---

## 6. Estructura del repositorio

```
HospedaSmart/
│
├── documentacion/                          ← 📖 todo lo que se lee, no se ejecuta
│   ├── Propuesta de Proyecto.pdf
│   ├── guia-arquitectura.md                ← ESTE ARCHIVO (léeme primero)
│   ├── guia-pruebas-hardware-y-simulacion.md ← cómo probar: simulación, Arduino, Alexa
│   ├── ANALISIS-prueba-alexa.md            ← análisis de la prueba de concepto (histórico)
│   ├── prueba-alexa-explicacion.md         ← explicación detallada del spike (histórico)
│   └── arquitectura/                       ← documentos técnicos detallados
│       ├── 00-metodo-y-drivers.md
│       ├── 01-contexto-y-alcance.md
│       ├── 02-contenedores.md
│       ├── 03-modulos-internos.md
│       ├── 04-transversales.md
│       └── 05-validacion-y-plan.md
│
├── api/                                    ← 🖥️ backend FastAPI (Docker)
│   ├── main.py                             ← arranca todo
│   ├── core/                               ← configuración, seguridad, BD
│   ├── models/                             ← tablas de la base de datos
│   ├── schemas/                            ← forma de los datos (Pydantic)
│   ├── routers/                            ← puntos de entrada (URLs)
│   ├── usecases/                           ← lógica de negocio
│   ├── adapters/                           ← conexión con servicios externos
│   ├── templates/                          ← HTML del panel (Jinja2)
│   └── static/                             ← CSS, JS, imágenes
│
├── gateway/                                ← 🔌 puente API ↔ Arduino (nativo)
│
├── mocks/                                  ← 🎭 servicios externos simulados (Docker)
│
├── firmware/                               ← 🤖 sketch del Arduino
│   └── sensor_diagnostics/                 ← banco de pruebas + órdenes remotas (OK:<orden>)
│
├── alexa/                                  ← 🗣️ interaction_model.json + guía de la consola
│
├── docker-compose.yml                      ← levanta api + db + mocks
├── .gitignore
├── LICENSE
└── README.md
```

---

## 7. ¿Dónde pongo mi código?

Esta es la pregunta más importante. La respuesta depende de **qué tipo de cosa** estás
escribiendo:

| Estoy escribiendo... | Va en... | Ejemplo |
|---|---|---|
| Algo que **recibe** una petición HTTP o WebSocket | `api/routers/` | "Alexa mandó un intent", "alguien abrió el panel" |
| Algo que **decide** qué hacer (la lógica) | `api/usecases/` | "Si el PIN es correcto Y la reserva está vigente → abrir" |
| Una **tabla** de la base de datos | `api/models/` | "La tabla de reservas tiene estos campos..." |
| La **forma** de datos que entran o salen | `api/schemas/` | "Un comando tiene id, device, action, params" |
| Algo que **habla con el exterior** | `api/adapters/` | "Llamar al mock del 911", "mandar comando al gateway" |
| **Configuración** o utilidades | `api/core/` | "URL de la BD", "cómo hashear un PIN" |
| **HTML** del panel | `api/templates/` | "La página que muestra las habitaciones" |
| Algo del **puente con el Arduino** | `gateway/` | "Leer del puerto serie y traducir a JSON" |
| Algo de los **servicios falsos** | `mocks/` | "Responder con un código de pago inventado" |
| Algo del **Arduino** | `firmware/` | "Activar el extractor cuando el MQ-2 pasa del umbral" |

### La regla de las flechas

```
routers/  →  usecases/  →  models/
                         →  adapters/
                         →  core/
```

**Las flechas solo van hacia la derecha.** Nunca al revés:
- ❌ Un modelo NO importa un router
- ❌ Un adaptador NO importa un caso de uso
- ❌ Un router NO habla directo con la BD ni con el Arduino
- ✅ Un router llama a un caso de uso, que usa modelos y adaptadores

---

## 8. Las reglas para trabajar en equipo

### Ramas de Git

Cada persona trabaja en su propia rama:

```
main                          ← solo código que funciona
├── feature/f1-confort        ← Persona A
├── feature/f2-emergencia     ← Persona B
├── feature/f3-acceso         ← Persona C
└── feature/f4-tareas         ← Persona D
```

**Se hace merge a `main` cuando un flujo funciona completo**, no antes.
Hacer merges frecuentes (al menos 1 vez por semana) para evitar conflictos grandes.

### Convenciones de código

| Tema | Convención | Ejemplo |
|---|---|---|
| Nombres de variables y funciones | Inglés, `snake_case` | `verify_pin()`, `create_task()` |
| Nombres de clases | Inglés, `PascalCase` | `AccessEvent`, `GatewayClient` |
| Mensajes al usuario | Español | `"Listo, ventilador encendido"` |
| Comentarios | Español | `# Verificar que la reserva esté vigente` |
| Nombres de archivos | `snake_case.py` | `access_event.py` |
| Commits | Español, descriptivos | `feat: agregar verificación de PIN por voz` |
| Formato de código | Usar `black` (formateador automático) | `pip install black && black .` |

### Zonas de propiedad

| Zona | Propiedad | Regla |
|---|---|---|
| `api/usecases/confort.py` | Persona A | Solo Persona A lo toca |
| `api/usecases/emergencia.py` | Persona B | Solo Persona B lo toca |
| `api/usecases/acceso.py` | Persona C | Solo Persona C lo toca |
| `api/usecases/tareas.py` | Persona D | Solo Persona D lo toca |
| `api/models/`, `api/core/` | **Compartida** | Si necesitas cambiar algo aquí, avisa al grupo primero |
| `gateway/` | Quien tome F1 o F2 | Es la persona que más interactúa con el hardware |
| `firmware/` | Quien tome F2 | Es el flujo que más depende del firmware |

---

## 9. La base de datos

Estas son las tablas. No hay que memorizarlas, pero sí saber que existen:

```
property          → una propiedad (casa/departamento)
  └── room        → una habitación (con estado: disponible/ocupada/limpieza/mantenimiento)
       ├── device      → un dispositivo (ventilador, cerrojo, sensor...)
       ├── reservation → una reserva (huésped, fechas)
       │    └── credential → un PIN (hasheado, con fecha de inicio y fin)
       ├── task         → una tarea de limpieza/mantenimiento
       ├── alert        → una alerta de emergencia
       └── access_event → un registro de quién entró/salió
staff             → personal (limpieza, mantenimiento) con código propio
user              → usuarios del panel web (anfitrión, mantenimiento) con contraseña
```

**Reglas de seguridad:**
- Los PINs y contraseñas NUNCA se guardan en texto plano (se usa bcrypt)
- Los eventos de acceso NUNCA se borran ni se editan (son la auditoría)
- Los PINs tienen fecha de vencimiento y se bloquean tras 5 intentos fallidos

---

## 10. ¿Qué pasa cuando algo falla?

| Se cae... | ¿Funciona la seguridad de gas? | ¿Funciona Alexa? | ¿Funciona el panel? |
|---|---|---|---|
| Internet / ngrok | ✅ Sí | ❌ No | ✅ Sí (es local) |
| El backend (api) | ✅ Sí | ❌ No | ❌ No |
| La base de datos | ✅ Sí | ⚠️ Parcial | ❌ No |
| Los mocks | ✅ Sí | ✅ Sí | ✅ Sí |
| La laptop entera | ✅ **SÍ** | ❌ No | ❌ No |

La fila más importante es la última: **si se apaga la laptop, la detección de gas
sigue funcionando**. Eso es lo que se demuestra en el punto 7 de la demo.

---

## 11. El plan de trabajo (resumen)

| Fase | Semanas | Qué se logra |
|---|---|---|
| **Fase 0: Cimientos** | 1–2 | Docker funciona, el skeleton de punta a punta funciona (1 orden de voz → hardware) |
| **Fase 1: Los 4 flujos** | 3–5 | Cada persona implementa su flujo completo |
| **Fase 2: Integración** | 5–6 | Se unen las ramas, se pule el panel, se prueba todo junto |
| **Fase 3: Defensa** | 6+ | Documentación final, ensayos de la demo, video de respaldo |

Para el detalle completo del plan (tareas por persona, guion de la demo, checklists),
ver `arquitectura/05-validacion-y-plan.md`.

---

## 12. Cómo levantar el sistema (cuando haya código)

```bash
# Terminal 1: levantar backend + BD + mocks
docker compose up

# Terminal 2: levantar el gateway (necesita acceso al puerto USB)
cd gateway
python main.py

# Terminal 3: levantar el túnel para Alexa
ngrok http 8000

# Arduino: flashear firmware/hospeda_smart.ino y CERRAR el Monitor Serial
```

---

## 13. Para profundizar

Estos documentos tienen todo el detalle técnico. No hace falta leerlos todos al
principio, pero están disponibles cuando se necesiten:

| Documento | Qué contiene |
|---|---|
| `guia-pruebas-hardware-y-simulacion.md` | Cómo probar el sistema hoy en simulación y mañana con hardware real |
| `arquitectura/00-metodo-y-drivers.md` | Las 7 fuerzas que condicionan el diseño |
| `arquitectura/01-contexto-y-alcance.md` | Actores, qué se simula, qué está fuera de alcance |
| `arquitectura/02-contenedores.md` | Los 5 componentes, el contrato WebSocket, los ADR |
| `arquitectura/03-modulos-internos.md` | Estructura de carpetas, cómo fluye cada caso de uso |
| `arquitectura/04-transversales.md` | Seguridad, errores, logs, datos sembrados, convenciones |
| `arquitectura/05-validacion-y-plan.md` | Walking skeleton, plan por fases, guion de la demo |
| `ANALISIS-prueba-alexa.md` | Análisis de la prueba de concepto (qué conservar y qué cambiar) |
| `prueba-alexa-explicacion.md` | Explicación detallada del código de la prueba de concepto |
