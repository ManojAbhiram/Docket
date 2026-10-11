"""What this server can do, for the screens that offer a choice (ADR-0015)."""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.auth.deps import current_user, get_settings_from_app
from app.core.config import Settings
from app.core.errors import ErrorEnvelope

router = APIRouter(tags=["capabilities"])


class CapabilitiesOut(BaseModel):
    """`vision` is true only when a key and a model are configured. Neither is ever returned."""

    vision: bool


@router.get(
    "/capabilities",
    response_model=CapabilitiesOut,
    dependencies=[Depends(current_user)],
    responses={401: {"model": ErrorEnvelope}},
)
async def capabilities(
    settings: Annotated[Settings, Depends(get_settings_from_app)],
) -> CapabilitiesOut:
    """Whether the opt-in OpenRouter Vision reader can be chosen on upload."""
    return CapabilitiesOut(vision=settings.vision_configured)
