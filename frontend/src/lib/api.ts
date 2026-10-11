import type {
  Investigation,
  LogsResponse,
  ScenarioInfo,
  StatusResponse,
} from '../types'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!response.ok) {
    let detail = `Request failed (HTTP ${response.status})`
    try {
      const body = await response.json()
      if (body?.detail) detail = body.detail
    } catch {
      /* keep default detail */
    }
    throw new Error(detail)
  }
  return response.json() as Promise<T>
}

export const api = {
  getStatus: () => request<StatusResponse>('/status'),
  getLogs: (limit = 150) => request<LogsResponse>(`/logs?limit=${limit}`),
  getScenarios: () => request<{ scenarios: ScenarioInfo[] }>('/scenarios'),
  activateScenario: (scenarioId: string) =>
    request<{ scenario: ScenarioInfo }>(`/scenarios/${scenarioId}/activate`, { method: 'POST' }),
  startInvestigation: () =>
    request<Investigation>('/investigations', { method: 'POST', body: JSON.stringify({}) }),
  getInvestigation: (id: string) => request<Investigation>(`/investigations/${id}`),
}
