"""Business logic for report creation and validation."""

from fastapi import HTTPException, status

from app.core.database import get_async_db
from app.core.enums import Provider, ReportStatus
from app.core.progress import init as init_progress
from app.models.report import Report
from app.models.user import User
from app.services.providers import MODELS
from app.tasks import run_analysis


def validate_models(model_keys: list[str]) -> None:
    """Raise 400 if any model key is not in the registry."""
    for mk in model_keys:
        if mk not in MODELS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown model: {mk}",
            )


def validate_provider_keys(user: User, model_keys: list[str]) -> None:
    """Raise 400 if the user is missing API keys for the required providers."""
    has_key = bool(user.api_keys) or user.encrypted_api_key is not None
    if not has_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please add at least one API key before running an analysis.",
        )

    required_providers = {MODELS[mk]["provider"] for mk in model_keys}
    available_providers = set(user.api_keys.keys())
    if user.encrypted_api_key:
        available_providers.add(Provider.ANTHROPIC)
    missing = required_providers - available_providers
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing API keys for: {', '.join(missing)}. Add them in settings.",
        )


async def create_report(
    user: User,
    brand: str,
    competitors: list[str],
    model_keys: list[str],
) -> dict:
    """Validate inputs, persist a new report, seed progress, and dispatch analysis.

    Returns the report as a dict for the response.
    """
    validate_models(model_keys)
    validate_provider_keys(user, model_keys)

    db = get_async_db()
    report = Report(
        user_id=user.id,
        brand=brand,
        competitors=competitors,
        models=model_keys,
        status=ReportStatus.PROCESSING,
    )
    await db.reports.insert_one(report.to_doc())

    init_progress(report.id, model_keys)
    run_analysis.delay(report.id, report.brand, report.competitors, user.id, model_keys)

    return report.model_dump()
