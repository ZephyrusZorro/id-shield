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

export interface FaceCropInfo {
  document_id: string;
  file_name: string;
  bbox: [number, number, number, number];
  normalized_bbox: [number, number, number, number];
  confidence: number;
  detection_method: string;
  sharpness: number;
  brightness: number;
  contrast: number;
  has_crop: boolean;
}

export interface FaceMetrics {
  ssim_score: number;
  phash_similarity: number;
  lbp_correlation: number;
  color_correlation: number;
}

export interface FaceComparisonPair {
  doc_a_id: string;
  doc_a_name: string;
  doc_b_id: string;
  doc_b_name: string;
  similarity_score: number;
  status: "match" | "borderline" | "mismatch";
  severity: "info" | "medium" | "high";
  explanation: string;
  metrics: FaceMetrics;
}

export interface CaseFacesResponse {
  case_id: string;
  disclaimer: string;
  faces: FaceCropInfo[];
  comparisons: FaceComparisonPair[];
  overall_status: "match" | "borderline" | "mismatch" | "single_face" | "no_faces";
}

// ---------------- Analytics & Intelligence ----------------

export interface AnalyticsKpis {
  total_cases: number;
  valid_count: number;
  review_count: number;
  high_risk_count: number;
  pass_rate: number;
  review_rate: number;
  high_risk_rate: number;
  average_risk_score: number;
  avg_processing_time_ms: number;
  total_documents_analyzed: number;
  face_verifications_count: number;
  face_mismatch_rate: number;
}

export interface VolumeTrendPoint {
  date: string;
  valid: number;
  under_review: number;
  high_risk: number;
  total: number;
}

export interface RiskDistributionBucket {
  tier: string;
  range_label: string;
  count: number;
  percentage: number;
  color: string;
}

export interface MismatchFieldStat {
  field_name: string;
  label: string;
  count: number;
  percentage: number;
  severity_breakdown: Record<string, number>;
}

export interface DocumentTypeStat {
  document_type: string;
  label: string;
  count: number;
  percentage: number;
  pass_rate: number;
  avg_confidence: number;
}

export interface ForensicSignalStat {
  signal_key: string;
  label: string;
  category: "tampering" | "biometric" | "validation" | "security_feature";
  detected_count: number;
  rate_percent: number;
  avg_severity_score: number;
}

export interface StageLatencyStat {
  stage_key: string;
  stage_label: string;
  avg_duration_ms: number;
  min_duration_ms: number;
  max_duration_ms: number;
}

export interface IntelligenceInsight {
  id: string;
  type: "risk_alert" | "trend" | "performance" | "quality";
  title: string;
  description: string;
  metric: string;
  importance: "high" | "medium" | "info";
}

export interface AnalyticsResponse {
  time_range: "7d" | "30d" | "90d" | "all";
  kpis: AnalyticsKpis;
  volume_trends: VolumeTrendPoint[];
  risk_distribution: RiskDistributionBucket[];
  mismatch_fields: MismatchFieldStat[];
  document_types: DocumentTypeStat[];
  forensic_signals: ForensicSignalStat[];
  stage_latencies: StageLatencyStat[];
  insights: IntelligenceInsight[];
  is_synthetic_baseline: boolean;
}
