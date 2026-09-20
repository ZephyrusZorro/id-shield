"""Cross-document comparison response schemas."""
from pydantic import BaseModel


class ComparisonValue(BaseModel):
    document_id: str
    file_name: str
    raw_value: str
    normalized_value: str | None
    confidence: float | None
    agrees: bool  # agrees with the majority/reference cluster


class RuleEvaluationItem(BaseModel):
    rule_id: str
    rule_name: str
    category: str  # identity | chronological | cross_document | structural
    status: str  # pass | warning | fail | not_applicable
    severity: str  # info | low | medium | high
    confidence: float
    explanation: str
    evidence: dict | None = None


class ComparisonFieldRow(BaseModel):
    field_name: str
    label: str
    status: str  # consistent | mismatch | single_source
    severity: str | None  # high | medium when mismatched
    explanation: str | None = None
    similarity: float | None = None
    values: list[ComparisonValue]


class OtherDocValue(BaseModel):
    doc_id: str
    doc_name: str
    doc_type: str | None = None
    value: str


class EvidenceFusionRow(BaseModel):
    field_name: str
    label: str
    ocr_value: str | None = None
    ocr_confidence: float | None = None
    qr_value: str | None = None
    qr_confidence: float | None = None
    mrz_value: str | None = None
    mrz_confidence: float | None = None
    other_docs: list[OtherDocValue] = []
    consensus_value: str | None = None
    agreement_status: str = "single_source"  # unanimous | majority_conflict | mismatch | single_source
    conflict_summary: str | None = None
    caution_level: str = "normal"  # normal | elevated | high


class GraphNode(BaseModel):
    id: str
    label: str
    type: str  # person | document | field
    status: str = "neutral"  # verified | mismatch | warning | neutral
    value: str | None = None
    confidence: float | None = None
    details: dict | None = None


class GraphEdge(BaseModel):
    source: str
    target: str
    label: str | None = None
    status: str = "neutral"  # agree | conflict | neutral


class EvidenceGraphData(BaseModel):
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []


class CaseComparisonResponse(BaseModel):
    case_id: str
    fields: list[ComparisonFieldRow]
    rules_evaluated: list[RuleEvaluationItem] = []
    overall_name_similarity: float | None = None
    fusion_matrix: list[EvidenceFusionRow] = []
    evidence_graph: EvidenceGraphData | None = None

