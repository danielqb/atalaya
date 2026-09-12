# Plan De Fases De Construccion

Este documento describe como construir Atalaya durante la ventana de hackathon y que debe quedar demostrable en cada fase.

## Principio Rector

El proyecto gana si demuestra un bucle tactico completo y confiable, no si intenta cubrir toda la vision multiagente.

El camino critico es:

```text
CoT event -> listener -> normalizer -> geo engine -> LLM tactical brief -> dashboard
```

Todo lo que no fortalezca ese bucle queda como extra.

## Fase 0: Infraestructura Base Reusada

Estado: preexistente.

Objetivo: dejar claro que OpenTAKServer y el Helm Chart son infraestructura, no el entregable principal del hackathon.

Se usa:

- OpenTAKServer como fuente o destino de eventos.
- Helm Chart como base de despliegue.
- Endpoint local `/api/cot` como fallback de demo.

Criterio de salida:

- La submission explica que lo construido durante el evento es el agente Atalaya.
- La demo puede correr aunque OpenTAKServer falle, usando simulacion local.

## Fase 1: Listener Y Normalizador

Tiempo estimado: 45 minutos.

Objetivo: recibir eventos CoT o JSON compatible y convertirlos en un objeto interno estable.

Entregables:

- Endpoint `POST /api/cot`.
- Listener para consumir OpenTAKServer cuando este disponible.
- Modelo `TacticalEvent`.
- Validacion minima de `uid`, `type`, `callsign`, `lat`, `lon`, `time` y `detail`.
- Store en memoria para eventos procesados.

Criterio de salida:

- Un evento simulado aparece en logs o en una respuesta API.
- Un evento mal formado se rechaza con error claro.
- No se rompe el flujo si llega un tipo desconocido.

## Fase 2: Motor Geo Y Aviso Tactico

Tiempo estimado: 45 minutos.

Objetivo: calcular distancia y rumbo desde el puesto de comando, y convertir el evento en lenguaje tactico.

Entregables:

- Funcion `haversine_distance_m`.
- Funcion `bearing_degrees`.
- Funcion `bearing_to_cardinal_es`.
- Prompt de aviso tactico.
- Llamada a OpenAI u OpenRouter.
- Fallback deterministico si el LLM falla.

Criterio de salida:

- Cada evento aceptado muestra distancia en metros.
- Cada evento aceptado muestra direccion relativa en espanol.
- El LLM devuelve maximo dos frases accionables.
- El fallback produce un aviso usable sin modelo.

## Fase 3: Dashboard Del Coordinador

Tiempo estimado: 45 minutos.

Objetivo: dar al coordinador una vista operacional minima del feed en vivo.

Entregables:

- Feed de eventos.
- Panel de alerta seleccionada.
- Estado del listener.
- Boton para simular eventos.
- UI generativa con CopilotKit.

Criterio de salida:

- El usuario puede enviar eventos simulados desde la UI.
- La alerta aparece sin refrescar manualmente o con polling simple.
- Las prioridades se distinguen visualmente.
- El copiloto puede resumir el feed activo.

## Fase 4: Resiliencia Con Trigger.dev

Tiempo estimado: 30 minutos.

Objetivo: demostrar que el listener esta pensado como proceso operacional, no como script fragil.

Entregables:

- Job `listen-cot-events`.
- Reintentos ante error de red.
- Logs de eventos procesados.
- Manejo de desconexion.

Criterio de salida:

- El job puede iniciarse y registrar actividad.
- Si falla la fuente, reintenta o pasa a fallback local.
- La demo no depende de mantener una terminal manual perfecta.

## Fase 5: Acceso Con Auth0

Tiempo estimado: 30 minutos.

Objetivo: proteger el dashboard, porque los eventos de rescate no deben ser publicos.

Entregables:

- Login.
- Logout.
- Ruta de dashboard protegida.
- Usuario autenticado visible.

Criterio de salida:

- Un usuario no autenticado no entra al dashboard.
- Un usuario autenticado ve el feed.
- Existe variable de entorno para desactivar auth durante contingencia de demo.

## Fase 6: Demo Y Pulido

Tiempo estimado: 60 minutos.

Objetivo: preparar una demostracion repetible, breve y robusta.

Entregables:

- Eventos simulados CASEVAC, FINDING, HAZARD y CHAT.
- Guion de demo de 2 a 3 minutos.
- Fallbacks probados.
- README/submission con mensaje de elegibilidad.

Criterio de salida:

- La demo funciona con un solo comando o con pasos muy claros.
- El video muestra el bucle completo.
- El pitch explica por que esto ayuda en una emergencia real.

## Eventos Que Deben Verse En La Demo

### CASEVAC

Valor demostrado: urgencia medica y accion inmediata.

Aviso esperado:

```text
Alpha-2 reporta CASEVAC a 830 metros al noreste. Prioridad alta: coordinar extraccion medica y confirmar ruta segura.
```

### FINDING

Valor demostrado: hallazgo relevante sin sobrerreaccion.

Aviso esperado:

```text
Bravo-1 localiza una persona consciente con movilidad limitada a distancia media. Prioridad media: enviar evaluacion y mantener comunicacion.
```

### HAZARD

Valor demostrado: proteccion de equipos en campo.

Aviso esperado:

```text
Charlie-3 reporta cable electrico caido bloqueando la ruta principal. Prioridad critica: aislar el area y redirigir unidades.
```

### CHAT

Valor demostrado: ruido controlado.

Aviso esperado:

```text
Evento de baja prioridad registrado; no interrumpe el feed tactico principal.
```

## Orden De Implementacion Recomendado

1. Backend con `/api/cot`.
2. Simulador local.
3. Calculo geo.
4. Generador tactico con fallback.
5. Dashboard.
6. CopilotKit.
7. Trigger.dev.
8. Auth0.
9. Video y submission.

## Riesgos Y Mitigaciones

| Riesgo | Mitigacion |
|---|---|
| TAK no responde en demo | Usar simulador local contra `/api/cot` |
| LLM lento o caido | Usar template fallback |
| Auth0 consume demasiado tiempo | Activar `DEMO_AUTH_ENABLED=false` |
| Trigger.dev no queda desplegado | Dejar job implementado y ejecutar listener local |
| UI generativa se complica | Mantener feed y panel tactico como demo principal |

## Definicion De Listo

Atalaya esta listo para entregar si:

- Un evento entra por API o TAK.
- El sistema calcula distancia y rumbo.
- El aviso tactico se genera con LLM o fallback.
- El dashboard muestra el evento y la prioridad.
- El operador puede entender que hacer sin leer payloads tecnicos.
- El repositorio explica que la infraestructura TAK es base reusada y el agente fue construido durante el evento.
