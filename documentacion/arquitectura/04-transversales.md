# Paso 4 — Decisiones transversales

> Las decisiones "transversales" son las que **cruzan todos los módulos**: seguridad,
> qué pasa cuando algo falla, cómo se registra lo que ocurre. Son las decisiones que
> si no se toman al principio, terminan hechas de forma diferente por cada persona del
> equipo y después es un desastre unificar.

---

## 1. Autenticación y autorización

### 1.1 Panel web (anfitrión y mantenimiento)

**Mecanismo:** usuario y contraseña simple, con sesión por cookie.

```
1. El usuario entra a /login y pone su usuario + contraseña.
2. El backend verifica contra la tabla `user` (contraseña hasheada con bcrypt).
3. Si es correcto, crea una cookie de sesión con un token firmado (JWT).
4. En cada petición, el backend lee la cookie y sabe quién es y qué rol tiene.
5. Si el token expiró (24 horas) o no existe, redirige a /login.
```

**Roles del panel:**

| Rol | Qué puede hacer | Qué NO puede hacer |
|---|---|---|
| `anfitrión` | Ver todo, crear tareas, ver alertas, gestionar reservas | — |
| `mantenimiento` | Ver alertas, ver estado de dispositivos | Crear reservas, ver datos de huéspedes |

**Datos iniciales (sembrados):** en la primera ejecución se crean automáticamente
un usuario `admin` con contraseña `admin123` y rol `anfitrión`. Es solo para la demo;
en producción se cambiaría.

### 1.2 Alexa (huéspedes y personal de limpieza)

Alexa **no tiene login**. La autenticación se hace **por lo que saben** (PIN o código
de personal), no por quiénes son en el sistema.

```
Huésped dice: "Alexa, abre la puerta" → "Dime tu PIN" → "1234"
    → El backend busca un PIN activo que coincida con esa habitación
    → Si lo encuentra y la reserva está vigente → abre

Personal dice: "Alexa, limpieza finalizada" → "Dime tu código" → "5678"
    → El backend busca un staff con ese código
    → Si lo encuentra y tiene rol "limpieza" → cierra la tarea
```

**¿Por qué no se usa account linking de Alexa?** Porque requiere OAuth 2.0 completo
y es demasiada complejidad para un proyecto de curso. Se documenta como limitación
conocida.

### 1.3 Reglas de seguridad de credenciales

| Regla | Implementación |
|---|---|
| Las contraseñas y PINs **nunca** se guardan en texto plano | Se usa `bcrypt` para hashear antes de guardar |
| Los PINs tienen fecha de inicio y fin | Campos `válido_desde` y `válido_hasta` en tabla `credential` |
| Cada intento de acceso queda registrado (exitoso o fallido) | Tabla `access_event` con `resultado = "ok"` o `"denegado"` |
| Después de 5 intentos fallidos seguidos, el PIN se bloquea | Campo `intentos_fallidos` en `credential`; se desbloquea desde el panel |
| El código del personal no expira pero se puede desactivar | Campo `activo` en tabla `staff` |

---

## 2. Manejo de errores — qué pasa cuando algo falla

La regla general es: **nunca mentir al usuario**. Si algo falló, se dice.

### 2.1 El gateway no responde (el Arduino está desconectado)

```
Situación: el huésped dice "enciende el ventilador" pero el cable USB se desconectó.

Qué pasa:
1. El caso de uso manda el comando por WebSocket.
2. No llega ack en 2,5 segundos (timeout).
3. El caso de uso NO dice "listo, ventilador encendido".
4. El caso de uso dice: "No pude confirmar la acción. Intenta de nuevo."
5. En el panel, el dispositivo se marca como "sin respuesta".
```

### 2.2 El servicio de mocks no responde

```
Situación: se necesita llamar al ECU 911 simulado pero el contenedor `mocks` está caído.

Qué pasa:
1. El adaptador intenta la llamada HTTP con timeout de 3 s.
2. Si falla, registra el error en la tabla `alert` con campo `escalada = "fallida"`.
3. El panel muestra la alerta con un ícono de "escalamiento pendiente".
4. NO se reintenta automáticamente (para la demo, basta con mostrarlo).
```

### 2.3 La base de datos no responde

```
Situación: PostgreSQL se cayó.

Qué pasa:
1. Cualquier operación que necesite la BD devuelve HTTP 500.
2. El panel muestra "Error de conexión con el sistema".
3. La seguridad local (gas) SIGUE FUNCIONANDO porque vive en el Arduino.
4. Al volver la BD, todo se recupera solo (SQLAlchemy reconecta automáticamente).
```

### 2.4 Tabla resumen de modos de fallo

| Componente caído | ¿Funciona la seguridad de gas? | ¿Funciona la voz? | ¿Funciona el panel? |
|---|---|---|---|
| Internet / ngrok | ✅ Sí | ❌ No (Alexa necesita internet) | ✅ Sí (es local) |
| Contenedor `api` | ✅ Sí | ❌ No | ❌ No |
| Contenedor `db` | ✅ Sí | ⚠️ Parcial (no puede verificar PINs) | ❌ No |
| Contenedor `mocks` | ✅ Sí | ✅ Sí | ✅ Sí (solo falla el escalamiento 911) |
| Gateway / laptop apagada | ✅ Sí | ❌ No | ⚠️ Parcial (sin datos de dispositivos) |
| Arduino desconectado | ❌ No | ⚠️ Responde "no pude confirmar" | ⚠️ Dispositivos offline |

> **El punto más importante de esta tabla:** la detección de gas y la activación de
> extractores/sirena es lo único que **siempre funciona**, porque vive en el firmware
> del Arduino. Esa es la decisión arquitectónica D1 y es lo más fuerte que el equipo
> puede defender ante los profesores.

---

## 3. Observabilidad — cómo saber qué está pasando

### 3.1 Logs (registros de texto)

Cada componente imprime un registro estructurado en la consola. No se necesita nada
sofisticado (no Elasticsearch ni Grafana): basta con `print` o `logging` de Python
y la terminal de Docker.

**Formato sugerido:**

```
[2026-10-27 15:04:05] [api] [INFO] POST /alexa → EncenderVentiladorIntent (room101)
[2026-10-27 15:04:05] [api] [INFO] Comando enviado: cmd_7f3a91 → room101.fan set_power on
[2026-10-27 15:04:06] [gateway] [INFO] Serie TX: VENT_ON
[2026-10-27 15:04:06] [gateway] [INFO] Serie RX: OK:VENT_ON
[2026-10-27 15:04:06] [api] [INFO] Ack recibido: cmd_7f3a91 ok=true (320ms)
```

**Qué se registra siempre:**
- Toda petición de Alexa (intent, habitación).
- Todo comando enviado al gateway y su resultado (ack o timeout).
- Todo evento del gateway (gas, PIR, etc.).
- Todo intento de acceso (exitoso o fallido).
- Toda alerta y su escalamiento.

### 3.2 Estado en vivo (panel del anfitrión)

El panel web muestra en tiempo real:
- Estado de cada habitación (disponible / ocupada / limpieza / mantenimiento).
- Estado de cada dispositivo (encendido / apagado / offline).
- Última lectura de sensores si hay telemetría.
- Alertas activas.

La actualización en tiempo real se hace con **HTMX + Server-Sent Events (SSE)** o
polling cada 5 segundos. Ambas opciones son válidas; HTMX es más elegante, polling
es más fácil de implementar. **Recomendación: empezar con polling e iterar.**

### 3.3 Auditoría (tabla `access_event`)

Todo acceso físico queda registrado **para siempre**. No se edita ni se borra.
Es la respuesta a "¿quién entró a la habitación 101 ayer a las 3am?".

Campos: quién (credential o staff), a qué habitación, por qué canal (voz, PIN,
panel), resultado (ok o denegado), timestamp.

---

## 4. Datos iniciales (seed data)

Para que la demo funcione desde el primer `docker compose up`, la base de datos
se carga con datos iniciales:

| Tabla | Datos sembrados |
|---|---|
| `property` | "Casa Demo" |
| `room` | "Habitación 101" (estado: disponible) |
| `device` | fan, light, lock, gas_sensor, pir, ldr (todos de room 101) |
| `user` | admin / admin123 (rol: anfitrión), maint01 / maint123 (rol: mantenimiento) |
| `staff` | "María Limpieza" (código: 5678, rol: limpieza), "Juan Mantenimiento" (código: 9012, rol: mantenimiento) |
| `reservation` | Reserva de prueba: huésped "Carlos García", check-in hoy, check-out en 3 días |
| `credential` | PIN 1234 para la reserva de Carlos, válido durante la reserva |

> Estos datos se crean con un script `seed.py` que corre una vez al iniciar. Si la
> base ya tiene datos, no hace nada (idempotente).

---

## 5. Convenciones de código (para que los 4 escriban igual)

| Tema | Convención |
|---|---|
| Idioma del código | **Inglés** para nombres de variables/funciones/clases. **Español** para mensajes al usuario y comentarios |
| Nombres de archivos | `snake_case.py` (minúsculas con guiones bajos) |
| Nombres de clases | `PascalCase` (ej: `AccessEvent`, `GatewayClient`) |
| Nombres de funciones | `snake_case` (ej: `verificar_pin()`, `crear_tarea()`) |
| Nombres de tablas en BD | `snake_case` en singular (ej: `room`, `access_event`) |
| Formato | Usar `black` (formateador automático) para no pelear por espacios |
| Commits | En español, descriptivos: "feat: agregar verificación de PIN por voz" |
| Ramas | `feature/f1-confort`, `feature/f2-emergencia`, `feature/f3-acceso`, `feature/f4-tareas` |

---

## 6. Decisiones registradas (ADR adicionales)

| # | Decisión | Alternativa descartada | Motivo |
|---|---|---|---|
| 009 | **Sesión por cookie + JWT firmado** | OAuth 2.0 / account linking de Alexa | Demasiada complejidad para proyecto de curso |
| 010 | **bcrypt para hashear contraseñas y PINs** | SHA-256, texto plano | bcrypt es el estándar; SHA-256 no tiene sal; texto plano es inaceptable |
| 011 | **Polling cada 5s para el panel** (iterar a SSE si hay tiempo) | WebSocket bidireccional | El panel solo *recibe* datos; polling es más simple y HTMX lo maneja limpio |
| 012 | **Datos sembrados con script idempotente** | Crear datos a mano en la demo | Reproducible; cualquiera puede recrear la demo desde cero |
| 013 | **Código en inglés, mensajes en español** | Todo en español o todo en inglés | El estándar de la industria; evita mezclas incómodas como `obtener_habitacion()` |
| 014 | **Bloqueo de PIN tras 5 intentos fallidos** | Sin protección contra fuerza bruta | Es una medida mínima de seguridad que demuestra que se pensó en el tema |
