# Paso 1 — Contexto y alcance

> Decisiones tomadas por el grupo:
> - Solo **Alexa es real**; las otras 5 integraciones se simulan.
> - **1 habitación física** (maqueta con el kit KS0085).
> - Backend en **FastAPI**.
> - Despliegue **Docker local** + demo en laptop.
> - Meta de la entrega: **3–4 casos de uso funcionales**.

---

## 1. Criterio de éxito

La entrega se considera lograda si en la demo se pueden mostrar **4 flujos completos** que
atraviesen todas las capas del sistema, con datos que persisten y con la seguridad local
funcionando aunque se caiga la red. No se evalúa la cantidad de casos de uso, sino que los
elegidos estén **bien resueltos de punta a punta**.

---

## 2. Actores

| Actor | Qué hace en la demo | Canal |
|---|---|---|
| **Anfitrión** | Ve el panel, crea una tarea de limpieza, recibe la alerta de gas | Web |
| **Huésped** | Pide confort por voz y abre la puerta con su PIN | Voz (Alexa) |
| **Personal de limpieza** | Se autentica con su código y cierra la tarea | Voz (Alexa) |
| **Personal de mantenimiento** | Consulta el historial de eventos y alertas | Web |
| **Sistema (edge)** | Detecta gas y actúa solo, sin intervención | Arduino |

---

## 3. Sistemas externos: real vs. simulado

| Sistema externo | En la entrega | Cómo se resuelve |
|---|---|---|
| **Alexa Voice Service** | **REAL** | Skill custom `es-US` + ngrok → FastAPI. Ya validado en `prueba-alexa` |
| Channel Manager | Simulado | Servicio `mocks` que envía un webhook de "nueva reserva" |
| Pasarela de pagos | Simulado | `mocks` responde `approved` con un código de autorización falso |
| KYC / Biometría | Simulado | `mocks` responde `approved` tras 1 s |
| Servicio meteorológico | Simulado | `mocks` devuelve temperatura/humedad fijas |
| ECU 911 | Simulado | `mocks` devuelve un código de despacho ficticio |

**Por qué simular:** el flujo arquitectónico (llamar, validar, reintentar, registrar) es
idéntico. Lo único que cambia al conectar el proveedor real es la implementación del
adaptador. Eso es precisamente lo que demuestra el patrón de adaptadores.

---

## 4. Hardware disponible

- **Kit Keyestudio KS0085** sobre Arduino UNO: servo (cerrojo), ventilador L9110, relé,
  LEDs, buzzer, LCD 1602 I2C, PIR, LDR, MQ-2, sensor de vapor, pulsador.
- **Echo Dot 5.ª gen**, idioma español (EE. UU.), misma cuenta de Amazon que la skill.
- **Laptop** que hace de servidor local y de gateway hacia el Arduino.

> El **teclado matricial** y el **módulo Bluetooth** del kit **no se usan** en la entrega.
> El PIN se dicta por voz (CU 1.6) en lugar de teclearse. Es una desviación consciente del
> documento y hay que decirla en la defensa.

---

## 5. Alcance: los 4 flujos elegidos

Se eligieron por **cobertura arquitectónica**, no por facilidad. Entre los cuatro tocan
todas las capas: voz, edge, identidad, roles, persistencia, web y eventos.

| # | Flujo | CUs | Qué capa prueba | Qué se ve en la demo |
|---|---|---|---|---|
| **F1** | **Confort por voz** | 2.3 | Canal de voz → núcleo → gateway → actuador | "Alexa, enciende el ventilador" y el ventilador gira; el panel cambia a "encendido" |
| **F2** | **Emergencia de gas** | 4.1 (+4.2 simulado) | **Edge autónomo** → evento → alerta → escalamiento | Se acerca un encendedor sin llama al MQ-2: extractor + sirena **sin pasar por la nube**; el panel muestra la alerta y se "llama" al 911 simulado |
| **F3** | **Acceso con PIN por voz** | 1.6 + 1.5 | Identidad, credenciales, autorización, auditoría | "Alexa, abre la puerta" → "Dime tu PIN" → "1234" → servo a 90°; queda registrado quién entró y a qué hora |
| **F4** | **Limpieza y panel** | 3.4 + 3.1 (3.2 mínimo) | Roles, estado compartido, web, persistencia | El anfitrión crea la tarea en el panel; limpieza dice "limpieza finalizada" + su código; la habitación pasa a *Disponible* y el panel se actualiza solo |

**CUs de soporte mínimo:** 3.2 (crear tarea desde el panel) y 1.4 (una reserva sembrada con
ventana de validez del PIN). No se demuestran como flujo propio, pero existen como datos.

**Bonus si sobra tiempo:** CU 2.2 (luz automática con PIR + LDR) — es casi gratis porque ya
está resuelto en el sketch (`S3`) y no depende del backend.

---

## 6. Fuera de alcance (decirlo explícitamente)

- 1.1 sincronización real con Airbnb/Booking · 1.2 pagos reales · 1.3 KYC real.
- 1.4 check-in/check-out como flujo completo (solo datos sembrados).
- 2.1 pre-acondicionamiento con clima real (el `mocks` existe, pero no se demuestra).
- 3.5 incidencias y 3.6 reparaciones.
- 4.2 escalamiento real al ECU 911 (solo simulado).
- Multi-propiedad real, app móvil, Bluetooth, teclado matricial.
- Autenticación de Alexa por *account linking* (fuera del alcance de una skill custom de curso).

---

## 7. Supuestos y limitaciones aceptadas

| Limitación | Impacto | Mitigación |
|---|---|---|
| La skill no sabe en qué habitación está el Echo | Hay 1 sola habitación: se fija en configuración | Documentar como limitación; la solución real es *account linking* o preguntar la habitación |
| El PIN dictado en voz alta lo escucha cualquiera | Riesgo de seguridad aceptado para la demo | Código de un solo uso y ventana de validez corta |
| La laptop debe estar encendida | Si se apaga, no hay voz ni panel | **La seguridad (F2) sigue funcionando**: vive en el Arduino |
| ngrok cambia de URL en el plan gratuito | Hay que actualizar el endpoint en la consola de Alexa | Usar dominio fijo de la cuenta o actualizar antes de cada demo |
| Alexa exige respuesta en ~8 s | Un handler lento produce "no responde" | Responder con timeout corto (2,5 s) y mensaje honesto si no hay confirmación |

---

## 8. Trazabilidad con la propuesta

| Módulo de la propuesta | Cobertura en la entrega |
|---|---|
| 1. Reservas, identidad y accesos | **Parcial**: 1.5, 1.6 funcionales; 1.4 como dato |
| 2. Confort y energía | **Parcial**: 2.3 funcional; 2.2 opcional |
| 3. Operaciones | **Parcial**: 3.1, 3.2, 3.4 funcionales |
| 4. Seguridad | **Completo en lo demostrable**: 4.1 real, 4.2 simulado |

> Para la defensa: "los 4 módulos están representados; en cada uno se profundizó un flujo
> en lugar de cubrir todos superficialmente". Es una decisión de alcance defendible.
