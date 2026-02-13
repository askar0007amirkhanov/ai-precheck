from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database import get_db
from app.modules.policies.service import PolicyService
from app.modules.policies.schemas import WidgetResponse

router = APIRouter()

@router.get("/content/{client_id}", response_model=WidgetResponse)
async def get_widget_content(
    client_id: str,
    db: AsyncSession = Depends(get_db)
):
    service = PolicyService(db)
    try:
        return await service.get_widget_content(client_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
