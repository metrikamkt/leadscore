# Mapeamento: field_name do Facebook → chave interna
# IMPORTANTE: O Facebook gera nomes de campo baseados no texto da pergunta.
# Use o endpoint GET /debug-lead/{leadgen_id} para ver os nomes exatos do seu formulário.
FIELD_MAP = {
    # Variações comuns — ajuste conforme o retorno do /debug-lead
    "qual_e_o_faturamento_medio_mensal_da_sua_empresa": "faturamento",
    "faturamento_medio_mensal_da_sua_empresa": "faturamento",
    "faturamento_medio_mensal": "faturamento",
    "sua_empresa_ja_vende_todos_os_dias": "vende",
    "empresa_ja_vende_todos_os_dias": "vende",
    "voce_ja_investe_em_marketing_ou_trafego_pago": "marketing",
    "ja_investe_em_marketing_ou_trafego_pago": "marketing",
    "investe_em_marketing_ou_trafego_pago": "marketing",
    "qual_e_o_seu_principal_objetivo_agora": "objetivo",
    "principal_objetivo_agora": "objetivo",
    "seu_principal_objetivo_agora": "objetivo",
}

SCORE_TABLE: dict[str, dict[str, int]] = {
    "faturamento": {
        "ainda não faturo": 0,
        "r$ 1.000 - r$ 5.000": 1,
        "r$ 6.000 - r$ 50.000": 2,
        "r$ 50.000 - r$ 100.000": 3,
        "+ r$ 100.000": 4,
    },
    "vende": {
        "ainda não": 0,
        "sim, mas de forma irregular": 1,
        "sim, com consistência": 2,
    },
    "marketing": {
        "nunca investi": 0,
        "sim, mas sem muitos resultados": 1,
        "sim, e já tenho experiência": 2,
    },
    "objetivo": {
        "outro": 0,
        "estruturar o time de vendas": 1,
        "aumentar o ticket médio": 2,
        "atrair mais clientes": 2,
    },
}


def calculate_score(raw_fields: dict) -> tuple[int, dict]:
    normalized: dict[str, str] = {}
    for fb_field, internal_key in FIELD_MAP.items():
        value = raw_fields.get(fb_field, "").lower().strip()
        if value and internal_key not in normalized:
            normalized[internal_key] = value

    score = 0
    breakdown: dict[str, dict] = {}
    for key, table in SCORE_TABLE.items():
        answer = normalized.get(key, "")
        points = table.get(answer, 0)
        score += points
        breakdown[key] = {"resposta": answer or "(não mapeada)", "pontos": points}

    return score, breakdown
