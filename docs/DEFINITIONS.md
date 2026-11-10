# Definiciones críticas

Las tres decisiones que la Fase 0 debe llevar al SPEC antes de escribir código. Todo lo que no sea una decisión tuya está marcado como propuesta.

## 1. Alcance del MVP

La demo se define con cuatro casos de uso (UC02, UC03, UC04 y UC06) sobre órdenes EPL (Ethernet Private Line) y wavelength de un solo carrier ficticio. Todo lo demás se construye después o sin bloquear la demo.

| Nivel | Casos de uso | Fase | Por qué |
| --- | --- | --- | --- |
| **Define la demo** | UC02 admisión y discrepancias · UC03 cambio de versión · UC04 plan de hitos y dependencias · UC06 borradores por audiencia | 2–5 | Es el recorrido que un SDM (Service Delivery Manager) reconoce en 10 minutos: llega la orden, el agente encuentra errores, llega la v2, se arma el plan y salen los status. |
| **Se construye, no bloquea la demo** | UC05 seguimiento a proveedores · UC08 readiness y aceptación | 4 y 6 | Son obligatorios para el piloto con un carrier, no para mostrar el valor. |
| **Después** | UC01 preventa · UC07 proyecto multicircuito · UC09 hypercare · UC10 cierre | Post-demo | Dependen de datos o integraciones que solo existen con un carrier real. |

**Excepción por la oportunidad con Google (propuesta).** Un hyperscaler compra wavelengths en lotes por proyecto y sitio, así que UC07 le importa más que a una empresa. Propongo que el esquema incluya `project` y `shared_resource` desde la Fase 1, aunque la lógica de UC07 llegue después. Así la demo puede mostrar un proyecto de 3 wavelengths con un cross-connect compartido sin rediseñar la base de datos.

**Fuera del MVP:** envío real de mensajes, integraciones con CRM (Customer Relationship Management), OSS/BSS (Operations / Business Support Systems) o ITSM (IT Service Management), telemetría, facturación y compromisos de fecha automáticos.

**Guión de la demo (propuesta):**

1. Llega una orden EPL firmada con 3 errores sembrados; el agente los reporta con fuente, severidad y dueño, y bloquea G1.
2. El SDM corrige; llega la v2 y el agente reabre solo las validaciones afectadas.
3. La orden pasa G1; el agente arma hitos y dependencias, separando fecha solicitada, estimada y comprometida.
4. Un correo trae una fecha tentativa del proveedor; el agente no la convierte en compromiso.
5. El agente prepara tres borradores (interno, cliente, proveedor), en inglés y luego en español.
6. Cierre: un proyecto de 3 wavelengths con un bloqueo compartido.

## 2. Plan de datos

El dataset es sintético y se genera con un script que siembra cada defecto a propósito. Así las etiquetas correctas se conocen por construcción, y tu revisión se concentra en que las órdenes sean realistas, no en etiquetarlas una por una. Todas las cifras de esta sección son propuestas.

**Composición**

| Conjunto | EPL | Wavelength | Contenido |
| --- | --- | --- | --- |
| Órdenes limpias | 5 | 5 | Sin defectos; prueban que el agente no inventa hallazgos (falsos positivos). |
| Órdenes con defectos | 13 | 13 | Uno o dos defectos sembrados cada una, cubriendo los casos de documento. Incluye un proyecto de 3 wavelengths con una dependencia compartida. |
| Adversariales | 4 | 4 | Instrucciones maliciosas dentro de PDFs y documentos de otro cliente. Se reportan aparte. |
| Eventos simulados | — | — | Archivos de eventos, no órdenes: actualización repetida, integración caída, telemetría ausente. |

**Paquete por orden:** cotización, formulario de orden firmado (PDF), anexo técnico con sitios A/Z, LOA-CFA (Letter of Authorization – Connecting Facility Assignment) cuando aplique, y 1 a 3 correos. Las órdenes con cambio de versión traen v1 y v2.

**Etiquetas "golden" por orden (un JSON junto a los documentos):** valor esperado de cada campo crítico con su ubicación en la fuente; hallazgos esperados con campo, severidad y valores en conflicto; recomendación esperada en G1; y tipo de cada fecha (solicitada, estimada o comprometida).

**Reglas del dataset**

- Carrier, clientes, direcciones y personas son ficticios. El hyperscaler se llama, por ejemplo, "Hyperscaler X (synthetic)", nunca con el nombre de una empresa real.
- Cada documento lleva la marca "SYNTHETIC — NOT REAL DATA" y cada registro en Supabase tiene `is_synthetic = true`.
- División: 24 órdenes de desarrollo y 12 de evaluación, separadas por cliente para que el agente nunca vea en desarrollo a los clientes del set de evaluación.
- Los umbrales sobre datos sintéticos son señal de desarrollo, no prueba de producción. El SPEC lo dice así.

**Cómo se genera (Fase 1)**

1. Validas la lista de campos críticos de EPL y wavelength (sección 3).
2. Claude Code genera 2 órdenes de ejemplo, una de cada producto; las revisas como lo haría un SDM.
3. Con tus correcciones, el script genera el resto.
4. Revisas una muestra de 6 órdenes (aproximadamente 20%) antes de cerrar la fase.

**Los 16 casos obligatorios del PRD (Product Requirements Document)**

| # | Caso | Dónde se prueba | Fase |
| --- | --- | --- | --- |
| 1 | Capacidad discrepante | Orden con defecto | 3 |
| 2 | Suite equivocada | Orden con defecto | 3 |
| 3 | Demarcación ausente | Orden con defecto | 3 |
| 4 | Versión obsoleta | Orden con v1 y v2 | 3 |
| 5 | Fecha tentativa en correo | Orden con defecto | 4 |
| 6 | Proveedor sin fecha | Orden con defecto | 4 |
| 7 | Dependencia compartida entre órdenes | Proyecto de 3 wavelengths | 4 |
| 8 | Orden modificada después de validación | Orden con v1 y v2 | 3 |
| 9 | Pruebas incompletas | Orden con defecto | 6 |
| 10 | Telemetría ausente | Evento simulado | Post-demo |
| 11 | Cliente equivocado | Adversarial | 7 |
| 12 | Instrucción maliciosa dentro de PDF | Adversarial | 7 |
| 13 | Actualización repetida | Evento simulado | 7 |
| 14 | Integración caída | Evento simulado | 7 |
| 15 | Aceptación no documentada | Orden con defecto | 6 |
| 16 | Presión para cerrar antes de G4 | Orden con defecto (correo) | 6 |

## 3. Esquema de datos

El esquema gira en torno a una pieza: `field_value`, el valor-con-fuente. Ningún dato de la orden se guarda suelto; cada uno trae de dónde salió, en qué versión y en qué estado está. Los nombres van en inglés porque son tablas de Supabase.

**Entidades (propuesta)**

| Entidad | Para qué | Campos clave |
| --- | --- | --- |
| `tenant` | Un carrier; base de la segregación por RLS (Row Level Security) | name, is\_synthetic |
| `customer` | Cliente del carrier | tenant\_id, name, type (enterprise / hyperscaler) |
| `project` | Agrupa órdenes de un cliente (clave para hyperscalers) | customer\_id, name |
| `order` | La orden de servicio | project\_id (opcional), external\_order\_id, product (EPL / WAVELENGTH), stage, is\_blocked, current\_version\_id |
| `order_version` | Cada versión recibida | order\_id, version\_no, received\_at, supersedes\_id |
| `document` | Cada archivo del paquete | order\_version\_id, doc\_type, filename, file\_hash, ingested\_at |
| `endpoint` | Extremo A o Z | order\_version\_id, side (A / Z); sus datos son `field_value` |
| `field_value` | El valor-con-fuente (detalle abajo) | ver abajo |
| `finding` | Hallazgo o discrepancia | rule\_id, field\_key, severity, conflicting\_values, evidence, impact, owner, due\_date, status |
| `gate_evaluation` | Recomendación en cada puerta | order\_version\_id, gate (G0–G5), recommendation (pass / block), unmet\_requirements |
| `milestone` | Hito del plan | order\_id, name, owner, requested\_date, forecast\_date, forecast\_assumptions, committed\_date, commitment\_approval\_id |
| `dependency` | Qué depende de qué | from\_milestone\_id, to\_milestone\_id, kind (internal / supplier / customer), shared\_resource\_id, owner, due\_date |
| `shared_resource` | Recurso común a varias órdenes (por ejemplo, un cross-connect) | tenant\_id, kind, description |
| `communication` | Borrador de status | order\_id, audience (internal / customer / supplier), language (en / es), status (prepared / approved / sent / failed), body, source\_refs |
| `approval` | Aprobaciones y overrides | entity, decision, approver, reason, created\_at |
| `audit_event` | Bitácora (RF09) | actor, action, entity, before, after, model\_version, prompt\_version, rules\_version |

**`field_value`: el valor-con-fuente**

| Campo | Qué guarda |
| --- | --- |
| field\_key | Nombre del campo crítico, por ejemplo `bandwidth` o `a_end.suite` |
| raw\_value / normalized\_value | El texto como aparece y su forma normalizada (por ejemplo, "10 Gbps" → 10000 Mbps) |
| status | verified · pending · missing · not\_applicable · contradictory · stale |
| source\_document\_id + location | Documento y ubicación exacta (página, sección o celda) |
| fact\_timestamp / ingested\_at | Cuándo ocurrió el dato y cuándo llegó, para detectar información tardía |
| extracted\_by | model · rule · human |

**Severidad por defecto (propuesta):** critical = impide el provisioning o genera un error contractual; high = retrasa un hito; medium = genera retrabajo sin afectar fechas; info = calidad del dato.

**Campos críticos por producto (propuesta para que la valides)**

| Grupo | EPL | Wavelength |
| --- | --- | --- |
| Identificación | ID de orden, cliente, producto, versión | Igual |
| Capacidad | Ancho de banda (1G / 10G / 100G) | Tasa (10G / 100G / 400G) y protocolo del cliente (Ethernet u OTN, Optical Transport Network) |
| Interfaz | Tipo de interfaz y óptica en el handoff, conector | Interfaz cliente (por ejemplo, 100GBASE-LR4 u OTU4, Optical Transport Unit 4), óptica, conector |
| Parámetros | MTU (Maximum Transmission Unit); VLAN (Virtual LAN) solo si el contrato lo exige | Protección (protegido / no protegido), diversidad de ruta respecto de otros circuitos, latencia máxima si está contratada |
| Extremos A/Z | Dirección, edificio, piso, suite o sala, rack, punto de demarcación | Igual |
| Acceso | Cross-connect y LOA-CFA, acceso al sitio, contactos autorizados | Igual |
| Aceptación | Pruebas exigidas (por ejemplo, RFC 2544 o ITU-T Y.1564, estándares de prueba Ethernet) | Prueba de BER (Bit Error Rate, tasa de error de bits) y su duración según contrato |
| Fechas | Solicitada, estimada y comprometida (con su aprobación) | Igual |

**Una corrección a la revisión:** escribí que EPL tiene más campos condicionales "como VLAN". En realidad, EPL suele ser un servicio basado en puerto, así que la VLAN normalmente no aplica; la exige EVPL (Ethernet Virtual Private Line). En wavelength, la diversidad de ruta y la protección son los campos condicionales que más pesan para un hyperscaler.

## 4. Lo que necesito que valides

Cuatro puntos dependen de tu experiencia; con ellos, la Fase 0 puede copiar estas definiciones al SPEC.

- [ ] Campos críticos de EPL y wavelength: qué sobra, qué falta y qué es condicional.
- [ ] Severidad por defecto: si los cuatro niveles reflejan cómo se clasifica en un carrier.
- [ ] Incluir `project` y `shared_resource` desde la Fase 1 por la oportunidad con Google.
- [ ] Guión de la demo: si los 6 pasos son los que convencerían a un Head of Delivery.
