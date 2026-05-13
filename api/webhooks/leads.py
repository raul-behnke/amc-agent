"""
Endpoint de Qualificação — Consulta o estado do lead.

Permite que o dashboard ou outros sistemas consultem
o progresso de qualificação de um lead específico.
"""

from fastapi import APIRouter

from state.lead_model import LeadQualification
from tools.qualification import _get_lead

router = APIRouter(prefix="/leads", tags=["leads"])


@router.get("/{session_id}/qualification")
async def get_lead_qualification(session_id: str) -> dict:
    """Retorna os dados de qualificação de um lead."""
    lead = _get_lead(session_id)
    return {
        "session_id": session_id,
        "status": lead.status.value,
        "score": lead.completeness_score(),
        "qualification": lead.to_dict(),
    }
