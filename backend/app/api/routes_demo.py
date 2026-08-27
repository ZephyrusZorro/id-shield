"""Demo endpoints — one-click signature case + synthetic dataset seeding."""
from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.schemas.cases import CaseCreated
from app.services import case_service, demo_service
from app.services.pipeline import analyze_case

router = APIRouter()


@router.post("/demo/signature-case", response_model=CaseCreated, status_code=201)
def load_signature_case(
    background_tasks: BackgroundTasks, db: Session = Depends(get_db)
) -> CaseCreated:
    """Create the synthetic Rahul Sharma case and start its analysis."""
    case = demo_service.create_signature_case(db)
    background_tasks.add_task(analyze_case, case.id)
    return CaseCreated(
        id=case.id,
        case_number=case.case_number,
        case_name=case.case_name,
        status="processing",
    )
