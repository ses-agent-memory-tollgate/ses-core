<div align="center">
  <h1>🧠 SES Agent Memory Tollgate</h1>
  <p><strong>Curated paid memory for autonomous agents.</strong></p>
  
  [![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org)
  [![License](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
  
  *[Agent docs (AGENTS.md)](AGENTS.md)*
</div>

---

**SES Agent Memory Tollgate** provides curated paid memory namespaces for autonomous agents.

Agents pay when they need fresh, cited and verifiable context to complete a goal. SES returns answer, citations, receipt and value_proof.

### Core Flow
`Discover → Quote → Pay → Retrieve → Cite → Receipt`

### Primary Interfaces
- **Hosted:** `ses-agent-sdk` for agent-payable API calls.
- **Local:** `ses.agent.RAG` for offline dev and local embedded memory.

---

## 🚀 Quickstart: Hosted B2A / x402 Tollgate (Cliente SDK)

Para agentes autónomos que consumen memoria semántica pagada por uso (`x402` HTTP + Solana Pay / USDC):

```python
from ses_sdk import SESClient

# Callback de billetera para firmar y procesar transferencias USDC en Solana Pay
def my_wallet_provider(amount_usdc: float, payment_data: dict) -> str:
    # Lógica del agente para validar los datos del pago y firmar con su llave privada
    # Debe retornar la firma de la transacción de Solana Pay (tx_signature)
    return "firma_de_transaccion_solana"

# Cliente de peaje B2A
client = SESClient(
    agent_id="my-agent-1", 
    api_url="http://localhost:8000",
    payment_provider=my_wallet_provider
)

# Consulta pagada (el SDK cotiza, paga vía x402 y recupera el resultado de forma automática)
response = client.query("What does SES do?")
print(response["answer"])
```

Para ver la especificación detallada optimizada para modelos, consulta [AGENTS.md](AGENTS.md).

---

## 🛠️ Quickstart: Uso Local (Motor Interno SES Core)

Si necesitas utilizar el motor RAG interno de forma local y gratuita para desarrollo offline (sin peajes ni criptomonedas):

```python
from ses.agent import RAG

# Motor RAG local y offline
rag = RAG()
rag.ingest("contrato.pdf")
respuesta = rag.query("¿Cuáles son las cláusulas de rescisión?")
print(respuesta)
```

---

## 🌟 ¿Por qué pagar por contexto en SES?

1. **Contexto ya indexado:** Evita que el agente gaste recursos y tiempo realizando la extracción e indexación de repositorios masivos de documentos.
2. **Menos pasos para el agente:** El SDK se encarga de negociar el peaje `x402` de manera transparente durante la ejecución del request.
3. **Citas verificables:** Cada consulta responde con metadatos y citas exactas que apuntan a la procedencia original del conocimiento.
4. **Sin montar infraestructura RAG:** Olvídate de levantar, mantener y configurar bases de datos vectoriales (Qdrant, Redis) en el entorno del agente.
5. **Receipt auditable por operación:** Obtén un recibo criptográfico en el ledger por cada llamada exitosa, útil para auditorías de costos de agentes.

---

## 🧭 Operating Modes

### 1. Local Embedded RAG
- SQLite + numpy
- no payments
- no external vector DB
- for development, offline tests and demos

### 2. Hosted Curated Tollgate
- Qdrant
- FastAPI Gateway
- payment middleware
- curated public technical namespaces

### 3. Future Private / Marketplace
- private BYOD namespaces
- publisher marketplace
- not part of current build

---

## Explicit Non-Goals
SES is not building a legal corpus in this roadmap.
SES is not building Lex Mex API.
SES is not opening a public marketplace yet.
SES is not building a human dashboard yet.
SES is not adding multi-chain billing yet.

---

## 📦 Instalación

### Instalar el SDK de Agente (Cliente)
```bash
pip install ses-agent-sdk
```

### Instalar el Servidor Tollgate (Hospedador de Memoria)
```bash
pip install ses-core[server]
```

---

## ⚙️ Configuración del Servidor Tollgate

El servidor se configura mediante variables de entorno en un archivo `.env`:

```env
# URL base pública expuesta en el Agent Card
SES_PUBLIC_BASE_URL=http://localhost:8000

# MODO DEBUG (true acepta proofs simulados solo para desarrollo)
DEBUG=true

# SQLite embebido por defecto. Cambiar a false para usar Qdrant/Redis.
EMBEDDED_MODE=true
```

Para iniciar el servidor Tollgate:
```bash
ses serve
```

### Docker quickstart verificado

Modo embedded local, sin Qdrant:

```bash
docker compose up -d --build gateway
curl http://127.0.0.1:8001/v1/health
```

Modo full local con Qdrant + Redis:

```bash
EMBEDDED_MODE=false docker compose --profile full up -d --build
curl http://127.0.0.1:8001/v1/health
```

En PowerShell:

```powershell
$env:EMBEDDED_MODE="false"
docker compose --profile full up -d --build
Invoke-RestMethod http://127.0.0.1:8001/v1/health
```

El modo full de Docker es una integración local con servicios sin credenciales. No equivale a producción remota.

### Curar y publicar `public:ses-docs`

```bash
ses curate build public:ses-docs --base-dir .
ses curate validate public:ses-docs --base-dir .
ses curate publish public:ses-docs --base-dir .
```

El publish usa `SentenceTransformer` y puede descargar el modelo `sentence-transformers/all-MiniLM-L6-v2` si no está en cache.

### Query local con pago simulado

Para desarrollo:

```bash
DEBUG=true EMBEDDED_MODE=true ses serve
```

Luego enviar una consulta con identidad de agente y proof simulado:

```bash
curl -X POST http://127.0.0.1:8000/v1/query \
  -H "Content-Type: application/json" \
  -H "X-Agent-Id: demo-agent" \
  -H "X-Payment-Proof: simulated-demo" \
  -H "Idempotency-Key: demo-query-1" \
  -d '{"question":"What does SES do?","namespace":"public:ses-docs","top_k":3}'
```

La respuesta esperada contiene `answer`, `citations`, `receipt` y `value_proof`. El `receipt.response_hash` compromete criptográficamente el contenido central de la respuesta. Si Ollama no está disponible, el proveedor LLM local cae a respuesta fallback; eso sirve para desarrollo, no para demostrar calidad LLM productiva.

### Solana USDC mint por red (devnet / mainnet-beta)

SolanaPay resuelve automáticamente el mint de USDC correcto según `SOLANA_NETWORK`:

- **mainnet-beta** (default): `EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v`
- **devnet**: `4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU` (Circle faucet)

`USDC_MINT` siempre tiene precedencia si se define explícitamente.

Ejemplo para pruebas reales en devnet (usa `merchant.env` o variables de entorno):

```env
DEBUG=false
SOLANA_NETWORK=devnet
SOLANA_RPC_URL=https://api.devnet.solana.com
USDC_MINT=4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU
SOLANA_MERCHANT_SECRET=<tu_base58_secret>
```

Ejemplo producción mainnet:

```env
DEBUG=false
SOLANA_NETWORK=mainnet-beta
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
USDC_MINT=EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v
SOLANA_MERCHANT_SECRET=<tu_base58_secret>
```

Verifica una transferencia real:

```bash
python scripts/verify_merchant_payment.py <signature> 20.0
```

El script imprime la configuración resuelta (network, mint, rpc) y sale con código 0 solo si `verified=True`.

**Importante:** carga el archivo de entorno *antes* de importar `SolanaPay` (los scripts lo hacen).

---

## Estado de release

Este paquete está marcado como **Beta**. No se debe afirmar producción comercial hasta que CI, Docker, security scans y verificación de pagos reales pasen en el entorno de release objetivo.

---

## 🏗️ Estructura del Proyecto

El motor interno **SES Core** está dividido en los siguientes módulos:

```text
ses/
├── core/
│   ├── parsers.py       # Extractores de texto (PDF, DOCX, XLSX, TXT)
│   ├── chunking.py      # Fragmentación semántica local
│   ├── embeddings.py    # Envolturas de SentenceTransformers
│   └── rag.py           # Orquestador del motor RAG local
├── curation/            # Curation Engine para procesar los namespaces
├── discovery/
│   └── card.py          # Definición del Agent Card (Capacidades, interfaces y precios)
├── payments/
│   ├── solana_pay.py    # Verificación de transacciones USDC en Solana
│   └── receipts.py      # Ledger interno de recibos e idempotencia
└── server/
    ├── app.py           # Configuración de FastAPI y middleware x402
    ├── middleware.py    # Enforzamiento del protocolo de pago requerido (402)
    └── routes.py        # Endpoints REST (/v1/quote, /v1/query, /v1/receipt)
```

Además, el repositorio incluye:
- `ses-agent-sdk/`: SDK oficial para conectar agentes a la memoria.
- `ses-portal/`: Portal de documentación interactivo construido en React/Vite.
- `docker-compose.yml`: Archivos oficiales para orquestación de contenedores.
