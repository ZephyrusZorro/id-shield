"""Unit and integration tests for ID-SHIELD Analytics & Intelligence."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base, get_db
from app.db.models import Case, CrossDocumentFinding, Document, ExtractedField
from app.main import app
from app.services import analytics_service


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_analytics_empty_db_baseline(db_session: Session):
    """Analytics gracefully handles an empty or sparse DB with realistic baseline metrics."""
    data = analytics_service.get_analytics_data(db_session, time_range="30d")
    assert data.kpis.total_cases > 0
    assert data.kpis.pass_rate >= 0
    assert len(data.volume_trends) > 0
    assert len(data.risk_distribution) == 4
    assert len(data.mismatch_fields) > 0
    assert len(data.document_types) > 0
    assert len(data.forensic_signals) > 0
    assert len(data.stage_latencies) > 0
    assert len(data.insights) > 0
    assert data.is_synthetic_baseline is True


def test_analytics_with_actual_cases(db_session: Session):
    """Verify analytics accounts for seeded cases."""
    # Seed 2 cases
    case1 = Case(case_name="Valid Case A", case_number=101, status="completed", overall_risk=12, recommendation="verification_passed")
    case2 = Case(case_name="Fraud Case B", case_number=102, status="completed", overall_risk=85, recommendation="manual_review_required")
    db_session.add_all([case1, case2])
    db_session.commit()

    # Add a cross-document finding
    finding = CrossDocumentFinding(
        case_id=case2.id,
        field_name="date_of_birth",
        severity="high",
        explanation="DOB mismatch between Passport and National ID",
    )
    db_session.add(finding)
    db_session.commit()

    data = analytics_service.get_analytics_data(db_session, time_range="7d")
    assert data.kpis.total_cases >= 2
    assert any(f.field_name == "date_of_birth" for f in data.mismatch_fields)


def test_analytics_api_endpoint(client: TestClient):
    """Test GET /api/analytics HTTP endpoint."""
    response = client.get("/api/analytics?time_range=30d")
    assert response.status_code == 200
    json_data = response.json()
    assert "kpis" in json_data
    assert "volume_trends" in json_data
    assert "risk_distribution" in json_data
    assert "mismatch_fields" in json_data
    assert "document_types" in json_data
    assert "forensic_signals" in json_data
    assert "stage_latencies" in json_data
    assert "insights" in json_data
    assert json_data["time_range"] == "30d"


def test_analytics_export_endpoint(client: TestClient):
    """Test GET /api/analytics/export CSV endpoint."""
    response = client.get("/api/analytics/export?time_range=30d")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    csv_text = response.text
    assert "ID-SHIELD FORENSICS & INTELLIGENCE AUDIT EXPORT" in csv_text
    assert "METRIC,VALUE" in csv_text
    assert "Total Cases Screened" in csv_text
