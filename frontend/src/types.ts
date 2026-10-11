export interface TimelinePoint {
  label: string
  requests: number
  avg_ms: number
  errors: number
}

export interface EndpointStat {
  endpoint: string
  count: number
  avg_ms: number
  error_rate: number
}

export interface Metrics {
  service: string
  scenario: string
  window_minutes: number
  total_requests: number
  error_count: number
  error_rate: number
  avg_response_ms: number
  p95_response_ms: number
  status_breakdown: Record<string, number>
  endpoints: EndpointStat[]
  timeline: TimelinePoint[]
}

export interface ServiceHealth {
  status: string
  service: string
  uptime_s: number
  dependencies: Record<string, string>
}

export interface ScenarioInfo {
  id: string
  name: string
  description: string
}

export interface StatusResponse {
  health: ServiceHealth
  health_response_time_ms: number
  scenario: ScenarioInfo
  metrics: Metrics
}

export type LogLevel = 'INFO' | 'WARNING' | 'ERROR'

export interface LogEntry {
  timestamp: string
  level: LogLevel
  service: string
  endpoint: string
  method: string
  status_code: number
  duration_ms: number
  request_id: string
  message: string
}

export interface LogsResponse {
  logs: LogEntry[]
  total: number
}

export type InvestigationStatus = 'pending' | 'running' | 'completed' | 'failed'

export interface InvestigationStep {
  step: number
  tool: string
  arguments: Record<string, unknown>
  summary: string
  result: unknown
  timestamp: string
}

export type Severity = 'healthy' | 'low' | 'medium' | 'high' | 'critical'

export interface IncidentReport {
  title: string
  severity: Severity
  affected_service: string
  summary: string
  evidence: string[]
  root_cause: string
  confidence: number
  recommended_actions: string[]
}

export interface Investigation {
  id: string
  status: InvestigationStatus
  description: string
  scenario: ScenarioInfo
  steps: InvestigationStep[]
  report?: IncidentReport | null
  error?: string | null
  created_at: string
  finished_at?: string | null
}
