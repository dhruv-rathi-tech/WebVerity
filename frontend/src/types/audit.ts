export type SeverityLevel = 'critical' | 'high' | 'medium' | 'low' | 'info';

export interface SuggestedAction {
  summary: string;
  priority: string;
  implementation_details?: string;
}

export interface Finding {
  id: string;
  title: string;
  category: string;
  severity: SeverityLevel;
  confidence: string;
  observation: string;
  evidence: string;
  root_cause: string;
  impact: string;
  detection_method: string;
  affected_urls: string[];
  suggested_action: SuggestedAction;
}

export interface ProactiveRecommendation {
  id: string;
  title: string;
  opportunity: string;
  suggested_action: SuggestedAction;
}

export interface AuditSummary {
  total_findings: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
  info: number;
}

export interface HeadingItem {
  tag: string;
  level: number;
  text: string;
  dom_index: number;
}

export interface PageDto {
  url: string;
  normalized_url: string;
  status_code: number;
  response_time_ms: number;
  page_archetype: string;
  is_primary_page: boolean;
  title: string;
  meta_description: string;
  canonical_url?: string;
  headings_count: number;
  headings: HeadingItem[];
  schema_types: string[];
  internal_links_count: number;
  external_links_count: number;
  extracted_facts: Record<string, any>;
  error_message?: string;
}

export interface AuditReport {
  id: string;
  site: string;
  audited_at: string;
  site_archetype: string;
  pages_audited: number;
  pages_discovered: number;
  crawl_duration_seconds: number;
  summary: AuditSummary;
  findings: Finding[];
  proactive_recommendations: ProactiveRecommendation[];
  pages: PageDto[];
  markdown_report?: string;
}

export interface AuditRequestOptions {
  url: string;
  max_pages?: number;
  max_depth?: number;
  timeout?: number;
  external_records?: any[];
}
