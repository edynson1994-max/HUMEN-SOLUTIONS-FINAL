# Perú en Datos — Conectores de fuentes reales

Este paquete conecta "Perú en Datos" a fuentes de datos públicos reales del
Perú. Es la primera fase de conexión real, siguiendo tu pedido de priorizar
MEF, SEACE/OECE, INEI, Contraloría y sobre todo el Portal Nacional de Datos
Abiertos (PNDA, `datosabiertos.gob.pe`) por ser datos libres y usables.

## Qué se investigó y qué se encontró

**PNDA (`www.datosabiertos.gob.pe`)** es un portal DKAN (basado en Drupal)
con una capa de API estilo CKAN. Se probaron 3 endpoints documentados:

- `api/action/datastore/search.json?resource_id=...` — la "Data API" real
  por recurso. Al principio pareció rota (probada con un `resource_id`
  adivinado/incorrecto), pero el instructivo oficial que compartiste
  ("Instructivo para el Registro de Datasets en la PNDA", PCM 2021)
  confirmó que SÍ es un mecanismo real — solo funciona para los recursos
  que se registraron con la opción "Grilla"/datastore activada al
  subirlos, no para todos. Ahora los conectores la intentan primero con el
  `resource_id` real (obtenido de `package_show`), y si ese recurso en
  particular no tiene datastore, caen automáticamente al siguiente nivel.
- `api/3/action/package_search` — **no enrutado** (404). Sigue sin haber
  forma de *buscar* datasets por API; hay que conocer el dataset de
  antemano.
- `api/3/action/package_show?id=<id>` — **funciona**. Devuelve metadata
  JSON real de un dataset conocido, incluyendo la lista de sus recursos
  con su `resource_id` real y su URL de descarga *actual* (más confiable
  que una URL fija capturada a mano, porque viene de la fuente de verdad
  en el momento de la corrida).

**Estrategia de 3 niveles** (ver el aviso completo en `connectors/common.py`
y en las cabeceras de cada conector) — cada conector intenta, en orden,
cayendo al siguiente solo si el anterior falla, y dejando registrado en
`"metodo"` cuál funcionó:

1. **Data API** (`datastore_search_all`) sobre el `resource_id` real.
2. **Descarga directa** de la URL *en vivo* que reporta `package_show` para
   ese recurso.
3. **Descarga directa** de la URL fija que verifiqué a mano (por si
   `package_show` mismo falla, ej. si el slug del dataset cambió).

Ninguno de los 3 niveles necesita usuario ni clave — el login que pide el
instructivo es solo para las entidades que *publican* datasets nuevos, no
para leer datos ya públicos.

El CSV del MEF (~2.3 GB) es la excepción: ahí NO se usa la Data API a
propósito (paginar millones de filas sería mucho más lento que el
streaming directo que ya tiene el conector) — `package_show` solo se usa
para refrescar la URL de descarga, no para leer los datos.

**Fuentes conectadas a mano en esta fase inicial:**

| Fuente | Dataset | Conector |
|---|---|---|
| Contraloría | Monitores Ciudadanos de Control (2 datasets: intervenciones 2021 + info general) | `contraloria.py` |
| INEI | RENAMU 2023 (muestra) | `inei_renamu.py` |
| MEF | Presupuesto y Ejecución de Gasto — Devengado Mensual 2025 (~2.3 GB) | `mef.py` |

Estos 3 conectores hechos a mano NO cambiaron con las fases siguientes —
`discovery.py` y `sync_dataset.py` (Fases 3-4) son módulos nuevos que
conviven con ellos, para generalizar el patrón a cualquier dataset del
portal sin tener que escribir un archivo por cada uno.

## Cómo están construidos los conectores

Cada conector fue diseñado para **nunca asumir un nombre de columna
fijo**:

- `detect_column()` busca la columna real por coincidencia aproximada
  (sin tildes, insensible a mayúsculas) contra una lista de nombres
  candidatos en español.
- Cada resultado incluye `columnas_detectadas`: la lista real de columnas
  que encontró en el archivo, para que puedas verificar de un vistazo si la
  detección funcionó.
- Si una columna esperada no se encuentra, el conector reporta `null` en
  vez de inventar un número. Nunca fabrica datos.
- El CSV del MEF (~2.3 GB) se procesa en streaming línea por línea, sin
  cargar el archivo completo en memoria.

Los conectores solo usan la librería estándar de Python — no necesitas
instalar nada (`pip install`).

## Bugs reales encontrados y corregidos (conectores originales)

1. **El push a git fallaba con "[rejected] ... fetch first".** Corregido
   con `fetch` + `merge -X ours` + reintentos en vez de un `git push` a
   secas — mismo mecanismo que usan TODOS los workflows de este proyecto.
2. **`package_show` truena con nombres de dataset que tienen tildes** —
   corregido con `quote()` antes de construir la URL.
3. **El "monto total" del MEF en realidad era solo el de enero** — el
   archivo viene en formato ancho (`MONTO_DEVENGADO_ENERO`..`DICIEMBRE` +
   `MONTO_DEVENGADO_ANUAL`), no una columna "monto" + una columna "mes".
   Corregido, y de paso ahora arma una serie mensual real
   (`gasto_mensual_nacional`).
4. **Las regiones salían como códigos numéricos en vez de nombres** — bug
   de fondo en `detect_column()`: un candidato largo quedaba emparejado
   con un campo corto porque el corto queda "contenido" en el largo.
   Corregido con búsqueda en dos pasadas (exacta primero, substring
   después).
5. **Columnas con tildes salían con `�` (mojibake)** — esos CSV vienen en
   Windows-1252, no UTF-8. Corregido con `smart_decode()` (intenta UTF-8,
   cae a cp1252 si quedan caracteres de reemplazo).
6. **`package_show` a veces devuelve una lista en vez de un objeto** — ver
   el bug equivalente (y mejor entendido) documentado en la Fase 3 más
   abajo.

## Fase 3 — Descubrimiento del catálogo completo (`discovery.py`)

Recorre **todo el portal** (4,650 datasets a la fecha de la última
corrida) y clasifica cuáles son de Economía y Finanzas, sin scrapear
ninguna página bloqueada por `robots.txt`.

Verificado en vivo antes de escribirlo (no adivinado):

- `api/3/action/package_list` — **sí funciona**, devuelve los slugs de
  todos los datasets del portal.
- La página `/search/field_topic/economía-y-finanzas-29` (la que muestra
  "1,330 datasets" en un navegador normal) está **bloqueada por el
  robots.txt del portal** — por eso `discovery.py` NO la scrapea. En su
  lugar, clasifica cada dataset con una heurística transparente y
  ajustable: primero por entidad publicadora conocida (MEF, SUNAT, BCRP,
  Banco de la Nación, ONP, COFIDE, FONAFE, SBS), y si no matchea, por
  palabras clave en el título/descripción/tags (presupuesto, gasto,
  tributación, deuda, etc.). Cada dataset guarda `categoria_metodo`
  (`"entidad"` o `"palabra_clave"`) para que la clasificación sea siempre
  auditable — nunca es una caja negra.
- Para detectar qué recursos tienen la Data API (datastore) activada, se
  agregó `has_data_api()` a `common.py` — por defecto solo prueba esto
  para los datasets clasificados como Economía y Finanzas
  (`--probar-data-api todos` lo activa para el portal completo).

Salida: `data/catalog.json` — el catálogo completo del portal (todas las
categorías quedan registradas, no solo Economía y Finanzas).

**Cómo correrlo — desde GitHub Actions:** pestaña **Actions** → workflow
**"Descubrir catálogo PNDA (Fase 3 - Perú en Datos)"** → **Run workflow**.
Manual a propósito (ver Fase 5 sobre por qué).

**La corrida se puede cortar y continuar sin perder nada:** guarda un
checkpoint de `data/catalog.json` cada 200 datasets, se detiene
ordenadamente antes del `timeout-minutes` del job con `--max-minutos`, y
si queda parcial (`"corrida_completa": false`), se retoma poniendo
`siguiente_empezar_en` en el campo **"empezar_en"** del formulario.

**Bugs de clasificación reales, encontrados analizando con Python la
primera corrida completa (706 clasificados) contra el `catalog.json`
real:**

1. **La palabra clave "fiscal" generaba 107 falsos positivos limpios** —
   "fiscal" en español también significa "de la fiscalía" o
   "fiscalización" (OEFA, MINEM, Ministerio Público), no solo "de
   impuestos". Se quitó de la lista sin perder cobertura real (los casos
   legítimos ya quedaban cubiertos por otras palabras).
2. **OEFA y PRONABEC se colaban por tags compartidos, no por contenido
   real** — sus nombres institucionales contienen palabras
   finance-adjacent ("Fiscalización", "Crédito Educativo"). Se agregó
   `ENTIDADES_EXCLUIDAS_DE_PALABRA_CLAVE` (~89 + ~33 datasets corregidos).
3. **Los `tags` ahora se guardan en `catalog.json`** — antes se usaban
   para clasificar pero no se persistían, haciendo imposible auditar
   ~99 datasets clasificados solo por un tag sin volver a llamar a la API.

Con estos 3 ajustes, una simulación offline sobre los mismos datasets bajó
el total de 706 a ~495-511 clasificados (el número exacto definitivo
requiere una corrida nueva).

## Fase 4 — Sincronización genérica de un dataset (`sync_dataset.py`)

Generaliza el patrón de 3 niveles que `mef.py`/`contraloria.py` repetían a
mano para que funcione con CUALQUIER `dataset_id` de `catalog.json`, sin
escribir un conector nuevo por cada uno.

**A propósito, NO interpreta el significado de las columnas** de cada
dataset. Con ~500-700 datasets de estructuras totalmente distintas,
adivinar qué columna es "monto" o "región" en cada uno sería inventar. Lo
que sí hace, para cualquier CSV: cuenta filas, detecta las columnas reales
(`columnas_detectadas`) y guarda una muestra de las primeras filas tal
cual — interpretar el significado de cada dataset queda para conectores
dedicados (como `mef.py`) o para el usuario final vía la ficha de dataset
(Fase 11).

Solo CSV por ahora; un recurso en otro formato queda marcado
`"estado": "formato_no_soportado"`, sin forzar un parseo que saldría mal.

**Salida** (sección 3 del plan de Fase 1):

```
data/sources/<dataset_id>/
  latest.json         - resultado de la sincronización más reciente,
                         incluyendo cambio_vs_corrida_anterior (Fase 6)
  raw/<fecha>.json     - copia de ese mismo resultado, nunca se sobreescribe
  history.jsonl        - una línea por corrida (fecha, estado, filas,
                          nivel_usado, cambio)
```

## Fase 5 — El cron automático (`sincronizar-economia-finanzas.yml`)

El workflow que corre solo, sin que nadie lo dispare a mano, para mantener
`data/sources/` actualizado.

**Por qué descubrimiento y sincronización son dos workflows separados**
(no uno combinado, como sugería el plan original):

| | `descubrir-catalogo.yml` | `sincronizar-economia-finanzas.yml` |
|---|---|---|
| Qué hace | Recorre TODO el portal y arma/actualiza `data/catalog.json` | Sincroniza los datasets YA clasificados como Economía y Finanzas |
| Frecuencia | Baja — el portal no publica datasets nuevos todos los días | Alta — los datasets ya conocidos se actualizan con su propio calendario |
| Disparo | Manual (`workflow_dispatch`) | Automático (`schedule` semanal) + manual disponible |

**Continuación automática entre corridas programadas:** cada corrida
escribe `data/sources/_resumen_ultima_corrida.json` con
`siguiente_empezar_en`. La siguiente corrida programada lo lee sola: si
la anterior quedó parcial, continúa donde quedó; si se completó entera,
reinicia en 0 — el ciclo se repite indefinidamente sin dejar ningún
dataset eternamente desactualizado.

**Cron:** domingos 09:00 UTC (04:00 hora Perú).

Validado offline (`test_sync_checkpoint.py`) encadenando una corrida
cortada por tiempo con su continuación, verificando cobertura exacta sin
huecos ni repetidos.

Después de sincronizar, este mismo workflow corre las Fases 6-7-12 (ver
abajo) — los 3 solo LEEN lo que `sync_dataset.py` ya guardó, así que
corren siempre (`if: always()`), incluso sobre una corrida parcial.

## Fase 6 — Detección de cambios

Dos piezas:

1. **`_calcular_cambio()` dentro de `sync_dataset.py`** — cada vez que
   `guardar_resultado()` escribe una nueva sincronización, primero lee la
   ÚLTIMA línea del `history.jsonl` existente (la corrida anterior de ese
   mismo dataset) y calcula si cambió el conteo de filas. Guarda el
   resultado como `cambio_vs_corrida_anterior` en `latest.json` y como
   `cambio` en la nueva línea de `history.jsonl`. SOLO afirma una
   diferencia cuando ambas corridas (anterior y actual) fueron `"ok"` con
   un conteo de filas real — en cualquier otro caso (primera
   sincronización, o alguna corrida falló) queda explícitamente
   `"primera_sincronizacion"` o `"no_comparable"`, nunca un delta
   inventado.
2. **`connectors/detectar_cambios.py`** — recorre TODOS los
   `data/sources/*/history.jsonl`, toma la última línea de cada uno (ya
   con su `cambio` calculado) y arma `data/cambios_recientes.json`: la
   lista agregada que consume la sección "¿Qué cambió?" del frontend
   (Fase 9), ordenada por magnitud del cambio, con el recorte
   (`MAX_MOSTRADOS`) siempre explícito en el propio JSON (nunca un corte
   silencioso).

Validado offline (`test_fase6_cambios.py`): aumento, disminución, sin
cambio, primera sincronización, y un error que NO debe inventar un delta
— los 5 casos, más el recorte explícito y el caso de `data/sources/`
todavía inexistente.

## Fase 7 — Analítica (`analytics.py`)

Lee `catalog.json` + todos los `history.jsonl` y calcula, para Economía y
Finanzas: cobertura del catálogo, estado de sincronización (ok/error/
formato no soportado), ranking de datasets por filas, ranking de mayores
variaciones % (aumento y disminución), tendencia por dataset (creciente/
decreciente/estable/insuficiente historial, sobre las últimas 5 corridas
ok) y top de entidades por datasets sincronizados con éxito. Escribe
`data/analytics/economia-finanzas.json`, que alimenta "En cifras"
(Fase 10).

**A propósito, todo se basa en `filas_leidas` y metadata del catálogo —
nunca en el contenido de las columnas** (mismo principio que
`sync_dataset.py`): con datasets de estructuras tan distintas, cualquier
otra cosa sería inventar.

Validado offline (`test_fase7_analytics.py`) con un catálogo y varias
corridas de muestra construidas con el `guardar_resultado()` REAL (no a
mano), cubriendo aumento/disminución/tendencia creciente/estado de
error/exclusión de datasets fuera de la categoría.

## Fase 8 — "Lo último" (catálogo real en el frontend)

`peru-datos/app.html`, sección **Catálogo**: el número "datasets reales
de Economía y Finanzas" y el nuevo bloque **"Lo último actualizado en el
portal"** ahora se alimentan de `data/catalog.json` en vivo (antes eran
estáticos). Se muestran los datasets con `fecha_modificacion_portal` más
reciente, ordenados de verdad por fecha.

**Detalle importante encontrado con datos reales (no una suposición):**
el portal NO es consistente en el orden día/mes de esa fecha — la
mayoría de ejemplos vistos vienen como DD/MM/AAAA, pero al menos uno real
trae `"Mié, 12/17/2025 - 11:57"` (inequívocamente MM/DD, porque no existe
el mes 17). `parseFechaPortal()` en `app.html` asume DD/MM por defecto,
pero si el componente que leería como "mes" sale > 12, invierte los dos
números (evidencia inequívoca de MM/DD). Esto SOLO afecta el ORDEN
interno de "lo último" — el texto que se muestra en pantalla es siempre
el string crudo del portal, nunca reformateado.

Si `catalog.json` no existe o el fetch falla, la sección de "Lo último"
simplemente no aparece (no rompe nada, no muestra contenido fabricado) y
el número de la tarjeta principal se queda en su valor de demo.

## Fase 9 — "¿Qué cambió?"

Sección nueva en `app.html`, alimentada por `data/cambios_recientes.json`
(Fase 6). Cada fila enlaza a la ficha del dataset (Fase 11). Si todavía
no hay comparaciones posibles (catálogo recién descubierto, o solo una
sincronización por dataset), muestra un estado vacío honesto explicando
por qué, en vez de datos de relleno — esta sección se presenta como
100% real, así que nunca tiene una versión "demo".

## Fase 10 — "En cifras"

Sección nueva en `app.html`, alimentada por `data/analytics/
economia-finanzas.json` (Fase 7): cuántos datasets de la categoría se
conocen (de cuántos en total, y si el descubrimiento está completo),
cuántos se sincronizaron con éxito, cuántos tienen Data API confirmada, y
el total/promedio de filas sincronizadas. Mismo principio que la Fase 9:
si `analytics.json` no existe todavía, estado vacío honesto, nunca
números inventados.

## Fase 11 — Ficha de dataset individual (`peru-datos/dataset.html`)

Página nueva, `dataset.html?id=<dataset_id>`, enlazada desde "Lo último"
y "¿Qué cambió?". Muestra: estado de la última sincronización, el cambio
vs. la corrida anterior, un gráfico de tendencia (filas por corrida, a
partir de `history.jsonl`), una muestra de las filas reales tal como
llegaron, y el botón "Ver dataset oficial" hacia la fuente en
datosabiertos.gob.pe. Si el id no existe, o no se encuentra ni en el
catálogo ni en los datos sincronizados, muestra un mensaje honesto en vez
de una página rota.

## Fase 12 — Historias candidatas (`story_engine.py`)

**Esto NO es redacción de historias** — a propósito, según el plan
original (la redacción asistida por IA queda para una iteración
posterior). Lee `analytics.json` + `cambios_recientes.json` (ambos ya
calculados, no vuelve a tocar ningún dataset) y arma
`data/stories/candidatas.json`: una lista de historias candidatas
priorizadas, cada una con sus hechos numéricos reales expuestos por
separado (`hechos`) y una frase armada por PLANTILLA (`resumen_
estructurado`) que solo rellena números ya calculados — nunca agrega una
interpretación nueva. Tipos: mayor aumento, mayor disminución, dataset
con más filas, cobertura del catálogo, nuevas conexiones.

Validado offline (`test_fase12_stories.py`): los 5 tipos de candidata, que
nunca inventa una candidata de cobertura sin datos de catálogo, y que no
lanza si los archivos de entrada no existen todavía.

## Verificación de las Fases 6-12

Todo lo de arriba se verificó de 3 formas antes de entregarse:

1. **Pruebas offline con datos simulados** (`test_fase6_cambios.py`,
   `test_fase7_analytics.py`, `test_fase12_stories.py`) — construidas con
   las funciones REALES del pipeline (no JSON escrito a mano), cubriendo
   los casos límite de cada fase.
2. **Corrida real contra el `catalog.json`/`data/sources/` que ya estaban
   en el repo** (aunque parciales) — para confirmar que ninguna fase
   nueva revienta con datos de producción reales, incompletos.
3. **Verificación visual con Playwright** (servidor HTTP local +
   capturas de pantalla) de `app.html` y `dataset.html`, tanto contra los
   datos reales (parciales) como contra un catálogo/historial sintético
   más rico, en escritorio y en móvil, confirmando que las secciones
   nuevas se ven bien, que los estados vacíos son honestos y que nada
   rompió las secciones existentes (Estelares, Fuentes, Mapa, Tu Perú).

## Siguiente paso pendiente

Con las Fases 3-12 completas, lo que queda del plan original de Fase 1 es
seguir alimentando y refinando este pipeline con datos reales — en
particular, completar el descubrimiento del catálogo (ver la nota sobre
el estado real del catálogo al momento de esta entrega) y dejar correr el
cron un tiempo para que "¿Qué cambió?"/"En cifras"/candidatas tengan
suficiente historial real detrás. No hay ninguna fase de este plan sin
construir.
