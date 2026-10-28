# Skill de Alexa — HospedaSmart

Configuración de la **skill custom** de Alexa que recibe la voz y la manda a la API.
El código que atiende los intents vive en [`api/routers/alexa.py`](../api/routers/alexa.py);
esta carpeta solo guarda lo que se configura **a mano** en la consola de Amazon.

| Archivo | Para qué |
|---|---|
| `interaction_model.json` | Nombre de invocación, intents y frases de ejemplo. Se pega en la consola. |

## Cómo llega la voz al Arduino

```
Persona ──voz──▶ Echo Dot ──▶ Nube de Alexa (Amazon)
                                    │  HTTPS (JSON firmado)
                                    ▼
                    https://<dominio>.ngrok-free.app/alexa
                                    │  túnel ngrok
                                    ▼
          API FastAPI (puerto 8000) ── routers/alexa.py ── usecases/ (confort, acceso)
                                    │  WebSocket /ws/gateway
                                    ▼
                    Gateway (gateway/main.py) ── USB serie, 115200 baudios
                                    ▼
                    Kit Keyestudio KS0085 (firmware/sensor_diagnostics)
```

**¿Por qué ngrok?** La API corre en la laptop, detrás del router y sin IP pública, y Alexa exige
HTTPS. ngrok publica el puerto 8000 con un certificado válido. Todo es gratuito: cuenta de
desarrollador, skill en modo desarrollo (funciona en los Echo de la misma cuenta, sin publicarla)
y ngrok (el plan gratuito incluye un dominio fijo por cuenta).

## Intents

| Intent | Caso de uso | Orden al Arduino |
|---|---|---|
| `EncenderVentiladorIntent` / `ApagarVentiladorIntent` | `confort.py` (F1) | `VENT_ON` / `VENT_OFF` |
| `EncenderLuzIntent` / `ApagarLuzIntent` | `confort.py` (F1) | `LUZ_ON` / `LUZ_OFF` |
| `AbrirPuertaIntent` / `CerrarPuertaIntent` | `acceso.py` (F3, **todavía sin PIN**) | `PUERTA_ABRIR` / `PUERTA_CERRAR` |
| `AMAZON.HelpIntent`, `FallbackIntent`, `Cancel`/`Stop`/`NavigateHome` | — | — |

Para añadir un intent: frases en `interaction_model.json` → entrada en `ORDENES` de
`api/routers/alexa.py` → caso de uso en `api/usecases/` → volver a cargar el modelo en la consola.

## Configuración en la consola (una sola vez)

En [developer.amazon.com/alexa](https://developer.amazon.com/alexa/console/ask), con la **misma
cuenta de Amazon que el Echo Dot**:

| Campo | Valor |
|---|---|
| Tipo | Custom |
| Idioma | Spanish (US) — `es-US` (el Echo debe estar en ese idioma) |
| Hosting | **Provision your own** |
| Invocación | `hospeda smart` (viene en `interaction_model.json`) |

**Modelo de interacción:** *Build → Interaction Model → JSON Editor* → borrar todo → pegar
`interaction_model.json` → **Save** → **Build Model** → esperar *Build Successful*.

> La consola **no** lee este archivo sola: cada vez que cambie hay que repetir esos pasos.

**Endpoint:** *Build → Endpoint* → **HTTPS** →
- *Default Region*: `https://<dominio-ngrok>/alexa` (**con `/alexa`**; el prototipo usaba `/`).
- Certificado: *"My development endpoint is a sub-domain of a domain that has a wildcard
  certificate from a certificate authority"* → **Save Endpoints**.

**Skill ID (opcional):** copia el ID (`amzn1.ask.skill...`) a la variable `SKILL_ID` para que la API
acepte solo tu skill.

## Puesta en marcha (cada prueba)

Antes, comprueba que el hardware responde sin Alexa (niveles 1 y 2 de
[`guia-pruebas-hardware-y-simulacion.md`](../documentacion/guia-pruebas-hardware-y-simulacion.md)).
Desde la raíz del repo, con el venv activado:

```powershell
# Terminal 1 — API con verificación de firma de Amazon
$env:VERIFY_ALEXA_SIGNATURE="true"; $env:VERIFY_ALEXA_TIMESTAMP="true"; python -m api.main

# Terminal 2 — Gateway exigiendo el Arduino real
$env:SIMULACION="false"; python -m gateway.main

# Terminal 3 — Túnel (la primera vez: ngrok config add-authtoken <TOKEN>)
ngrok http 8000
```

Verifica que la URL de *Forwarding* de ngrok coincide con la del endpoint en la consola.

## Cómo probar

- **Consola → pestaña Test** (modo *Development*): `abre hospeda smart` → `enciende la luz`.
- **Echo Dot:** "Alexa, abre hospeda smart" … "enciende el ventilador", o en una sola frase:
  "Alexa, pídele a hospeda smart que encienda la luz".

| Dónde | Qué se ve si funciona |
|---|---|
| Echo / consola | "Listo, luz encendida." |
| ngrok | `POST /alexa  200 OK` |
| API | `[ALEXA-REQUEST] IntentRequest -> EncenderLuzIntent` |
| Gateway | `[SERIAL] -> Enviado a Arduino: LUZ_ON` y `[ARDUINO] OK:LUZ_ON` |

Con la firma activada, una petición hecha a mano (curl, Postman, `test_alexa_local.py`) recibe
**HTTP 400**: es lo esperado. Para probar sin el Echo, arranca la API sin esas variables.

## Problemas frecuentes

| Síntoma | Causa | Solución |
|---|---|---|
| "No tengo claro cómo puedo ayudarte con eso" y JSON Input vacío | Modelo sin compilar o invocación sin guardar | Revisar *Invocations*, **Save** y **Build** |
| Alexa habla de una TV u otro dispositivo | La sesión de la skill ya se cerró y la frase se tomó como comando general | Abrir la skill otra vez o usar "pídele a hospeda smart que…" |
| "Abre la puerta" enciende la luz | El intent no está en el modelo cargado y Alexa eligió el más parecido | Cargar `interaction_model.json` actualizado y **Build** |
| "Esa función aún no está disponible" | La API recibió un intent que no tiene en `ORDENES` | Revisar el log de la API: muestra el nombre del intent |
| "Hubo un problema con la respuesta de la skill" | ngrok cambió de URL o al endpoint le falta `/alexa` | Actualizar el endpoint |
| ngrok muestra `502` | ngrok corre pero la API no | `python -m api.main` |
| ngrok muestra `400` | Firma inválida (petición que no viene de Amazon) o reloj de la PC desfasado | Sincronizar la hora de Windows |
| "No pude comunicarme con la habitación" | Gateway caído o Arduino sin responder | Ver la terminal del gateway; probar `python -m gateway.test_serial` |
| El Echo no encuentra la skill | Idioma del Echo distinto de es-US o cuenta distinta | Revisar en la app de Alexa |

## Limitaciones conocidas

- La laptop debe estar encendida con API, gateway y ngrok. Por eso la respuesta ante gas (F2) se
  resuelve **localmente en el Arduino**, sin depender de Alexa ni de internet.
- El dominio de ngrok es fijo **por cuenta**: si otro integrante usa la suya, hay que cambiar el endpoint.
- Alexa espera la respuesta pocos segundos: la API espera el `ack` como máximo 2,5 s.
- Una skill *Custom* exige la invocación ("pídele a hospeda smart que…"). La frase corta
  "Alexa, enciende la luz" requeriría una *Smart Home skill*, fuera del alcance.
- **La puerta abre sin PIN** (igual que la prueba de concepto). El flujo F3 añadirá
  `VerificarPinIntent` y la verificación en `usecases/acceso.py`.
- Si el Arduino está ocupado en una prueba de su menú (p. ej. `S1` esperando un PIN por serie),
  no confirmará las órdenes y Alexa dirá que no pudo comunicarse.
