# Monkyfi SDI — Revisión del PRD y plan de construcción por fases

Nov 9, 2026 · @Dante Ruiz

## Resumen ejecutivo

El PRD (Product Requirements Document, documento de requisitos de producto) está listo para construir, con tres ajustes antes de empezar: reducir el MVP (Minimum Viable Product, producto mínimo viable), definir los esquemas de datos y resolver de dónde salen los datos de prueba sin un carrier piloto.

Su mayor fortaleza es el control: separa fechas solicitadas, estimadas y comprometidas, exige evidencia por dato y bloquea la liberación ante una sola filtración o fecha inventada. Su mayor riesgo no es técnico: las fases A y B del despliegue dependen de 100 órdenes históricas de un carrier que hoy Monkyfi no tiene.

Recomendación: construir en 9 fases (0 a 8), cada una cerrada con `/hand-off` y abierta con `/prime`, usando un dataset sintético claramente etiquetado. Con eso se obtiene una demo funcional para conseguir un carrier socio de diseño (design partner), y las fases A a E del PRD se ejecutan después, ya con datos reales.

## Fortalezas del PRD

Estas partes se pasan casi sin cambios al `docs/SPEC.md`:

- **Honestidad del alcance.** Dice explícitamente que es una propuesta, no un agente desplegado ni resultados demostrados. Esto protege la credibilidad de Monkyfi frente a un carrier.
- **Puertas de control G0–G5 con autoridad humana.** El agente recomienda; el humano decide. Los overrides quedan registrados sin borrar la discrepancia.
- **Validadores determinísticos + modelo para extraer y redactar.** Es la arquitectura correcta: las reglas críticas no dependen del LLM (Large Language Model, modelo de lenguaje grande).
- **Estados de dato distintos** (faltante, no aplicable, contradictorio, vencido) y jerarquía de fuentes por campo.
- **Evals con umbrales y casos obligatorios**, incluyendo inyección de instrucciones dentro de PDFs y segregación por cliente.
- **Métricas con definición, fórmula y advertencias** sobre mezcla de órdenes y tamaño de muestra.
- **Despliegue gradual** (offline → shadow mode → piloto supervisado), que es como un carrier acepta probar algo nuevo.

## Mejoras recomendadas al PRD

Once mejoras, ordenadas por impacto en la construcción. Las cuatro primeras conviene resolverlas en la Fase 0, antes de escribir código.

| # | Prioridad | Hallazgo | Cambio propuesto |
| --- | --- | --- | --- |
| 1 | Alta | **No hay plan de datos sin carrier.** Los evals (sección 11) piden 100 órdenes históricas anonimizadas; Monkyfi no tiene acceso a ellas hoy. | Agregar una "Fase pre-A": dataset sintético de 30–40 órdenes con etiquetas, cubriendo los 16 casos obligatorios, marcado como sintético. Umbrales sobre datos sintéticos = señal de desarrollo, no prueba de producción. |
| 2 | Alta | **MVP demasiado amplio para un equipo de una persona.** Seis casos P0 (UC02–UC06 y UC08). | P0 de construcción: UC02, UC03, UC04 y UC06. Pasar UC05 y UC08 a P0 del piloto (se construyen en fases 4 y 6, pero no bloquean la demo). |
| 3 | Alta | **Falta el esquema de datos.** Sección 7 lista entidades, pero los validadores determinísticos necesitan estructura exacta. | Anexo con JSON Schema (formato estándar para describir datos JSON) de orden, versión, valor-con-fuente, hallazgo, hito, dependencia, comunicación, aprobación y evidencia. |
| 4 | Alta | **Producto inicial sin decidir** ("Ethernet o wavelength"). Sin esto no hay checklist de campos críticos. | Decidido: EPL (Ethernet Private Line) y wavelength, con un checklist de campos críticos para cada uno desde la Fase 1. |
| 5 | Media | **Severidad sin criterios por defecto.** RF02 dice "criterios configurados" sin dar una base. | Definir defaults: crítico = impide provisioning o genera error contractual; alto = retrasa un hito; medio = retrabajo sin impacto en fecha; informativo = calidad. |
| 6 | Media | **No define arquitectura ni stack técnico** (modelo, orquestación, base de datos, interfaz del SDM). | Sección nueva "Arquitectura propuesta" con decisión explícita; ver decisiones pendientes al final. |
| 7 | Media | **No dice dónde trabaja el SDM** (SDM, Service Delivery Manager): web, correo, Slack, CRM. | Definir la superficie del MVP: vista web de órdenes + borradores exportables. Integraciones después. |
| 8 | Media | **Falta el modelo comercial.** Quién paga, cómo se cobra, qué recibe el design partner. | Sección breve: oferta de piloto (alcance, duración, precio o gratuidad, datos que el carrier aporta, NDA, Non-Disclosure Agreement). |
| 9 | Media | **Las correcciones del SDM no alimentan los evals.** RF09 las registra, pero no se reutilizan. | Agregar RF11: cada corrección del SDM se guarda como caso etiquetado candidato para el set de evaluación. |
| 10 | Baja | **Mezcla de términos** (requested/forecast/committed en inglés en la tabla; solicitada/estimada/comprometida en el texto) y siglas sin definir (LOA-CFA, OSS/BSS, ITSM, p95, SLO). | Glosario al inicio. LOA-CFA = Letter of Authorization – Connecting Facility Assignment; OSS/BSS = Operations/Business Support Systems; ITSM = IT Service Management; p95 = percentil 95; SLO = Service Level Objective. |
| 11 | Baja | **El prompt maestro (sección 14) es largo y siempre devuelve las 8 secciones A–H.** Para una actualización pequeña es excesivo y costoso. | Separarlo en: prompt de sistema estable, definiciones de herramientas y modos de salida (admisión completa, actualización incremental, solo comunicaciones). |

No encontré contradicciones internas graves: puertas, etapas, casos de uso y evals son coherentes entre sí.

## Cómo se usa /prime y /hand-off en este proyecto

Cada sesión de Claude Code abre con `/prime` y cierra con `/hand-off`; el PRD se convierte en `docs/SPEC.md`, que es la única fuente de verdad del plan.

1. **Abrir:** `/prime fase N`. Claude lee `docs/SPEC.md` y `docs/HANDOFF.md`, revisa `git status` y `git log`, corre los tests y entrega un brief de unas 15 líneas. No escribe código.
2. **Aprobar:** revisas el brief (dónde estamos, objetivo, plan, riesgos) y das el visto bueno.
3. **Construir:** solo lo que define la fase N en el SPEC.
4. **Verificar:** tests + evals de la fase. Nunca se declara algo funcionando sin correrlo.
5. **Cerrar:** `/hand-off`. Reescribe `docs/HANDOFF.md` con: a) tareas completadas, b) siguientes pasos y prompt de arranque, c) fricciones, d) cambios al plan, e) rutas exactas de archivos.
6. **Commit:** guardar código y `docs/` juntos, para que el handoff coincida con el código.

Tres reglas adicionales para este proyecto:

- **Una fase puede tomar varias sesiones.** El HANDOFF dice "Partially done" y el siguiente `/prime` retoma desde ahí. Una fase solo se marca "Done" si cumple su criterio de salida.
- **Los cambios de alcance van al SPEC.** Si una sesión decide algo distinto al PRD, se actualiza `docs/SPEC.md` y se anota en la sección d) del HANDOFF.
- **Evals en cada cierre.** Desde la Fase 1, el `/hand-off` incluye el resultado del comando de evals, no solo de los tests.

## Fases de construcción del agente

Nueve fases llevan del PRD a una demo funcional; cada una tiene un criterio de salida que el `/hand-off` debe demostrar antes de marcarla "Done".

&#91;embedded content: Plan de construcción · 9 fases y el piloto posterior\]

La Fase 8 es la meta de construcción; las fases A–E del PRD (validación con datos reales, shadow mode y piloto) empiezan cuando haya un carrier socio.

**Prompt de arranque para las fases 1–8** (cambiar N): *"Ejecuta /prime fase N. Cuando apruebe el plan, construye solo la Fase N según docs/SPEC.md, corre tests y evals, y termina con /hand-off."*

### Fase 0 · SPEC, decisiones y repositorio

- Entregables: repo con la estructura propuesta; `docs/PRD.md` (original); `docs/SPEC.md` con las 11 mejoras aplicadas, las fases y sus criterios; `CLAUDE.md`; `docs/DECISIONS.md` con las cinco decisiones; primer `docs/HANDOFF.md`.
- Sin código de producto.
- Criterio de salida: apruebas el SPEC.
- Prompt: *"Lee docs/PRD.md y esta revisión. Crea docs/SPEC.md aplicando las mejoras, con las fases 0–8 y sus criterios de salida. Crea CLAUDE.md y docs/DECISIONS.md. No escribas código de producto. Termina con /hand-off."*

### Fase 1 · Esquemas, dataset sintético y runner de evals

- Entregables: JSON Schemas de las entidades de la sección 7; reglas EPL y wavelength en `rules/`; 30–40 órdenes sintéticas con anexos y etiquetas "golden"; un runner de evals que se ejecuta con un solo comando.
- Tú revisas las etiquetas: tus 28 años de delivery reemplazan al "etiquetado por expertos" mientras no haya carrier.
- Criterio de salida: todas las órdenes validan contra los esquemas y cubren los 16 casos obligatorios.

### Fase 2 · Ingesta y extracción (UC02 parcial, RF01)

- Entregables: lectura de PDF/DOCX; extracción de campos críticos con valor, fuente, página, versión y fecha; los cuatro estados de dato.
- Criterio de salida: exactitud por campo reportada sobre el set sintético; cero valores sin fuente. El ≥98% del PRD se mide luego con datos reales.

### Fase 3 · Validadores y puertas G0–G1 (UC02, UC03, RF02–RF03)

- Entregables: checklists EPL y wavelength; comparación entre documentos y versiones; severidad; hallazgos con dueño, plazo y acción; recomendación de avanzar o bloquear; override con motivo y aprobador.
- Criterio de salida: recall de discrepancias críticas ≥95% en el set sintético y cero órdenes no listas recomendadas como listas.

### Fase 4 · Hitos, dependencias y fechas (UC04, UC05, RF04; UC07 opcional)

- Entregables: plan de hitos con dueños; grafo de dependencias; fechas solicitada, estimada y comprometida; umbral de seguimiento a proveedores; estado "no estimable".
- Criterio de salida: 100% de los casos distinguen las tres fechas; ninguna estimación aparece como compromiso.

### Fase 5 · Status por audiencia y aprobaciones (UC06, RF05–RF06)

- Entregables: plantilla de la sección 9; borradores interno, cliente y proveedor; filtro por audiencia; estados preparado, aprobado, enviado y fallido. El envío queda simulado.
- Criterio de salida: cero filtraciones entre audiencias en los casos de prueba y ≥4/5 en la rúbrica, evaluada por ti.

### Fase 6 · Entrega, aceptación, hypercare y cierre (UC08, UC09 manual, UC10, puertas G3–G5)

- Entregables: revisión de readiness y evidencias de pruebas; hypercare con evidencia cargada a mano; paquete de handover al NOC (Network Operations Center) y de billing readiness.
- Criterio de salida: no recomienda aceptación sin evidencia y reporta "cobertura desconocida" cuando no hay datos.

### Fase 7 · Seguridad, robustez y auditoría (RF07, RF09, RF10)

- Entregables: segregación por cliente; defensa contra instrucciones dentro de documentos; idempotencia y deduplicación; bitácora completa de decisiones.
- Criterio de salida: cero fallos en los casos adversariales y regresión completa de evals sin retrocesos.

### Fase 8 · Vista web y demo

- Entregables: vista de órdenes, hallazgos, plan y borradores; guion de demo de 10 minutos con una orden sintética; README para operar en shadow mode.
- Criterio de salida: demo de punta a punta sin intervención técnica, con todos los datos marcados como sintéticos.

## Estructura del repositorio

Propuesta de estructura para la Fase 0; los nombres de carpetas de código se ajustan cuando se decida el lenguaje.

```
monkyfi-sdi/
├── CLAUDE.md              # reglas permanentes: no secretos, datos sintéticos etiquetados, no enviar mensajes
├── docs/
│   ├── PRD.md             # PRD v0.1 original, sin cambios
│   ├── SPEC.md            # PRD ajustado + fases + criterios de salida (fuente de verdad)
│   ├── HANDOFF.md         # lo escribe /hand-off al final de cada sesión
│   └── DECISIONS.md       # registro de decisiones de arquitectura, una línea por decisión
├── schemas/               # JSON Schema de orden, hallazgo, hito, dependencia, comunicación...
├── rules/                 # checklist de campos críticos y reglas por producto (EPL primero)
├── data/
│   └── synthetic/         # órdenes sintéticas + etiquetas "golden"
├── src/
│   ├── ingest/            # lectura de PDF/DOCX y extracción con referencia a la fuente
│   ├── validators/        # reglas determinísticas, severidad, puertas G0–G5
│   ├── planner/           # hitos, dependencias, tipos de fecha
│   ├── comms/             # borradores por audiencia y aprobaciones
│   ├── acceptance/        # readiness, evidencias, hypercare, cierre
│   └── audit/             # bitácora de decisiones y acciones (RF09)
├── evals/                 # runner de evals + casos obligatorios + adversariales
└── tests/
```

`CLAUDE.md` complementa a `/prime`: lo que va ahí aplica a todas las sesiones, sin depender del handoff.

## Decisiones pendientes y próximos pasos

Decisiones tomadas el 9 de noviembre de 2026. El resto del PRD (sección 13) puede esperar al carrier piloto.

| Decisión | Elegido | Implicación para la construcción |
| --- | --- | --- |
| Producto del MVP | EPL (Ethernet Private Line) + wavelength | Dos checklists de campos críticos en `rules/` y dataset sintético con órdenes de ambos tipos. Wavelength apoya la oportunidad con Google. |
| Lenguaje | TypeScript + Python | Propuesta: Python para ingesta, extracción, validadores y evals (fases 1–7); TypeScript para la vista web y la API en Vercel (Fase 8). Las reglas viven en JSON para que ambos las lean. |
| Base de datos | Supabase (Postgres) | Los esquemas de la Fase 1 se crean como migraciones. RLS (Row Level Security, seguridad a nivel de fila) implementa la segregación por cliente de RF10. |
| Proveedor del modelo | Gemini o Muse Spark 1.1 (Meta Model API) | Meta Model API está en vista previa pública solo para EE. UU., es compatible con el SDK (Software Development Kit) de OpenAI y soporta salidas estructuradas y llamadas a herramientas; precio publicado: USD 1.25 / 4.25 por millón de tokens de entrada / salida. Capa de proveedor intercambiable: cambiar de modelo no reescribe el agente, pero obliga a re-ejecutar los evals (PRD, sección 12). [Fuente](https://developer.meta.com/ai/resources/blog/build-with-muse-spark/) |
| Idioma | Inglés, con opción de español | Todo en inglés por defecto: SPEC, documentación, código, interfaz y comunicaciones del agente. Un ajuste de idioma permite cambiar la interfaz y las comunicaciones a español, por usuario o por audiencia. |
|  |  |  |

Próximos pasos:

- [ ] Revisar los campos críticos de EPL y wavelength que proponga la Fase 1.
- [ ] Crear el repositorio `monkyfi-sdi` y copiar el PRD a `docs/PRD.md`.
- [ ] Arrancar la Fase 0 en Claude Code con el prompt de la Fase 0.
- [ ] En paralelo: armar una lista corta de carriers o contactos LATAM para ofrecer el piloto cuando exista la demo (Fase 8).
