export interface HealthResponse {
  status: string;
  app: string;
  version: string;
  tagline: string;
  time: string;
}

export interface DashboardSummary {
  total_screened: number;
  valid: number;
  under_review: number;
  high_risk: number;
  average_risk_score: number | null;
}

export type ScreeningStatus =
  | "valid"
  | "under_review"
  | "high_risk"
  | "pending"
  | "processing";

export interface RecentScreeningItem {
  case_id: string;
  case_number: number;
  case_name: string;
  document_type: string | null;
  person_name: string | null;
  risk_score: number | null;
  status: ScreeningStatus;
  created_at: string;
}

export interface RecentScreeningsResponse {
  items: RecentScreeningItem[];
}

export interface DocumentItem {
  id: string;
  file_name: string;
  mime_type: string;
  file_size: number;
  document_type: string | null;
  type_confidence: number | null;
  processing_status: string;
  has_preview: boolean;
}

export interface CaseDetail {
  id: string;
  case_number: number;
  case_name: string;
  status: string;
  overall_risk: number | null;
  recommendation: string | null;
  created_at: string;
  documents: DocumentItem[];
}

export interface HistoryItem {
  id: string;
  case_number: number;
  case_name: string;
  status: string;
  overall_risk: number | null;
  recommendation: string | null;
  person_name: string | null;
  document_count: number;
  created_at: string;
}

export interface ScreeningSummaryItem {
  module: string;
  outcome: string;
  detail: string;
}

export interface KeyFinding {
  level: "error" | "warning" | "info" | "success";
  text: string;
}

export interface ReportDocument {
  document_id: string;
  file_name: string;
  document_type: string | null;
  type_confidence: number | null;
  ocr_engine: string | null;
  ocr_mean_confidence: number | null;
  fields: { label: string; value: string; confidence: number | null }[];
  validation_overall: string | null;
}

export interface CaseReportResponse {
  case_id: string;
  case_number: number;
  case_name: string;
  generated_at: string;
  disclaimer: string;
  overall_risk: number | null;
  band: string | null;
  recommendation: string | null;
  screening_summary: ScreeningSummaryItem[];
  key_findings: KeyFinding[];
  factors: RiskFactorItem[];
  documents: ReportDocument[];
}

export interface RiskFactorItem {
  factor: string;
  score: number;
  direction: "increase" | "decrease";
  explanation: string;
}

export interface RiskReport {
  case_id: string;
  score: number | null;
  band: string | null;
  recommendation: string | null;
  factors: RiskFactorItem[];
}

export interface CaseCreated {
  id: string;
  case_number: number;
  case_name: string;
  status: string;
}

export interface UploadResult {
  case_id: string;
  uploaded: DocumentItem[];
  failed: { file_name: string; error: string }[];
}

export type StageStatus =
  | "pending"
  | "running"
  | "done"
  | "warning"
  | "unavailable"
  | "error";

export interface AnalysisStageItem {
  stage_key: string;
  stage_label: string;
  status: StageStatus;
  detail: string | null;
  duration_ms: number | null;
  order_index: number;
}

export interface AnalysisResponse {
  case_id: string;
  case_status: string;
  stages: AnalysisStageItem[];
}

export interface ExtractedFieldItem {
  field_name: string;
  raw_value: string;
  normalized_value: string | null;
  confidence: number | null;
  source_region: { x: number; y: number; w: number; h: number } | null;
}

export interface DocumentDetail extends Omit<DocumentItem, "type_confidence"> {
  case_id: string;
  type_confidence: number | null;
  ocr_engine: string | null;
  ocr_mean_confidence: number | null;
  file_hash_prefix: string | null;
  uploaded_at: string;
  fields: ExtractedFieldItem[];
}

export type CheckStatus = "pass" | "fail" | "warning" | "unavailable";

export interface ValidationItem {
  check_type: string;
  status: CheckStatus;
  message: string;
  evidence?: Record<string, unknown> | null;
}

export type OverallValidation = "valid" | "review_required" | "unable_to_verify";

export interface DocumentValidationReport {
  document_id: string;
  file_name: string;
  document_type: string | null;
  overall_status: OverallValidation;
  items: ValidationItem[];
}

export interface CaseValidationsResponse {
  case_id: string;
  documents: DocumentValidationReport[];
}

export interface ComparisonValue {
  document_id: string;
  file_name: string;
  raw_value: string;
  normalized_value: string | null;
  confidence: number | null;
  agrees: boolean;
}

export type ComparisonStatus = "consistent" | "mismatch" | "single_source";

export interface ComparisonFieldRow {
  field_name: string;
  label: string;
  status: ComparisonStatus;
  severity: "high" | "medium" | null;
  explanation: string | null;
  values: ComparisonValue[];
}

export interface CaseComparisonResponse {
  case_id: string;
  fields: ComparisonFieldRow[];
}

export interface ForensicItem {
  region: string;
  finding_type: string;
  severity: "low" | "medium" | "high";
  score: number;
  bbox: [number, number, number, number];
  explanation: string;
}

export interface DocumentForensicsReport {
  document_id: string;
  file_name: string;
  document_type: string | null;
  overall_suspicion: "low" | "medium" | "high";
  suspicion_score: number;
  findings: ForensicItem[];
}

export interface CaseForensicsResponse {
  case_id: string;
  disclaimer: string;
  documents: DocumentForensicsReport[];
}
