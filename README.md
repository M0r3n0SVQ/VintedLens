# VintedLens

[![CI](https://github.com/M0r3n0SVQ/VintedLens/actions/workflows/ci.yml/badge.svg)](https://github.com/M0r3n0SVQ/VintedLens/actions/workflows/ci.yml)

Pipeline serverless en AWS para ingesta, procesamiento y reporting del
inventario y las ventas de **LoopVTG**, un negocio de reventa de ropa
vintage activo en Vinted. Convierte un CSV exportado a mano en métricas
de negocio (rotación de inventario, precio medio, tiempo en catálogo) y
un resumen en lenguaje natural generado con IA, entregado por email.

Proyecto de portfolio orientado a Cloud/DevOps, hermano de
**AWS FinOps Monitor** (mismo stack base: Lambda, EventBridge, IAM,
Parameter Store, Terraform, pytest, GitHub Actions) y de **Plendu**
(Next.js + IA), con el que conecta en la Fase 5 opcional.

## Estado del proyecto

✅ **Fase 1 completada** — repo, Terraform base, bucket S3 desplegado,
formato de CSV definido, guardarraíl de coste activo.
✅ **Fase 2 completada** — Lambda de procesamiento, EventBridge,
Parameter Store, tests con pytest. Verificado de extremo a extremo
contra AWS real.
✅ **Fase 3 completada** — Lambda de reporting, resumen en lenguaje
natural con Bedrock, envío por SES. Verificado de extremo a extremo:
email real recibido con un resumen generado por IA a partir de las
métricas.
✅ **Fase 4 completada** — CI/CD con GitHub Actions (lint, tests,
cobertura, `terraform plan`/`apply`), autenticación OIDC sin
credenciales estáticas. Los tres workflows verificados corriendo de
verdad en GitHub (ver [CI/CD](#cicd-fase-4)).

✅ **Fase 5 completada** — API HTTP (API Gateway + Lambda) desplegada
y dashboard en Next.js publicado en Vercel, ambos verificados
end-to-end contra datos reales: [vintedlens-dashboard.vercel.app](https://vintedlens-dashboard.vercel.app/)
· [repo del dashboard](https://github.com/M0r3n0SVQ/vintedlens-dashboard).

**Las 5 fases completas** — el pipeline serverless entero (1-4) más
el dashboard opcional (5) conectando ambos proyectos del portfolio,
en vez de dejarlos como piezas sueltas.

## Por qué este proyecto

LoopVTG necesita saber qué se vende, a qué velocidad y a qué precio,
sin depender de la analítica limitada que ofrece Vinted. En vez de
montar un dashboard suelto, lo planteo como un pipeline de datos
serverless real: sirve como caso de uso de negocio genuino y, a la
vez, como proyecto de portfolio para demostrar diseño de arquitectura
en AWS, IaC y buenas prácticas de ingeniería.

## Arquitectura

```mermaid
flowchart LR
    A[CSV manual\ninventario/ventas] -->|upload| B[(S3 raw/)]
    B -->|ObjectCreated| C[EventBridge]
    C --> D[Lambda: procesamiento\nlimpieza + métricas]
    D --> E[(S3 processed/)]
    D -.config.-> F[[Parameter Store]]
    E --> G[Lambda: reporting]
    G -->|prompt| H[[Amazon Bedrock]]
    H -->|resumen NL| G
    G -->|email| I[SES]

    subgraph "Fase 5 (opcional)"
        E --> J[API Gateway]
        J --> K[Next.js en Vercel]
    end
```

### Flujo

1. **Origen**: CSV de inventario/ventas con formato propio (definido en
   este repo). Es la fuente de verdad manual — no hay integración con
   la API de Vinted (ver decisión más abajo).
2. **Ingesta**: subida manual del CSV a un bucket S3, prefijo `raw/`.
3. **Procesamiento**: un evento `ObjectCreated` en EventBridge dispara
   una Lambda que limpia los datos y calcula métricas (rotación,
   precio medio, tiempo en catálogo). La configuración (umbrales,
   parámetros de cálculo) vive en Parameter Store.
4. **Almacenamiento**: los datos limpios y las métricas se guardan en
   el mismo bucket, prefijo `processed/`.
5. **Reporting**: una segunda Lambda genera un resumen periódico,
   pide a Amazon Bedrock un resumen en lenguaje natural de los
   resultados (p. ej. *"la rotación de vaqueros bajó un 15% este mes,
   revisa el precio en esa categoría"*) y lo envía por email vía SES.
6. **IaC**: toda la infraestructura en Terraform, tests con pytest,
   CI/CD con GitHub Actions.
7. **(Opcional, Fase 5)**: los datos procesados se exponen vía API
   Gateway y se consumen desde un frontend ligero en Next.js
   desplegado en Vercel, reutilizando patrones de Plendu.

## Decisiones y por qué

**CSV como fuente de verdad, no la API de Vinted.**
Vinted no ofrece una API pública y estable para exportar
inventario/ventas; las alternativas son scraping o servicios de
terceros poco fiables, y ninguna encaja en un proyecto que quiero
mantener en producción de forma sostenible. El CSV es una interfaz
estable que controlo yo: si en el futuro aparece una fuente de datos
mejor (export oficial, herramienta de terceros fiable), solo cambia
quién genera el CSV, no el pipeline.

**Amazon Bedrock en vez de OpenAI para el resumen en lenguaje natural.**
Ahora mismo me estoy certificando en AWS CCP y AZ-900, así que quiero
practicar con servicios de IA nativos de AWS en vez de reutilizar
OpenAI (que ya uso en Plendu). Además da variedad real de stack entre
mis dos proyectos de portfolio: Plendu integra IA en un SaaS Next.js;
VintedLens la integra dentro de una arquitectura serverless AWS.

**Serverless (Lambda + EventBridge) en vez de un servidor siempre
activo.** La carga es esporádica (una subida de CSV cada cierto
tiempo, un reporting periódico), así que un servidor 24/7 sería coste
desperdiciado. Lambda + EventBridge además encajan con el patrón ya
usado en AWS FinOps Monitor, manteniendo coherencia de stack entre
proyectos.

**Terraform + pytest + GitHub Actions desde el principio.** El
objetivo es un repo que se pueda desplegar y verificar sin pasos
manuales ocultos, como se esperaría en un entorno de trabajo real.

**Un solo bucket S3 con prefijos `raw/` y `processed/`, no dos
buckets.** A esta escala (un archivo cada cierto tiempo) dos buckets
solo añadirían nombres que gestionar sin beneficio real. Un bucket con
prefijos simplifica el IAM y las políticas, y sigue permitiendo
filtrar por prefijo en las notificaciones de EventBridge (Fase 2).

**Budget de AWS con alerta desde el primer céntimo, no a fin de mes.**
El objetivo explícito es coste cero. Casi todo el stack (Lambda,
EventBridge, S3, Parameter Store estándar, SES, CloudWatch Logs) cae
en el always-free tier a este volumen de uso; la única pieza que no
tiene free tier perpetuo es **Amazon Bedrock** (Fase 3), que se paga
por token aunque sea céntimos. En vez de confiar en revisar la
consola de facturación, `aws_budgets_budget` (`terraform/budget.tf`)
manda un email en cuanto aparece cualquier cargo real (umbral al 1%
de un límite de 1 USD) y otro si el gasto previsto del mes va a
superar ese límite.

**Lambda sin dependencias de terceros, solo `boto3`.** El
procesamiento (parsing de CSV, validación, cálculo de métricas) es
lógica sencilla que la librería estándar de Python resuelve sin
necesidad de pandas. Evitarlo mantiene el paquete de despliegue
pequeño, sin paso de `pip install` antes de empaquetar, y sin el
cold-start extra que arrastra una dependencia pesada.

**`terraform-deploy` con `PowerUserAccess` + `IAMFullAccess`, no una
política a medida por recurso.** El objetivo inicial era una política
mínima solo para lo que cada fase necesita, pero crear el rol de la
Lambda requiere `iam:CreateRole`/`iam:PutRolePolicy`, que
`PowerUserAccess` bloquea a propósito. Para una cuenta personal de un
solo desarrollador, mantener una política de IAM recortada y
actualizarla en cada fase añade fricción sin beneficio de seguridad
real: el límite que importa aquí es no usar el usuario root a diario
y tener MFA en él, no la granularidad de `terraform-deploy`. Queda
anotado por si el proyecto creciera a un entorno multi-persona, donde
sí compensaría.

**El bucle EventBridge → Lambda no puede autodispararse.** La regla
filtra explícitamente por prefijo `raw/`; la Lambda solo escribe en
`processed/`. Así, sus propias escrituras nunca generan un nuevo
evento que la vuelva a disparar — sin esto, un fallo de diseño
trivial podría convertirse en un bucle de invocaciones sin fin (y
coste sin fin).

**`ssm:GetParametersByPath` necesita el recurso exacto, no solo el
comodín.** Durante la verificación end-to-end la Lambda fallaba con
`AccessDeniedException` pese a que la política incluía
`arn:.../parameter/vintedlens/dev/processing/*`. El motivo: IAM
evalúa `GetParametersByPath` contra la ruta exacta que se pide (sin
`/*` al final), mientras que `GetParameter` evalúa cada parámetro
hijo. Hace falta el recurso exacto **y** el comodín en la misma
política — con solo uno de los dos, falla. Documentado en
`terraform/lambda_processing.tf` para no repetir el error en futuras
Lambdas que lean Parameter Store.

**Claude Haiku 4.5 en vez de un modelo Nova.** El plan inicial era
Amazon Nova Micro por ser el más barato de Bedrock, pero no aparecía
como disponible en la cuenta/región al comprobarlo en la consola. Se
optó por Claude Haiku 4.5 ($1,10 / $5,50 por millón de tokens):
suficientemente barato para resumir unas pocas métricas (céntimos al
mes con cadencia semanal) y con disponibilidad confirmada en
`eu-west-1`.

**Los modelos de Anthropic en Bedrock no se invocan con el ID del
modelo directamente.** Hacen falta dos cosas que no son evidentes
desde la documentación de alto nivel:
1. Un **inference profile** (`eu.anthropic.claude-haiku-4-5-...`, no
   `anthropic.claude-haiku-4-5-...` a secas) — la invocación on-demand
   directa del modelo base no está soportada para este modelo. El
   prefijo `eu.` mantiene el tráfico dentro de la UE (Fráncfort,
   Estocolmo, Milán, España, Irlanda, París) en vez de enrutar
   globalmente.
2. La política IAM necesita permiso **tanto** sobre el ARN del
   inference profile **como** sobre el ARN del modelo base (con
   comodín de región, ya que el profile puede enrutar a cualquiera de
   esas regiones EU) — solo el profile no basta.
3. Un paso de cuenta, aparte de "Model access": Anthropic exige
   rellenar un formulario de "caso de uso" (`PutUseCaseForModelAccess`
   en la API de Bedrock) antes de la primera invocación. No aparece
   como un formulario obvio en la consola; se puede rellenar por API
   pasando `companyName`, `companyWebsite`, `intendedUsers` (código
   numérico: `"0"` interno / `"1"` externo), `industryOption` y
   `useCases` como JSON en base64.

**SES en modo sandbox, remitente = destinatario.** Una cuenta nueva
empieza en sandbox (solo se puede enviar a direcciones verificadas).
Como el informe es para un único destinatario (uno mismo), no hay
motivo para pedir salir del sandbox: verificar una sola identidad de
email y usarla como origen y destino del envío es suficiente y evita
un trámite adicional con AWS.

**Informe semanal por defecto, comparando con el anterior cuando
existe.** La Lambda de reporting no reacciona a cada CSV subido (eso
generaría un email por archivo); una regla EventBridge programada
(`rate(7 days)`, configurable) dispara el resumen periódico. Si hay
al menos dos snapshots de métricas en `processed/`, calcula el delta
de rotación y precio medio por categoría entre el más reciente y el
anterior, y se lo pasa a Bedrock para que lo mencione en el resumen
("bajó un X%"); en el primer informe, sin histórico, genera un
resumen del estado actual sin comparación.

**GitHub Actions se autentica con OIDC, no con access keys en
secrets.** Un rol IAM de confianza federada (`terraform/github_oidc.tf`)
solo puede asumirse desde workflows que corren dentro de
`M0r3n0SVQ/VintedLens`; las credenciales son temporales, por
invocación, y no hay ninguna access key de larga duración que rotar,
filtrar o revocar manualmente.

**`terraform apply` en CI/CD es manual (`workflow_dispatch`), no
automático en cada merge a main.** El objetivo del proyecto es coste
cero y cambios deliberados, no un pipeline que despliega infraestructura
real sin que nadie lo revise antes. `terraform plan` sí corre
automáticamente en cada PR que toca `terraform/` — se ve el diff antes
de fusionar — pero aplicar es siempre una acción explícita desde la
pestaña Actions. Coherente con cómo se ha trabajado en todas las fases
anteriores: plan primero, confirmación humana, apply después.

**`ruff` para linting, `pytest-cov` con un mínimo del 80%.** `ruff`
sustituye a flake8+isort+pyupgrade en una sola herramienta rápida,
sin más configuración que `line-length` y el set de reglas. El 80% de
cobertura es un umbral realista dado el código actual (86% en local):
dejar margen evita que el pipeline se rompa por líneas de manejo de
errores de SSM/Bedrock difíciles de testear con sentido, sin renunciar
a una cobertura real del código de negocio (parsing, métricas,
deltas, prompt).

**La política de confianza de OIDC usa el claim `sub` inmutable
(`repo:usuario@id_usuario/repo@id_repo`), no el formato clásico
solo-por-nombre.** GitHub cambió el formato por defecto del claim
`sub` para repos creados a partir del 15/07/2026 (este repo cae en
esa ventana): añade los IDs numéricos inmutables de usuario y repo,
para que un cambio de nombre no reasigne la confianza a otra cuenta.
Con la condición `repo:usuario/repo:*` de toda la documentación
"clásica" de AWS+GitHub OIDC, `sts:AssumeRoleWithWebIdentity` falla
con `Not authorized` aunque el resto de la configuración (rol,
proveedor OIDC, variable en GitHub) sea perfecta — no hay forma de
verlo sin decodificar un token real. Se depuró añadiendo
temporalmente un paso que decodifica el JWT del propio token OIDC y
publica sus claims como anotación del workflow.

## Plan de fases

El trabajo avanza de forma intermitente; cada fase termina en un
estado estable y funcional, sin depender de tiempo continuo.

- [x] **Fase 1 — Fundación**: estructura del repo, Terraform base,
  bucket S3 `raw/`, formato de CSV definido, ingesta simple. README
  con arquitectura y decisiones.
- [x] **Fase 2 — Procesamiento**: EventBridge + Lambda de limpieza y
  cálculo de métricas. Parameter Store para configuración. Tests con
  pytest. Bucket `processed/`.
- [x] **Fase 3 — IA + Reporting**: integración con Bedrock para el
  resumen en lenguaje natural. Lambda de reporting + envío por SES.
- [x] **Fase 4 — CI/CD y calidad**: GitHub Actions completo (tests +
  despliegue Terraform), linting, cobertura de tests, documentación
  final del README, diagrama de arquitectura actualizado.
- [x] **Fase 5 (opcional)** — Dashboard: API Gateway + frontend
  Next.js en Vercel, conectando con Plendu.

Las fases 1-4 son el proyecto completo para portfolio/CV. La fase 5
es prescindible.

## Estructura del repositorio

```
VintedLens/
├── terraform/
│   ├── versions.tf    # Terraform + providers requeridos
│   ├── providers.tf   # Provider AWS + default_tags
│   ├── variables.tf   # project / environment / owner / aws_region
│   ├── locals.tf      # Tags comunes
│   ├── s3.tf                    # Bucket de datos (raw/ + processed/)
│   ├── state.tf                 # Bucket de estado remoto de Terraform
│   ├── budget.tf                # Alerta de coste (guardarraíl de gasto cero)
│   ├── parameter_store.tf       # Config de procesamiento y reporting
│   ├── lambda_package.tf        # Zip de código compartido por las Lambdas
│   ├── lambda_processing.tf     # Lambda de procesamiento + rol IAM + log group
│   ├── eventbridge.tf           # Trigger raw/ -> EventBridge -> Lambda
│   ├── reporting.tf             # Lambda de reporting + SES + rol IAM + log group
│   ├── reporting_schedule.tf    # Disparo periódico (EventBridge programado)
│   ├── github_oidc.tf           # Rol OIDC para GitHub Actions (sin access keys)
│   ├── api.tf                   # API Gateway + Lambda del dashboard (Fase 5)
│   ├── terraform.tfvars.example  # Plantilla de variables locales
│   └── outputs.tf               # Nombres/ARNs de buckets, Lambdas, rol OIDC y API
├── data/
│   ├── schema.md       # Formato del CSV de inventario/ventas
│   └── samples/
│       └── inventory_sample.csv
├── src/
│   ├── processing/  # Lambda de procesamiento (parsing, métricas, handler)
│   ├── reporting/   # Lambda de reporting (deltas, prompt, Bedrock, SES)
│   └── api/         # Lambda de la API del dashboard (GET /metrics)
├── tests/                 # Tests pytest (funciones puras + integración con moto)
├── pyproject.toml         # Config de pytest + ruff
├── requirements-dev.txt   # Dependencias de test/lint (pytest, moto, ruff)
├── .github/workflows/
│   ├── ci.yml               # Lint + tests + terraform validate, en cada push/PR
│   ├── terraform-plan.yml   # terraform plan en PRs que tocan terraform/
│   └── terraform-apply.yml  # terraform apply manual (workflow_dispatch)
├── .gitignore
└── README.md
```

## Formato del CSV

El contrato de entrada del pipeline está documentado en
[`data/schema.md`](data/schema.md), con un ejemplo en
[`data/samples/inventory_sample.csv`](data/samples/inventory_sample.csv).

## Infraestructura (Terraform)

Requiere Terraform >= 1.11 (por el locking nativo del backend S3) y
credenciales AWS configuradas.

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars   # y rellena tu email real
terraform init
terraform plan
terraform apply
```

`terraform plan` se ejecuta siempre antes de `apply`, nunca se salta
este paso.

**Estado remoto**: `terraform.tfstate` vive en un bucket S3 dedicado
(`vintedlens-dev-tfstate-*`), versionado y cifrado, separado del
bucket de datos porque el estado puede contener valores sensibles y
tiene un ciclo de vida distinto. El locking usa el mecanismo nativo
de S3 (`use_lockfile`, Terraform >= 1.11) en vez de una tabla
DynamoDB — un recurso menos que mantener sin perder protección contra
`apply` concurrentes.

## Subir un CSV (ingesta manual, Fase 1)

```bash
aws s3 cp data/samples/inventory_sample.csv \
  s3://<data_bucket_name>/raw/inventory_$(date +%Y%m%d).csv \
  --profile <tu-perfil-aws>
```

`<data_bucket_name>` es el output `data_bucket_name` de `terraform
apply`. Esa subida dispara automáticamente el procesamiento vía
EventBridge: en segundos aparecen `<basename>_clean.csv` y
`<basename>_metrics.json` en `processed/`.

## Procesamiento (Fase 2)

La Lambda (`src/processing/`) valida cada fila del CSV contra
`data/schema.md` y calcula, por categoría y en global:

- **Precio medio**: media de `listing_price` (publicado) y de
  `sale_price` sobre lo vendido.
- **Tiempo en catálogo**: media de `sold_date - listed_date` en días,
  solo sobre artículos vendidos.
- **Rotación** (`sell_through_rate`): `vendidos / (vendidos +
  listados + reservados)`. Se excluye `removed` del denominador a
  propósito — un artículo retirado ya no compite por venderse, así
  que incluirlo penalizaría categorías donde se despublica por
  motivos ajenos a la demanda (cambio de temporada, error de
  publicación). Categorías con `sell_through_rate` por debajo del
  umbral de Parameter Store (`0.3` por defecto) se marcan
  `low_rotation: true`.

Las filas que incumplen el esquema (categoría no reconocida, fechas
inconsistentes, `sold` sin `sale_price`, etc.) no abortan el batch:
se registran en `row_errors` dentro del JSON de salida y el resto del
CSV se procesa igual.

### Tests

```bash
python -m venv .venv
./.venv/Scripts/pip install -r requirements-dev.txt   # Windows
# source .venv/bin/activate && pip install -r requirements-dev.txt  # Linux/Mac
python -m pytest
```

La lógica de parsing/métricas se testea como funciones puras, sin
AWS de por medio. El handler completo se testea con `moto`
(S3 mockeado en memoria), sin tocar la cuenta real.

## Reporting (Fase 3)

Una regla EventBridge programada (semanal por defecto) dispara la
Lambda de reporting (`src/reporting/`), que:

1. Lista `processed/` y coge el `*_metrics.json` más reciente (y el
   anterior, si existe, para calcular deltas), más el `*_clean.csv`
   correspondiente para tener los artículos reales, no solo agregados.
2. Elige hasta 8 artículos concretos para sugerencias individuales:
   solo los que siguen `listed` (vendidos/reservados/retirados no
   necesitan ayuda para venderse) en categorías con rotación baja,
   priorizando por precio de listado descendente — ahí hay más
   capital inmovilizado. Acota el prompt aunque el catálogo crezca.
3. Construye un prompt con las métricas, los deltas y esos artículos
   (con su título real), y pide a Bedrock (Claude Haiku 4.5 vía
   Converse API) un JSON estructurado: un resumen en español (máximo
   150 palabras) más una sugerencia concreta **por artículo**, no por
   categoría.
4. Envía el resumen (+ sugerencias en texto) por email vía SES.
5. Guarda el mismo resumen y sugerencias como `*_summary.json` en
   `processed/`, para que la API del dashboard (Fase 5) lo exponga
   también ahí, no solo por email.

**Por qué por artículo y no por categoría.** La primera versión daba
un consejo genérico por categoría ("añade marca y talla al título"),
pero sin ver los títulos reales acababa sugiriendo cosas que el
usuario ya hacía. Pasarle a Bedrock el título real de cada artículo
("Polo Fred Perry Twin Tipped blanco crema logo laurel bordado...")
le permite dar feedback que de verdad depende de lo que ya está
escrito — por ejemplo, señalar que falta la década/época en vez de
repetir que falta la marca, que ya está ahí.

### Requisitos únicos (una sola vez por cuenta AWS)

Antes de que la Lambda de reporting funcione hacen falta dos pasos
manuales que Terraform no puede hacer por ti:

1. **Verificar el email de SES**: `terraform apply` dispara el envío
   de un correo de verificación a `report_email`; hay que confirmarlo
   (revisa spam/promociones si no llega a la bandeja principal).
2. **Rellenar el formulario de caso de uso de Anthropic**: sin él,
   Bedrock devuelve `ResourceNotFoundException` con el mensaje *"Model
   use case details have not been submitted for this account"*. Se
   rellena una sola vez por cuenta, vía API:

```bash
python - <<'EOF'
import base64, json
form = {
    "companyName": "...",
    "companyWebsite": "...",
    "intendedUsers": "0",  # "0" interno, "1" externo
    "industryOption": "Retail",
    "otherIndustryOption": "",
    "useCases": "...",
}
print(base64.b64encode(json.dumps(form).encode()).decode())
EOF
# aws bedrock put-use-case-for-model-access --form-data <salida de arriba> --region eu-west-1
```

AWS avisa de que la propagación puede tardar hasta 15 minutos.

3. **Aceptar el acuerdo de AWS Marketplace del modelo**: sin esto,
   Bedrock devuelve `AccessDeniedException` — *"IAM user or service
   role is not authorized to perform the required AWS Marketplace
   actions (aws-marketplace:ViewSubscriptions, aws-marketplace:Subscribe)"* —
   incluso con `bedrock:InvokeModel` correctamente concedido. Los
   modelos de terceros en Bedrock (todos los de Anthropic incluidos)
   se sirven a través de una suscripción de AWS Marketplace que hay
   que aceptar explícitamente una vez por cuenta:

```bash
OFFER_TOKEN=$(aws bedrock list-foundation-model-agreement-offers \
  --model-id anthropic.claude-haiku-4-5-20251001-v1:0 --region eu-west-1 \
  --query 'offers[0].offerToken' --output text)

aws bedrock create-foundation-model-agreement \
  --model-id anthropic.claude-haiku-4-5-20251001-v1:0 \
  --offer-token "$OFFER_TOKEN" --region eu-west-1
```

Comprueba el estado con `aws bedrock get-foundation-model-availability
--model-id <id> --region <region>`: `agreementAvailability.status`
pasa de `NOT_AVAILABLE` a `PENDING` y, tras uno o dos minutos, a
`AVAILABLE`. Una vez aceptado, todos los roles IAM de la cuenta
pueden invocar el modelo sin necesitar permisos de Marketplace ellos
mismos — solo hace falta que alguien lo acepte una vez.

### Tests

Mismo comando que en Fase 2 (`python -m pytest`): `summarizer.py`
(deltas y construcción del prompt) se testea como funciones puras;
el handler se testea con `moto` para S3, y con dobles de prueba
(monkeypatch) para Bedrock y SES en vez de depender de que `moto` los
simule fielmente.

## CI/CD (Fase 4)

Tres workflows en `.github/workflows/`:

- **`ci.yml`**: en cada push/PR — lint (`ruff`), tests con cobertura
  mínima del 80%, y `terraform fmt -check` + `terraform validate`
  (sin credenciales AWS, solo sintaxis).
- **`terraform-plan.yml`**: en PRs que tocan `terraform/` — plan real
  contra AWS vía el rol OIDC, para ver el diff antes de fusionar.
- **`terraform-apply.yml`**: solo manual (`workflow_dispatch`, botón
  "Run workflow" en la pestaña Actions) — nunca automático en un
  merge.

### Configuración única del repo en GitHub (manual, no la hace Terraform)

1. **Secrets** (Settings → Secrets and variables → Actions → *Secrets*):
   - `BUDGET_ALERT_EMAIL`
   - `REPORT_EMAIL`
2. **Variable** (misma pantalla, pestaña *Variables* — no es secreta,
   es un ARN, no un credencial):
   - `AWS_ROLE_ARN` = output `github_actions_role_arn` de `terraform
     apply` (algo como
     `arn:aws:iam::<cuenta>:role/vintedlens-dev-github-actions`)

Sin esto, `terraform-plan.yml` y `terraform-apply.yml` fallan al
intentar asumir el rol o al faltarles las variables de Terraform —
`ci.yml` no necesita nada de esto, corre sin credenciales AWS.

## API del dashboard (Fase 5)

Un HTTP API de API Gateway (`GET /metrics`) delante de una Lambda que
devuelve el snapshot de métricas más reciente, un historial corto
(hasta 10 anteriores) y el resumen/sugerencias de IA más reciente
generado por la Lambda de reporting (`ai_summary`, puede ser `null`
si el reporting no se ha ejecutado todavía).

**Por qué HTTP API y no REST API.** REST API (v1) trae de serie API
keys + usage plans, pero para una sola ruta de solo lectura añade
complejidad (planes de uso, etapas, límites) que no aporta nada aquí.
HTTP API (v2) es más barato y simple; la protección se hace a mano
comparando un header `x-api-key` contra un valor en Parameter Store
(`SecureString`, generado por Terraform con `random_password`, nunca
escrito a mano) usando `hmac.compare_digest` para evitar timing
attacks.

**Sin CORS configurado, a propósito.** El dashboard en Next.js llama
a esta API desde el servidor (Server Components), nunca desde el
navegador. Así la clave vive solo en una
variable de entorno de servidor en Vercel y nunca llega al bundle de
cliente — si se llamara desde el navegador, la clave habría que
incluirla en el JS público, lo que anularía la protección.

```bash
curl -H "x-api-key: $(terraform output -raw api_key)" \
  "$(terraform output -raw api_endpoint)metrics"
```

## Stack técnico

AWS Lambda · Amazon EventBridge · Amazon S3 · Amazon API Gateway ·
AWS Systems Manager Parameter Store · Amazon Bedrock · Amazon SES ·
IAM (OIDC federado) · Terraform · Python + pytest + ruff ·
GitHub Actions · Next.js en Vercel

## Proyectos relacionados

- **AWS FinOps Monitor** — monitorización de costes AWS con el mismo
  stack serverless base.
- **Plendu** — SaaS en Next.js con IA (OpenAI gpt-4o-mini vision),
  cuyos patrones (Next.js + Vercel) reutiliza el dashboard de la
  Fase 5.
- **[vintedlens-dashboard](https://github.com/M0r3n0SVQ/vintedlens-dashboard)**
  — el frontend de la Fase 5, desplegado en Vercel.

*(Enlaces pendientes de añadir cuando los repos estén publicados.)*
