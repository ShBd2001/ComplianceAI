from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, Type

from dotenv import load_dotenv
try:
    from groq import Groq
except Exception:
    Groq = None
from pydantic import BaseModel, ValidationError

from fallback_data import build_fallback_context, build_fallback_questionnaire, fallback_domain_analysis, fallback_orchestrator
from prompts import CONTEXT_PROMPT, DOMAIN_ANALYSIS_PROMPT, ORCHESTRATOR_PROMPT, QUESTIONNAIRE_PROMPT
from schemas import ContextPack, DomainOutput, OrchestratorOutput, QuestionnairePack

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=False)

DEFAULT_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


class BackendError(RuntimeError):
    pass


def get_backend_api_key() -> str | None:
    key = os.getenv("GROQ_API_KEY")
    if key:
        return key
    try:
        import streamlit as st

        secret_key = st.secrets.get("GROQ_API_KEY")
        if secret_key:
            return str(secret_key)
    except Exception:
        pass
    return None


def get_client() -> Groq:
    if Groq is None:
        raise BackendError("SDK LLM indisponible sur le serveur.")
    key = get_backend_api_key()
    if not key:
        raise BackendError("Configuration serveur incomplète.")
    return Groq(api_key=key)


def _schema_instruction(schema: Type[BaseModel]) -> str:
    return (
        "Le JSON doit respecter exactement ce schéma:\n"
        + json.dumps(schema.model_json_schema(), ensure_ascii=False, indent=2)
    )


def _call_json(model: str, prompt: str, payload: Dict[str, Any], schema: Type[BaseModel]) -> BaseModel:
    client = get_client()
    last_error: Exception | None = None
    user_payload = json.dumps(payload, ensure_ascii=False)
    system_prompt = prompt + "\n\n" + _schema_instruction(schema)

    for _ in range(2):
        try:
            response = client.chat.completions.create(
                model=model,
                temperature=0.2,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_payload},
                ],
            )
            content = response.choices[0].message.content or "{}"
            return schema.model_validate_json(content)
        except (ValidationError, json.JSONDecodeError) as exc:
            last_error = exc
            user_payload = json.dumps(
                {
                    "payload": payload,
                    "repair_instruction": "Corrige le JSON et renvoie uniquement un objet strictement conforme au schéma.",
                },
                ensure_ascii=False,
            )
        except Exception as exc:
            raise BackendError(f"Appel LLM impossible: {exc}") from exc
    raise BackendError(f"Réponse LLM inexploitable: {last_error}")


def _filter_questions(questionnaire: QuestionnairePack, domain: str) -> list[dict]:
    return [q.model_dump() for q in questionnaire.questions if q.domain == domain]


def generate_context_pack(profile: Dict[str, Any], model: str = DEFAULT_MODEL) -> tuple[ContextPack, str]:
    try:
        parsed = _call_json(model, CONTEXT_PROMPT, {"profile": profile}, ContextPack)
        return parsed, "live_groq"
    except Exception:
        return build_fallback_context(profile), "fallback"


def generate_questionnaire(profile: Dict[str, Any], context: ContextPack, model: str = DEFAULT_MODEL) -> tuple[QuestionnairePack, str]:
    try:
        parsed = _call_json(
            model,
            QUESTIONNAIRE_PROMPT,
            {"profile": profile, "context": context.model_dump()},
            QuestionnairePack,
        )
        return parsed, "live_groq"
    except Exception:
        return build_fallback_questionnaire(profile, context), "fallback"


def analyze_domain(domain: str, profile: Dict[str, Any], context: ContextPack, questionnaire: QuestionnairePack, answers: Dict[str, str], model: str = DEFAULT_MODEL) -> tuple[DomainOutput, str]:
    payload = {
        "profile": profile,
        "context": context.model_dump(),
        "domain": domain,
        "questions": _filter_questions(questionnaire, domain),
        "answers": {k: v for k, v in answers.items() if k in {q.id for q in questionnaire.questions if q.domain == domain}},
    }
    try:
        parsed = _call_json(model, DOMAIN_ANALYSIS_PROMPT, payload, DomainOutput)
        return parsed, "live_groq"
    except Exception:
        return fallback_domain_analysis(domain, profile, questionnaire.questions, answers), "fallback"


def orchestrate(profile: Dict[str, Any], context: ContextPack, questionnaire: QuestionnairePack, analyses: Iterable[DomainOutput], model: str = DEFAULT_MODEL) -> tuple[OrchestratorOutput, str]:
    analyses_list = list(analyses)
    payload = {
        "profile": profile,
        "context": context.model_dump(),
        "questionnaire": [q.model_dump() for q in questionnaire.questions],
        "analyses": [a.model_dump() for a in analyses_list],
    }
    try:
        parsed = _call_json(model, ORCHESTRATOR_PROMPT, payload, OrchestratorOutput)
        return parsed, "live_groq"
    except Exception:
        return fallback_orchestrator(profile, analyses_list), "fallback"


def run_full_assessment(profile: Dict[str, Any], answers: Dict[str, str], model: str = DEFAULT_MODEL) -> Dict[str, Any]:
    context, context_mode = generate_context_pack(profile, model=model)
    questionnaire, questionnaire_mode = generate_questionnaire(profile, context, model=model)

    analyses = {}
    modes = [context_mode, questionnaire_mode]
    for domain in ["CYBER", "RGPD", "RSE"]:
        result, mode = analyze_domain(domain, profile, context, questionnaire, answers, model=model)
        analyses[domain.lower()] = result
        modes.append(mode)

    orchestrator, orchestration_mode = orchestrate(profile, context, questionnaire, analyses.values(), model=model)
    modes.append(orchestration_mode)

    return {
        "context": context,
        "questionnaire": questionnaire,
        "cyber": analyses["cyber"],
        "rgpd": analyses["rgpd"],
        "rse": analyses["rse"],
        "orchestrator": orchestrator,
        "meta": {
            "model": model,
            "mode": "live_groq" if all(m == "live_groq" for m in modes) else "fallback_mixte" if "live_groq" in modes else "fallback",
        },
    }
