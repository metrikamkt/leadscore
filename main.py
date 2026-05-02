import logging
import os

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse

from facebook_api import get_lead_data, parse_lead_fields, send_capi_event
from scoring import calculate_score

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)

VERIFY_TOKEN = os.environ["VERIFY_TOKEN"]
PAGE_ACCESS_TOKEN = os.environ["PAGE_ACCESS_TOKEN"]
PIXEL_ID = os.environ["PIXEL_ID"]
CAPI_ACCESS_TOKEN = os.environ["CAPI_ACCESS_TOKEN"]
GOOD_LEAD_THRESHOLD = int(os.getenv("GOOD_LEAD_THRESHOLD", "7"))

app = FastAPI(title="Lead Score")


async def process_lead(leadgen_id: str) -> None:
    try:
        lead_data = await get_lead_data(leadgen_id, PAGE_ACCESS_TOKEN)
        fields = parse_lead_fields(lead_data)
        score, breakdown = calculate_score(fields)

        log.info("Lead %s | score=%d/10 | %s", leadgen_id, score, breakdown)

        if score > GOOD_LEAD_THRESHOLD:
            log.info("Lead %s qualificado (%d/10) — disparando conversão", leadgen_id, score)
            result = await send_capi_event(
                pixel_id=PIXEL_ID,
                access_token=CAPI_ACCESS_TOKEN,
                lead_fields=fields,
                score=score,
                lead_id=leadgen_id,
            )
            log.info("CAPI OK: %s", result)
        else:
            log.info("Lead %s não qualificado (%d/10) — nenhuma ação", leadgen_id, score)

    except Exception:
        log.exception("Erro processando lead %s", leadgen_id)


# ── Webhook Facebook ──────────────────────────────────────────────────────────

@app.get("/webhook")
async def verify_webhook(request: Request) -> PlainTextResponse:
    params = dict(request.query_params)
    if params.get("hub.mode") == "subscribe" and params.get("hub.verify_token") == VERIFY_TOKEN:
        log.info("Webhook verificado")
        return PlainTextResponse(params["hub.challenge"])
    raise HTTPException(status_code=403, detail="Token inválido")


@app.post("/webhook")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks) -> dict:
    body = await request.json()
    log.info("Webhook recebido: %s", body)

    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            if change.get("field") == "leadgen":
                leadgen_id = change["value"]["leadgen_id"]
                background_tasks.add_task(process_lead, leadgen_id)

    return {"status": "ok"}


# ── Utilitários ───────────────────────────────────────────────────────────────

@app.get("/debug-lead/{leadgen_id}")
async def debug_lead(leadgen_id: str) -> dict:
    """Mostra dados brutos do lead + score calculado. Use para descobrir os field names do seu formulário."""
    lead_data = await get_lead_data(leadgen_id, PAGE_ACCESS_TOKEN)
    fields = parse_lead_fields(lead_data)
    score, breakdown = calculate_score(fields)
    return {
        "leadgen_id": leadgen_id,
        "campos_brutos": fields,
        "score": score,
        "detalhamento": breakdown,
    }


@app.get("/test-capi")
async def test_capi() -> dict:
    """Dispara um LeadQualificado de teste para registrar o evento no pixel do Facebook."""
    fake_fields = {
        "email": "teste@metrika.com",
        "phone_number": "11999999999",
        "full_name": "Lead Teste",
    }
    result = await send_capi_event(
        pixel_id=PIXEL_ID,
        access_token=CAPI_ACCESS_TOKEN,
        lead_fields=fake_fields,
        score=8,
        lead_id="test_lead_000",
    )
    return {"status": "evento disparado", "resposta_facebook": result}


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
