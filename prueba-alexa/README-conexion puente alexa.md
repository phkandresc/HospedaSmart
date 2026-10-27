# Conexión Alexa ↔ Backend local — HospedaSmart

Este documento explica cómo está conectada la **skill propia de Alexa** con el **backend en Python** que corre en la PC del grupo. Es parte de la prueba de factibilidad del canal de voz de HospedaSmart (casos de uso CU-06, CU-07 y CU-13).

> **Estado:** hitos 1 y 2 completados y grabados (la voz llega al backend en la PC). El hito 3 (backend → Kit Keyestudio por USB serie) está en desarrollo.

---

## 1. Arquitectura

```
Persona ──voz──▶ Echo Dot ──▶ Nube de Alexa (Amazon)
                                    │  HTTPS (JSON)
                                    ▼
                    https://<dominio>.ngrok-free.dev
                                    │  túnel ngrok
                                    ▼
                    PC con Windows: servidor Python (puerto 5000)
                                    │  USB serie, 9600 baudios (hito 3)
                                    ▼
                    Kit Keyestudio KS0085 (Arduino UNO)
```

| Componente | Qué hace | Quién lo controla |
|---|---|---|
| Echo Dot (3.ª gen.) | Capta la voz y reproduce la respuesta | Amazon |
| Nube de Alexa | Convierte la voz en una **intención** (*intent*) y la envía al endpoint | Amazon |
| Skill "HospedaSmart Local" | Define el nombre de invocación, los intents y las frases de ejemplo | Grupo (consola de Alexa) |
| ngrok | Publica el puerto 5000 de la PC en una dirección HTTPS pública | Grupo (cuenta gratuita) |
| Servidor Python (`app.py`) | Recibe el intent, decide qué hacer y responde lo que Alexa dirá | Grupo |
| Kit Keyestudio | Ejecuta la orden física (LED, servo, etc.) | Grupo (sketch de Arduino) |

**¿Por qué ngrok?** El servidor corre en `127.0.0.1:5000`, que solo existe dentro de la PC. La nube de Alexa no puede llegar ahí porque la PC está detrás del router, no tiene IP pública y Alexa exige HTTPS. ngrok crea una dirección pública con certificado válido y reenvía las solicitudes al puerto local.

---

## 2. Costo

Todo es **gratuito**:

- Cuenta de desarrollador de Amazon y consola de Alexa.
- Skill en **modo desarrollo**: no se publica ni pasa certificación; funciona en cualquier Echo vinculado a la misma cuenta de Amazon con la que se creó.
- ngrok, plan gratuito (incluye un dominio fijo por cuenta).

---

## 3. Requisitos

- PC con Windows, Python 3 (con *Add Python to PATH*).
- Cuenta de Amazon **igual** a la del Echo Dot.
- Echo Dot con idioma **Español (Estados Unidos)**.
- Cuenta gratuita en [ngrok.com](https://ngrok.com) y ngrok instalado (Microsoft Store, `winget install ngrok.ngrok` o ZIP).
- Arduino IDE (para el hito 3).

---

## 4. Configuración de la skill (consola de Alexa)

Se hace una sola vez en [developer.amazon.com/alexa](https://developer.amazon.com/alexa), con la misma cuenta del Echo.

| Campo | Valor |
|---|---|
| Nombre de la skill | `HospedaSmart Local` |
| Idioma (*locale*) | Spanish (US) — `es-US` |
| Tipo | Custom |
| Hosting | **Provision your own** (hosting propio) |
| Nombre de invocación | `casa smart` |

**Modelo de interacción:** está versionado en `interaction_model.json`. Para cargarlo:

1. **Build → Interaction Model → JSON Editor** (con Spanish (US) seleccionado).
2. Borrar el contenido, pegar el de `interaction_model.json`.
3. **Save** → **Build Model** → esperar *Build Successful*.

> Cada vez que se cambie `interaction_model.json` hay que repetir estos tres pasos; la consola **no** lee el archivo del repo por sí sola.

**Endpoint:** **Build → Endpoint**

1. Tipo: **HTTPS**.
2. *Default Region*: `https://<dominio>.ngrok-free.dev` (el que muestra ngrok en *Forwarding*; con o sin `/` final funciona, porque el servidor escucha en la ruta raíz `/`).
3. Certificado: **"My development endpoint is a sub-domain of a domain that has a wildcard certificate from a certificate authority"**.
4. **Save Endpoints**.

---

## 5. Backend (servidor Python)

**Tecnologías:** Flask + `ask-sdk-core` + `flask-ask-sdk` (SDK oficial de Alexa para Python). La verificación de firma y *timestamp* de las solicitudes de Alexa está **activada**: el servidor rechaza solicitudes que no vengan de Amazon.

**Archivos principales**

| Archivo | Para qué |
|---|---|
| `app.py` | Servidor Flask y *handlers* de la skill |
| `requirements.txt` | Dependencias de Python |
| `interaction_model.json` | Copia versionada del modelo de interacción de la consola |

**Handlers**

| Solicitud / intent | Qué hace |
|---|---|
| `LaunchRequest` | Saluda ("Hola, soy HospedaSmart…") y deja la sesión abierta |
| `EncenderLuzIntent` | Responde "Listo, luz encendida" e imprime `[ORDEN] Encender luz` |
| Intent de la puerta | Responde a "abre la puerta" (ver nombre exacto en `interaction_model.json`) |
| `AMAZON.HelpIntent`, `CancelIntent`, `StopIntent` | Ayuda y cierre |
| `SessionEndedRequest` | Fin de sesión |
| Manejador de excepciones | Responde en español si algo falla |

**Instalación (primera vez)**

```powershell
cd <carpeta-del-proyecto>
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
ngrok config add-authtoken <TU_TOKEN>
```

---

## 6. Puesta en marcha (cada prueba)

Se necesitan **dos ventanas de PowerShell abiertas a la vez**.

**Ventana 1 — servidor**
```powershell
cd <carpeta-del-proyecto>
.\venv\Scripts\Activate.ps1
python app.py
```
Debe mostrar que escucha en `http://127.0.0.1:5000`.

**Ventana 2 — túnel**
```powershell
ngrok http 5000
```
Verificar que la línea *Forwarding* coincida con la URL configurada en **Build → Endpoint**.

**Para detener:** `Ctrl + C` en cada ventana. En la consola de Alexa no hay que hacer nada.

---

## 7. Cómo probar

**En la consola (pestaña Test, modo *Development*):**
`abre casa smart` → `enciende la luz`

**En el Echo Dot:**
- "Alexa, abre casa smart" … "enciende la luz"
- En una sola frase: "Alexa, pídele a casa smart que encienda la luz"

**Señales de que funciona**

| Dónde | Qué se ve |
|---|---|
| Echo / consola | La respuesta hablada del servidor |
| Ventana de ngrok | `POST /   200 OK` |
| Ventana del servidor | `[ORDEN] Encender luz` |

---

## 8. Problemas frecuentes

| Síntoma | Causa | Solución |
|---|---|---|
| "No tengo claro cómo puedo ayudarte con eso" y JSON Input vacío | El modelo no está compilado o el nombre de invocación no se guardó | Revisar *Invocations*, **Save** y **Build** |
| Alexa habla de una TV u otro dispositivo | La sesión de la skill ya se cerró y Alexa tomó la frase como comando general de casa inteligente | Abrir la skill de nuevo o usar "pídele a casa smart que…" |
| "Abre la puerta" enciende la luz | El intent no existía y Alexa eligió el más parecido | Cargar el `interaction_model.json` actualizado y hacer **Build** |
| La frase de una sola vez no funciona | Falta la forma en subjuntivo | Agregar frases como `que encienda la luz` al intent |
| El Echo no encuentra la skill | Idioma del Echo distinto de es-US o cuenta distinta | Revisar en la app de Alexa |
| La skill "no responde" | El servidor o ngrok no están corriendo | Levantar las dos ventanas |
| ngrok muestra `502` | ngrok corre pero el servidor no | Ejecutar `python app.py` |
| Error de puerto en uso | Otro servidor (p. ej. uno dejado en segundo plano) ocupa el 5000 | Cerrarlo y volver a arrancar |

---

## 9. Limitaciones conocidas

- La PC debe estar **encendida** con el servidor y ngrok corriendo. Por eso la respuesta ante gas (CU-16) se resuelve **localmente en el Kit**, sin depender de Alexa ni de internet.
- El dominio de ngrok es fijo **por cuenta**: si otro integrante usa su propia cuenta, hay que actualizar el endpoint en la consola.
- Alexa espera la respuesta solo unos segundos: los *handlers* deben enviar la orden y responder de inmediato.
- Una skill *Custom* exige la invocación ("pídele a casa smart que…"). La frase corta "Alexa, enciende la luz" requeriría una *Smart Home skill*, fuera del alcance.
- Decir un código de empleado en voz alta lo escucha cualquiera cerca (limitación aceptada para la demo).
- El prototipo usa la invocación `casa smart`; el documento del proyecto define `hospeda smart` para la versión final.

---

