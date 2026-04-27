export interface Breakdown {
  state_info?: { summary: string; label: string; severity: number; color: string }
  risk_score?: {
    value: number
    verdict: string
    formula: string
    rating: 'safe' | 'watch' | 'warning' | 'critical'
  }
  compression_gradient?: { rating: string; verdict: string }
  velocity_variance?: { rating: string; verdict: string }
  anomaly_score?: { rating: string; verdict: string }
  confidence?: { penalties: string[]; bonuses: string[]; verdict: string }
  environment?: { verdict: string }
}

export interface InterventionAction {
  priority: string
  action: string
  owner: string
  outcome: string
}

export interface Interventions {
  level: string
  pastel_bg: string
  text_color: string
  border_color: string
  actions: InterventionAction[]
}

export interface AnalysisResult {
  status: 'done' | 'pending'
  task_id: string
  location: string
  timestamp: string
  state: string
  confidence: number
  risk_score: number
  congestion: number
  gradient: number
  velocity_var: number
  anomaly_score: number
  is_simulated: boolean
  breakdown: Breakdown
  interventions: Interventions
}

export interface HistoryRecord {
  id: number
  created_at: string
  location_name: string
  latitude: number
  longitude: number
  congestion: number
  speed: number | null
  gradient: number | null
  velocity_var: number | null
  anomaly_score: number | null
  risk_score: number | null
  state: string
  session_id: string | null
}

export interface AnalyzeParams {
  lat: number
  lon: number
  location_name: string
  env_weather_risk: number
  env_width_factor: number
  env_event_active: boolean
}
