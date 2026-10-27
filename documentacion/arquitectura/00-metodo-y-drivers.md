# Arquitectura de HospedaSmart — Paso 0: método y fuerzas que la condicionan

> Documento de trabajo del grupo. No es todavía "la arquitectura": es el **punto de partida**
> para construirla. Los pasos siguientes se agregan en esta misma carpeta (`documentacion/arquitectura/`).

---

## 1. Qué significa "arquitectura" (versión sin humo)

Arquitectura **no** es un diagrama bonito ni elegir framework. Es el conjunto de decisiones
que son **caras de cambiar después**. En concreto, tres preguntas:

1. **¿En qué partes se divide el sistema?** (y qué responsabilidad tiene cada una)
2. **¿Cómo se hablan esas partes?** (HTTP, colas, MQTT, llamadas internas)
3. **¿Dónde vive cada cosa?** (nube, laptop, Arduino) y **¿qué pasa si esa parte se cae?**

Si una decisión es fácil de revertir (un nombre, una librería de fechas), no es arquitectura.
Si revertirla implica reescribir medio proyecto, sí lo es.

**La arquitectura se elige por lo que el sistema necesita**, no por moda. En este proyecto
lo que manda es: seguridad física real, 6 integraciones externas, varios roles y hardware
limitado. Eso descarta varias opciones por sí solo.

---

## 2. Método: 6 pasos, cada uno deja un artefacto

| Paso | Qué hacemos | Qué queda escrito |
|---|---|---|
| **0. Fuerzas** | Identificar qué exige el sistema y qué lo limita | Este documento |
| **1. Contexto** | Quién usa el sistema y con qué externos habla | Diagrama de contexto + tabla de actores |
| **2. Contenedores** | Partes desplegables: web, API, worker, gateway, base de datos | Diagrama de contenedores + responsabilidad de cada uno |
| **3. Módulos internos** | Cómo se organiza el código dentro de cada contenedor | Mapa de módulos + contrato de datos |
| **4. Transversales** | Seguridad, modo offline, errores, observabilidad | Decisiones con su justificación (ADR cortos) |
| **5. Validación** | Recorrer 2–3 casos de uso de punta a punta y ajustar | "Walking skeleton" + plan de trabajo por persona |

**Regla del proyecto de curso:** no se diseñan 21 casos de uso. Se eligen 2–3 que obliguen a
tocar todas las capas; si la arquitectura aguanta esos, aguanta el resto.

---

## 3. Fuerzas que condicionan el diseño (Paso 0)

Salen directamente de la propuesta. Cada una **obliga** a una decisión concreta.

| # | Fuerza (lo que el sistema exige) | Consecuencia arquitectónica |
|---|---|---|
| **D1** | **Seguridad crítica local.** Gas/humo debe cortarse en milisegundos (CU 4.1) | El lazo sensor → extractor → alarma se cierra **en el dispositivo**, sin depender de internet. La nube solo notifica y escala (CU 4.2) |
| **D2** | **6 integraciones externas** (channel manager, pagos, KYC, clima, ECU 911, Alexa) | Un **adaptador por integración** detrás de una interfaz propia. Ningún módulo de negocio llama HTTP directo. Los webhooks entrantes deben ser idempotentes |
| **D3** | **Varias propiedades y habitaciones** | Modelo jerárquico `Propiedad → Habitación → Dispositivo → Lectura`. Nada hardcodeado a "la habitación" |
| **D4** | **4 roles con permisos distintos** (anfitrión, huésped, limpieza, mantenimiento) | Autenticación + autorización **por rol y por recurso**. El PIN del huésped no es el código del operador |
| **D5** | **4 canales de entrada**: web, voz (Alexa), teclado matricial, Bluetooth | **Un solo núcleo de casos de uso**; los canales son adaptadores que lo llaman. Es la lección directa de `prueba-alexa` |
| **D6** | **Hardware limitado**: Arduino UNO, un puerto serie, `loop()` bloqueante | El Arduino ejecuta órdenes simples y reporta; **no** contiene reglas de negocio. Un gateway por habitación abstrae el hardware |
| **D7** | **Proyecto de curso, 4 personas, tiempo finito** | Priorización explícita y entregables incrementales. Simular lo que no se pueda integrar de verdad |

**Restricciones fijas** (no se negocian): Kit Keyestudio KS0085, Echo Dot 5.ª gen, presupuesto
≈ $0, idioma español (es-US), contexto Ecuador (ECU 911).

**Atributos de calidad**, en orden de importancia para este sistema:

1. **Seguridad** (de personas y de datos de huéspedes)
2. **Disponibilidad local** (la habitación funciona sin internet)
3. **Trazabilidad** (quién abrió qué puerta y cuándo)
4. **Latencia** baja en el lazo local; tolerante en lo administrativo
5. **Costo** casi nulo

---

## 4. Hipótesis inicial de forma (a validar en los pasos 1–2)

Esto **no es la decisión**, es el borrador contra el que discutiremos:

```
        CANALES DE ENTRADA (adaptadores, ninguno tiene lógica propia)
   ┌──────────┬───────────┬────────────────┬─────────────┐
   │ Web/App  │ Alexa     │ Teclado / PIN  │ Bluetooth   │
   └────┬─────┴─────┬─────┴───────┬────────┴──────┬──────┘
        └───────────┴─────────────┴───────────────┘
                            │  todos invocan lo mismo
                  ┌─────────▼──────────┐
                  │  NÚCLEO DE NEGOCIO │ reservas, accesos, tareas, alertas
                  └───┬────────────┬───┘
        ┌─────────────┘            └──────────────┐
  ┌─────▼──────────┐                    ┌─────────▼──────────┐
  │ Adaptadores    │                    │ Gateway de         │
  │ externos       │                    │ habitación         │
  │ pagos, KYC,    │                    │ (red, no USB)      │
  │ clima, CM, 911 │                    └─────────┬──────────┘
  └────────────────┘                              │
                                        ┌─────────▼──────────┐
                                        │ Arduino + kit      │
                                        │ seguridad local D1 │
                                        └────────────────────┘
```

La idea central: **el núcleo no sabe si la orden vino de Alexa, de la web o de un teclado**.
Ese desacople es lo que permite agregar canales sin tocar la lógica, y es exactamente lo que
`prueba-alexa` no tenía (ahí Flask, la lógica y el puerto serie vivían en un solo archivo).

---

## 5. Los 21 casos de uso, agrupados (referencia rápida)

| Módulo | Casos de uso | Naturaleza |
|---|---|---|
| 1. Reservas, identidad y accesos | 1.1 sincronizar reservas · 1.2 pagos · 1.3 KYC · 1.4 check-in/out · 1.5 acceso físico · 1.6 auth por voz | Nube + integraciones + hardware |
| 2. Confort y energía | 2.1 pre-acondicionar clima · 2.2 luz por presencia · 2.3 control por voz | Automatización + hardware |
| 3. Operaciones | 3.1 panel en vivo · 3.2 asignar tareas · 3.3 cronograma por voz · 3.4 estado de habitación · 3.5 incidencias · 3.6 reparaciones | Web + voz + datos |
| 4. Seguridad | 4.1 respuesta local · 4.2 escalar a ECU 911 | **Edge** + integración crítica |

**Candidatos a "walking skeleton"** (los que prueban toda la arquitectura):

- **CU 4.1** — obliga a resolver edge, tiempo real y desacople de la nube.
- **CU 1.5** — obliga a resolver identidad, hardware y trazabilidad.
- **CU 3.3/3.4** — obligan a resolver voz + roles + estado compartido.

---

## 6. Decisiones pendientes (bloquean el Paso 1)

1. ¿Las 6 integraciones externas se implementan o se simulan?
2. ¿Cuántas habitaciones reales vs. simuladas?
3. ¿Stack del backend definitivo?
4. ¿Dónde se despliega?
5. ¿Cuánto tiempo y cuántas horas/semana tiene el equipo?

Cuando estén respondidas, se escriben `01-contexto.md` y `02-contenedores.md`.
