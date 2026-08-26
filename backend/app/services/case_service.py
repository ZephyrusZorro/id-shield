"""Case management service."""
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Case

CASE_NUMBER_START = 1000


def next_case_number(db: Session) -> int:
    current_max = db.scalar(select(func.max(Case.case_number)))
    return (current_max or CASE_NUMBER_START) + 1


def create_case(db: Session, case_name: str) -> Case:
    # Retry on unique-constraint collisions so two concurrent creates
    # (same max number) cannot surface as an unhandled 500.
    for _ in range(3):
        case = Case(
            case_number=next_case_number(db),
            case_name=case_name.strip(),
            status="draft",
        )
        db.add(case)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            continue
        db.refresh(case)
        return case
    raise RuntimeError("Could not allocate a unique case number.")


def get_case(db: Session, case_id: str) -> Case | None:
    return db.get(Case, case_id)


def list_cases(db: Session, limit: int = 100) -> list[Case]:
    return list(
        db.scalars(select(Case).order_by(Case.case_number.desc()).limit(limit)).all()
    )
