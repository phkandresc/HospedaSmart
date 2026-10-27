# Paso 5 — Validación y plan de trabajo

> Último paso de la arquitectura. Aquí se verifica que el diseño funciona recorriendo
> los flujos de punta a punta, y se define **quién hace qué y en qué orden**.
>
> **Contexto del equipo:** 4 personas, primera vez con un proyecto así, más de 6 semanas
> hasta la entrega.

---

## 1. Walking skeleton — la prueba de que la arquitectura funciona

Un "walking skeleton" es la versión más simple posible del sistema donde **todas las
capas están conectadas**, aunque no hagan casi nada útil todavía. Es como el esqueleto
de un edificio: no tiene paredes ni pintura, pero ya se ve la estructura.

### ¿Qué se demuestra con el skeleton?

```
Echo Dot → Alexa nube → ngrok → FastAPI → WebSocket → gateway → serie → Arduino → servo gira
                                    ↕
                              PostgreSQL (guarda el evento)
                                    ↕
                              Panel web (muestra el cambio)
```

Si esa cadena funciona de punta a punta (aunque sea con un solo comando "enciende el
ventilador"), la arquitectura está validada. Todo lo demás es agregar casos de uso
siguiendo el mismo patrón.

### Criterio de éxito del skeleton

- [ ] `docker compose up` levanta `api`, `db` y `mocks` sin errores.
- [ ] El panel web carga en `http://localhost:8000` y muestra la habitación 101.
- [ ] `python gateway/main.py` se conecta al WebSocket y al puerto serie.
- [ ] "Alexa, pídele a hospeda smart que encienda el ventilador" → el ventilador gira.
- [ ] El panel muestra que el ventilador cambió a "encendido".
- [ ] El log del `api` muestra la cadena completa (intent → comando → ack).

**Tiempo estimado para el skeleton: 1 a 2 semanas** (entre los 4, trabajando en paralelo
según las fases del plan).

---

## 2. Plan por fases

El plan tiene **4 fases**. Cada fase tiene un entregable claro. No se avanza a la
siguiente fase hasta que la anterior funcione. Esto evita construir sobre cosas rotas.

### Fase 0: Cimientos (Semana 1–2)

**Objetivo:** que todo esté instalado, configurado y el skeleton funcione.

| Tarea | Quién | Depende de | Resultado |
|---|---|---|---|
| Crear el repositorio con `.gitignore`, limpiar `prueba-alexa/` | Cualquiera | — | Repo limpio |
| Escribir `docker-compose.yml` (api + db + mocks vacíos) | Persona A | — | `docker compose up` funciona |
| Crear estructura de carpetas de `api/` (vacía, solo `main.py` que diga "hola") | Persona A | — | `localhost:8000` responde |
| Configurar SQLAlchemy + crear modelos básicos (`room`, `device`) | Persona B | Docker funcione | Las tablas existen en PostgreSQL |
| Escribir el script `seed.py` con datos iniciales | Persona B | Modelos | La BD tiene datos de prueba |
| Migrar el gateway desde `prueba-alexa` a la estructura nueva (`gateway/`) | Persona C | — | `gateway/main.py` se conecta al WebSocket y al serie |
| Migrar los handlers de Alexa a `routers/alexa.py` (solo EncenderVentilador) | Persona D | API funcione | Un intent funciona de punta a punta |
| Verificar el skeleton completo | **Todos** | Todo lo anterior | ✅ Checklist del skeleton |

**Entregable de la Fase 0:** la demo del skeleton — una sola orden de voz que enciende
el ventilador, queda registrada en la BD y se ve en el panel (aunque sea feo).

---

### Fase 1: Los 4 flujos (Semana 3–5)

**Objetivo:** implementar los 4 flujos completos. Cada persona toma un flujo.

| Persona | Flujo | Qué implementa | Archivos principales |
|---|---|---|---|
| **Persona A** | **F1: Confort por voz** | Intents de ventilador + luz, caso de uso `confort.py`, actualización del panel | `routers/alexa.py` (intents), `usecases/confort.py`, `schemas/device.py` |
| **Persona B** | **F2: Emergencia de gas** | Evento del gateway, caso de uso `emergencia.py`, alerta en panel, mock del 911 | `routers/ws_gateway.py`, `usecases/emergencia.py`, `adapters/mock_911.py`, `models/alert.py` |
| **Persona C** | **F3: Acceso con PIN** | Intent de verificación, caso de uso `acceso.py`, hash de PIN, auditoría | `routers/alexa.py` (intent PIN), `usecases/acceso.py`, `models/credential.py`, `core/security.py` |
| **Persona D** | **F4: Limpieza y panel** | CRUD de tareas en panel, intent de cierre por voz, cambio de estado de habitación | `routers/panel.py`, `routers/tasks.py`, `usecases/tareas.py`, `templates/` |

**Regla importante:** si alguien necesita modificar un archivo que "pertenece" a otro
flujo (por ejemplo, los modelos), lo comunica al grupo antes. Los `models/` y `core/`
son zona compartida.

**Coordinación sugerida:**
- Reunión corta al inicio de cada semana (15 min): "¿qué hice?, ¿qué voy a hacer?, ¿estoy trabado?"
- Cada persona trabaja en su rama (`feature/f1-confort`, etc.).
- Se hacen merge a `main` cuando un flujo funciona completo, no antes.

**Entregable de la Fase 1:** los 4 flujos funcionan por separado. Se pueden demostrar
uno por uno.

---

### Fase 2: Integración y pulido (Semana 5–6)

**Objetivo:** que todo funcione junto y se vea profesional para la demo.

| Tarea | Quién | Prioridad |
|---|---|---|
| Unir las 4 ramas en `main` y resolver conflictos | **Todos** | 🔴 Crítica |
| Prueba integral: correr los 4 flujos seguidos sin reiniciar | **Todos** | 🔴 Crítica |
| Pulir el panel: que se vea decente (CSS básico, layout claro) | Persona D | 🟡 Alta |
| Agregar login al panel (usuario/contraseña) | Persona C | 🟡 Alta |
| Agregar el bonus CU 2.2 (luz automática con PIR + LDR) si sobra tiempo | Persona A | 🟢 Opcional |
| Verificar que la seguridad de gas funciona con la laptop apagada | Persona B | 🔴 Crítica |
| Escribir README actualizado con instrucciones de instalación | Cualquiera | 🟡 Alta |

**Entregable de la Fase 2:** demo completa funcionando.

---

### Fase 3: Documentación y defensa (Semana 6+)

**Objetivo:** preparar la defensa del proyecto.

| Tarea | Quién |
|---|---|
| Diagrama de arquitectura final (actualizar si cambió algo) | Persona A + B |
| Preparar guion de la demo (qué se muestra, en qué orden) | **Todos** |
| Documentar las limitaciones y decisiones de alcance | Persona C + D |
| Ensayar la demo al menos 2 veces | **Todos** |
| Tener un plan B si el ngrok falla (video grabado de respaldo) | Cualquiera |

---

## 3. Guion sugerido para la demo (orden de los flujos)

El orden importa porque algunos flujos dejan el sistema en el estado correcto para
el siguiente:

```
1. ARRANQUE
   - Mostrar que todo empieza con `docker compose up` + `python gateway/main.py` + `ngrok http 8000`
   - Mostrar el panel: habitación 101, estado "disponible", dispositivos "apagados"

2. F4 → CREAR TAREA (panel)
   - El anfitrión crea una tarea de limpieza desde el panel
   - La habitación pasa a estado "limpieza"

3. F4 → CERRAR TAREA (voz)
   - "Alexa, pídele a hospeda smart que la limpieza está finalizada"
   - "Dime tu código" → "5678"
   - La tarea se cierra, la habitación vuelve a "disponible"
   - El panel se actualiza en vivo

4. F3 → ACCESO CON PIN (voz)
   - "Alexa, pídele a hospeda smart que abra la puerta"
   - "Dime tu PIN" → "1234"
   - El servo gira (la puerta se abre). Se cierra sola en 5s.
   - Mostrar en el panel: evento de acceso registrado con nombre y hora

5. F1 → CONFORT (voz)
   - "Alexa, pídele a hospeda smart que encienda el ventilador"
   - El ventilador gira. El panel muestra "encendido".
   - "Alexa, pídele a hospeda smart que encienda la luz"
   - El LED se enciende. El panel muestra "encendida".

6. F2 → EMERGENCIA DE GAS (hardware)
   - Acercar un encendedor (sin llama) al sensor MQ-2
   - INMEDIATAMENTE: extractor + sirena + LED estroboscópico (SIN pasar por la laptop)
   - DESPUÉS (1-2 segundos): el panel muestra la alerta roja
   - Mostrar el log: "escalamiento al ECU 911 simulado"

7. PRUEBA DE RESILIENCIA (bonus para la defensa)
   - Desconectar el cable de red / cerrar ngrok
   - Repetir el paso 6: la emergencia SIGUE funcionando
   - "Esto demuestra que la seguridad no depende de la nube"
```

---

## 4. Riesgos del plan y contingencias

| Riesgo | Probabilidad | Contingencia |
|---|---|---|
| Una persona se traba con su flujo | Alta | Los otros ayudan; el skeleton ya prueba que la arquitectura funciona |
| El merge de las 4 ramas genera conflictos | Alta | Hacer merges frecuentes (no esperar a la Fase 2); los modelos son la zona de conflicto principal |
| No da tiempo para los 4 flujos | Media | F2 (gas) y F1 (confort) son los más rápidos; F3 (PIN) y F4 (tareas) son los más complejos. Priorizar F2 + F1 + F3, dejar F4 como mínimo viable |
| El hardware falla el día de la demo | Baja | Tener video grabado de respaldo |
| Alguien del equipo desaparece | Media | Cada flujo es independiente; el resto se puede entregar |

---

## 5. Checklist final antes de la defensa

- [ ] `docker compose up` funciona en la laptop de la demo (probado el día anterior)
- [ ] El Arduino tiene el firmware correcto flasheado
- [ ] ngrok está corriendo y el endpoint está actualizado en la consola de Alexa
- [ ] Los datos sembrados están cargados (PIN 1234, código limpieza 5678, reserva activa)
- [ ] Los 4 flujos funcionan seguidos sin reiniciar nada
- [ ] La emergencia de gas funciona con la laptop apagada
- [ ] El guion de la demo está impreso (no depender de la memoria)
- [ ] Hay un video de respaldo por si algo falla en vivo
