# Formato del CSV de inventario/ventas

Este es el contrato de entrada del pipeline: cualquier archivo subido a
`raw/` en S3 debe cumplir este formato. Lo genera a mano quien lleva el
inventario de LoopVTG; si en el futuro se automatiza la exportación
(herramienta de terceros, export propio), debe producir un CSV con
este mismo esquema para no romper el resto del pipeline.

## Convenciones generales

- Codificación **UTF-8**, separador **coma** (`,`), primera fila de
  cabecera obligatoria.
- Decimales con **punto** (`.`), nunca coma, para evitar ambigüedad de
  parseo.
- Fechas en formato **ISO 8601** (`YYYY-MM-DD`).
- Un archivo = una foto completa del inventario en el momento de la
  subida (no un delta). El campo `item_id` es estable entre subidas
  para poder trackear el mismo artículo a lo largo del tiempo.
- Campos vacíos se representan como cadena vacía, no `NULL` ni `N/A`.

## Columnas

| Columna         | Tipo    | Obligatorio | Descripción                                                                 |
|-----------------|---------|:-----------:|------------------------------------------------------------------------------|
| `item_id`       | string  | sí          | Identificador interno único del artículo. Formato `LV-NNNN` (secuencial).   |
| `title`         | string  | sí          | Título del anuncio, texto libre.                                            |
| `category`      | enum    | sí          | Una de: `vaqueros`, `camisetas`, `polos`, `camisas`, `chaquetas`, `sudaderas`, `vestidos`, `jerseys`, `faldas`, `pantalones`, `calzado`, `accesorios`, `otros`. |
| `brand`         | string  | no          | Marca. `desconocida` si no se identifica.                                   |
| `size`          | string  | no          | Talla tal cual se publicó (`S`, `42`, `talla_unica`, ...). Sin normalizar entre sistemas de tallaje. |
| `condition`     | enum    | sí          | Una de: `nuevo_con_etiquetas`, `nuevo_sin_etiquetas`, `muy_bueno`, `bueno`, `satisfactorio` (mapea las categorías de estado de Vinted). |
| `cost_price`    | decimal | sí          | Coste de adquisición en EUR. `0.00` si fue donado o de stock propio.        |
| `listing_price` | decimal | sí          | Precio de publicación en EUR.                                               |
| `sale_price`    | decimal | no          | Precio real de venta en EUR. Vacío si `status` no es `sold`.                |
| `listed_date`   | date    | sí          | Fecha de publicación en Vinted (`YYYY-MM-DD`).                              |
| `sold_date`     | date    | no          | Fecha de venta (`YYYY-MM-DD`). Vacío si no se ha vendido.                    |
| `status`        | enum    | sí          | Una de: `listed`, `reserved`, `sold`, `removed`.                            |
| `platform`      | string  | sí          | Canal de venta. De momento siempre `vinted`; campo pensado para futuros canales. |

## Por qué este diseño

- **`item_id` estable en vez de recalcular todo cada vez**: permite
  que la Lambda de procesamiento (Fase 2) distinga altas, cambios de
  estado (`listed` → `sold`) y bajas entre una subida y la siguiente,
  en lugar de tratar cada CSV como datos aislados.
- **`cost_price` y `sale_price` separados**: sin el coste de
  adquisición no se puede calcular margen, solo rotación y precio de
  venta. Se incluye desde el principio aunque las métricas de la Fase
  2 no lo usen todavía, para no tener que romper el esquema más
  adelante.
- **`condition` como enum cerrado**: si fuera texto libre, la Lambda
  de limpieza tendría que normalizar variantes ("muy bueno", "Muy
  Bueno", "excelente"...) sin ninguna garantía de cobertura. Fijar el
  vocabulario en el propio CSV traslada esa disciplina a la fuente.
- **`platform` desde ya, aunque solo exista `vinted`**: si en el
  futuro se vende también en otro canal, el esquema no cambia — solo
  el valor de la columna.

## Ejemplo

Ver [`samples/inventory_sample.csv`](samples/inventory_sample.csv).
