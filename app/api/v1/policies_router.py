"""
V1 Policy management API — generate, list, edit, approve policies.
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.api.v1.auth import require_api_key
from app.infrastructure.database import get_db
from app.modules.policies.models import ClientPolicy
from app.modules.policies.generator import PolicyGenerator, POLICY_TYPES

logger = logging.getLogger(__name__)

router = APIRouter()


class GeneratePoliciesRequest(BaseModel):
    client_id: str
    company_name: str
    legal_address: str = ""
    support_email: str = ""
    site_url: str = ""
    jurisdiction: str = "GENERAL"  # EU, UK, CY, US, GENERAL
    language: str = "English"
    policies: List[str]  # e.g. ["privacy", "terms", "refund"]


class PolicyResponse(BaseModel):
    id: str
    client_id: str
    policy_type: str
    content_html: str
    jurisdiction: str
    language: str
    version: int
    status: str


class UpdatePolicyRequest(BaseModel):
    content_html: str


@router.post("/generate", response_model=List[PolicyResponse], summary="Generate missing policies")
async def generate_policies(
    request: GeneratePoliciesRequest,
    _api_key: str = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    """Generate missing compliance policies using Gemini AI."""
    # Validate policy types
    invalid = [p for p in request.policies if p not in POLICY_TYPES]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid policy types: {invalid}. Valid: {list(POLICY_TYPES.keys())}",
        )

    generator = PolicyGenerator()
    results = await generator.generate_missing_policies(
        missing_types=request.policies,
        company_name=request.company_name,
        legal_address=request.legal_address,
        support_email=request.support_email,
        site_url=request.site_url,
        jurisdiction=request.jurisdiction,
        language=request.language,
        client_id=request.client_id,
        db=db,
    )

    return [PolicyResponse(**r) for r in results]


@router.get("/{client_id}", response_model=List[PolicyResponse], summary="List client policies")
async def list_policies(
    client_id: str,
    _api_key: str = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    """List all policies for a client."""
    stmt = select(ClientPolicy).where(ClientPolicy.client_id == client_id)
    result = await db.execute(stmt)
    policies = result.scalars().all()
    return [
        PolicyResponse(
            id=p.id,
            client_id=p.client_id,
            policy_type=p.policy_type,
            content_html=p.content_html,
            jurisdiction=p.jurisdiction,
            language=p.language,
            version=p.version,
            status=p.status,
        )
        for p in policies
    ]


@router.get("/{client_id}/{policy_id}", summary="Get single policy")
async def get_policy(
    client_id: str,
    policy_id: str,
    _api_key: str = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    """Get a single policy by ID."""
    stmt = select(ClientPolicy).where(
        ClientPolicy.id == policy_id,
        ClientPolicy.client_id == client_id,
    )
    result = await db.execute(stmt)
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found.")
    return PolicyResponse(
        id=policy.id,
        client_id=policy.client_id,
        policy_type=policy.policy_type,
        content_html=policy.content_html,
        jurisdiction=policy.jurisdiction,
        language=policy.language,
        version=policy.version,
        status=policy.status,
    )


@router.put("/{client_id}/{policy_id}", summary="Edit policy text")
async def update_policy(
    client_id: str,
    policy_id: str,
    request: UpdatePolicyRequest,
    _api_key: str = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    """Edit a policy's HTML content before approving."""
    stmt = select(ClientPolicy).where(
        ClientPolicy.id == policy_id,
        ClientPolicy.client_id == client_id,
    )
    result = await db.execute(stmt)
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found.")

    policy.content_html = request.content_html
    policy.version += 1
    await db.commit()

    return {"message": "Policy updated", "version": policy.version}


@router.post("/{client_id}/{policy_id}/approve", summary="Approve policy for publishing")
async def approve_policy(
    client_id: str,
    policy_id: str,
    _api_key: str = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    """Approve a policy — the widget will start serving it."""
    from datetime import datetime, timezone

    stmt = select(ClientPolicy).where(
        ClientPolicy.id == policy_id,
        ClientPolicy.client_id == client_id,
    )
    result = await db.execute(stmt)
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found.")

    policy.status = "approved"
    policy.approved_at = datetime.now(timezone.utc)
    await db.commit()

    return {"message": "Policy approved and published", "policy_id": policy_id, "status": "approved"}


@router.delete("/{client_id}/{policy_id}", summary="Delete a policy")
async def delete_policy(
    client_id: str,
    policy_id: str,
    _api_key: str = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    """Delete a client policy."""
    stmt = select(ClientPolicy).where(
        ClientPolicy.id == policy_id,
        ClientPolicy.client_id == client_id,
    )
    result = await db.execute(stmt)
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found.")

    await db.delete(policy)
    await db.commit()

    return {"message": "Policy deleted", "policy_id": policy_id}
