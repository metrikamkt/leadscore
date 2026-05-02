import hashlib
import time

import httpx

GRAPH_VERSION = "v19.0"
GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_VERSION}"


async def get_lead_data(leadgen_id: str, page_access_token: str) -> dict:
    url = f"{GRAPH_BASE}/{leadgen_id}"
    params = {
        "access_token": page_access_token,
        "fields": "field_data,created_time,ad_id,form_id",
    }
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json()


def parse_lead_fields(lead_data: dict) -> dict:
    fields: dict[str, str] = {}
    for field in lead_data.get("field_data", []):
        name: str = field.get("name", "")
        values: list = field.get("values", [])
        fields[name] = values[0] if values else ""
    return fields


def _sha256(value: str) -> str:
    return hashlib.sha256(value.lower().strip().encode()).hexdigest()


async def send_capi_event(
    pixel_id: str,
    access_token: str,
    lead_fields: dict,
    score: int,
    lead_id: str,
) -> dict:
    url = f"{GRAPH_BASE}/{pixel_id}/events"

    user_data: dict = {}

    email = lead_fields.get("email", "")
    if email:
        user_data["em"] = [_sha256(email)]

    phone = lead_fields.get("phone_number", lead_fields.get("phone", ""))
    if phone:
        phone_digits = "".join(filter(str.isdigit, phone))
        if phone_digits:
            user_data["ph"] = [_sha256(phone_digits)]

    full_name = lead_fields.get("full_name", "")
    if full_name:
        parts = full_name.strip().split()
        user_data["fn"] = [_sha256(parts[0])]
        if len(parts) > 1:
            user_data["ln"] = [_sha256(" ".join(parts[1:]))]

    payload = {
        "data": [
            {
                "event_name": "LeadQualificado",
                "event_time": int(time.time()),
                "action_source": "website",
                "user_data": user_data,
                "custom_data": {
                    "lead_score": score,
                    "currency": "BRL",
                    "lead_id": lead_id,
                },
            }
        ],
        "access_token": access_token,
    }

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        return response.json()
