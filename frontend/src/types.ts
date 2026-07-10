export interface Zone {
  name: string;
  label?: string;
  capacity: number;
  density: number;
  current_occupancy?: number;
  trend?: number;
}

export interface OpsAction {
  id: number;
  title: string;
  description: string;
  reasoning: string;
  priority: 'critical' | 'high' | 'medium' | 'low';
  status: 'pending' | 'approved' | 'rejected' | 'completed';
  recommended_by: string;
  affected_zones: string[];
  affected_population: number;
  time_to_impact_min: number | null;
  approved_by?: number | null;
  approved_at?: string | null;
  created_at: string;
}

export interface PathNode {
  name: string;
  type: string;
  distance_m?: number;
  step_free?: boolean;
  estimated_time_s?: number;
}

export interface NavigationResult {
  path: PathNode[];
  total_distance_m: number;
  total_time_s: number;
  step_free: boolean;
  explanation: string;
  avoid_reason?: string | null;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface ChatResult {
  response: string;
  sources: Array<{ type: string; [key: string]: unknown }>;
  detected_intent: string;
  language: string;
}

export interface SustainabilityData {
  transit_split: Record<string, number>;
  estimated_co2_kg_per_1000_fans?: number;
  estimated_co2_kg?: number;
  sustainability_score: number;
  eco_tips: string[];
  waste_bin_fill_pct?: Record<string, number>;
  water_refill_usage?: number;
}

export interface CrowdAlert {
  id: string;
  zone: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  message: string;
  density: number;
  predicted_crossing_time_min: number | null;
  suggested_mitigation: string;
  affected_population: number;
  detected_at: string;
}

export interface TransitRecommendation {
  best_mode: string;
  best_wait_min: number;
  co2_saved_kg: number;
  nudge: string;
  alternatives: Array<{
    mode: string;
    wait_min: number;
    co2_kg_per_5km: number;
  }>;
}

export type UserRole = 'fan' | 'volunteer' | 'organizer';

export interface User {
  id: number;
  username: string;
  email: string;
  role: UserRole;
}
