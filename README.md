# HospedaSmart 🏨💡

**Sistema de automatización global y descentralizado para la gestión integral de hospedajes.**

HospedaSmart es una plataforma que fusiona la administración logística en la nube con la ejecución física en el sitio. Permite controlar habitaciones por voz (Alexa), detectar emergencias de gas automáticamente, gestionar accesos con PIN y coordinar tareas de limpieza — todo desde una arquitectura que prioriza la seguridad local sobre la dependencia de internet.

---

## 📖 Documentación

**Empieza aquí →** [`documentacion/guia-arquitectura.md`](documentacion/guia-arquitectura.md)

La guía de arquitectura explica todo el proyecto en un solo documento: qué estamos construyendo, cómo funciona, dónde va cada cosa y cómo trabajar en equipo.

Para los documentos técnicos detallados, ver [`documentacion/arquitectura/`](documentacion/arquitectura/).

---

## 🏗️ Estructura del repositorio

```
HospedaSmart/
├── documentacion/          ← 📖 arquitectura, análisis, guías
├── api/                    ← 🖥️ backend FastAPI (Docker)
├── gateway/                ← 🔌 puente API ↔ Arduino (nativo)
├── mocks/                  ← 🎭 servicios externos simulados (Docker)
├── firmware/               ← 🤖 sketch del Arduino
├── prueba-alexa/           ← 🧪 prueba de concepto original (referencia)
├── docker-compose.yml      ← levanta api + db + mocks
└── .gitignore
```

---

## 🚀 Los 4 flujos de la demo

| # | Flujo | Qué se demuestra |
|---|---|---|
| **F1** | Confort por voz | "Alexa, enciende el ventilador" → gira → panel se actualiza |
| **F2** | Emergencia de gas | Sensor detecta gas → extractor + sirena **sin internet** |
| **F3** | Acceso con PIN | "Abre la puerta" → "Dime tu PIN" → servo abre → queda registrado |
| **F4** | Limpieza y panel | Anfitrión crea tarea → limpieza cierra por voz → panel se actualiza |

---

## 🛠️ Tecnologías

| Componente | Tecnología |
|---|---|
| Backend | Python · FastAPI · SQLAlchemy · Pydantic · Jinja2/HTMX |
| Base de datos | PostgreSQL 16 |
| Gateway | Python · pyserial · websockets |
| Hardware | Arduino UNO · Kit Keyestudio KS0085 |
| Voz | Amazon Echo Dot (5.ª gen) · Alexa Skills Kit |
| Infraestructura | Docker Compose · ngrok |

---

## 👥 Equipo

| Rol en el sistema | Descripción |
|---|---|
| **Anfitrión** | Administra propiedades, crea tareas, supervisa alertas desde el panel web |
| **Huésped** | Check-in con PIN por voz, controla confort por voz |
| **Personal de limpieza** | Cierra tareas por voz con su código de personal |
| **Personal de mantenimiento** | Consulta alertas y estado de dispositivos desde el panel |
