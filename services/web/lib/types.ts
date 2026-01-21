/**
 * TypeScript types for SIMA web frontend.
 */

export type Stream = 'external' | 'conscious' | 'subconscious' | 'sleep' | 'memories';

export type Actor =
  | 'telegram_in'
  | 'perception'
  | 'memory'
  | 'planner'
  | 'critic'
  | 'attention_gate'
  | 'workspace'
  | 'metacog'
  | 'ast'
  | 'speaker'
  | 'monologue'
  | 'sleep'
  | 'telegram_out'
  | 'system';

export type EventType =
  | 'message_in'
  | 'tick'
  | 'percept'
  | 'candidate'
  | 'selection'
  | 'workspace_update'
  | 'broadcast'
  | 'metacog_report'
  | 'belief_revision'
  | 'attention_prediction'
  | 'attention_comparison'
  | 'monologue'
  | 'message_out'
  | 'sleep_start'
  | 'sleep_digest'
  | 'memory_consolidation'
  | 'sleep_end'
  | 'error'
  | 'pause'
  | 'resume';

export type InputType = 'user_message' | 'minute_tick' | 'autonomous_tick';

export interface Trace {
  trace_id: string;
  input_type: InputType;
  started_at: string;
  completed_at: string | null;
  telegram_chat_id?: number;
  telegram_message_id?: number;
  user_message: string | null;
  response_message: string | null;
  total_tokens: number;
  total_cost_usd: number;
}

export interface TraceDetail extends Trace {
  events: Event[];
}

export interface Event {
  event_id: string;
  trace_id: string;
  ts: string;
  actor: Actor;
  stream: Stream;
  event_type: EventType;
  content_text: string | null;
  content_json: Record<string, unknown> | null;
  model_provider: string | null;
  model_id: string | null;
  tokens_in: number | null;
  tokens_out: number | null;
  latency_ms: number | null;
  cost_usd: number | null;
  parent_event_id: string | null;
  tags: string[];
}

export interface TraceListResponse {
  traces: Trace[];
  total: number;
  limit: number;
  offset: number;
}

export interface OverviewMetrics {
  total_traces: number;
  total_events: number;
  total_tokens: number;
  total_cost_usd: number;
}

export interface RPTMetrics {
  avg_recurrence_steps: number;
  avg_stability_score: number;
  revision_frequency: number;
}

export interface GWTMetrics {
  parallel_module_count: number;
  avg_candidates_per_trace: number;
  avg_selected_items: number;
  broadcast_rate: number;
}

export interface HOTMetrics {
  avg_confidence: number;
  belief_revision_rate: number;
  metacog_reports_per_trace: number;
}

export interface ASTMetrics {
  prediction_accuracy: number;
  focus_shift_rate: number;
}

export interface TheoryIndicators {
  overview: OverviewMetrics;
  rpt: RPTMetrics;
  gwt: GWTMetrics;
  hot: HOTMetrics;
  ast: ASTMetrics;
}

export interface SystemStatus {
  paused: boolean;
  status: 'running' | 'paused';
}

export interface WebSocketMessage {
  type: 'connected' | 'event' | 'memory' | 'heartbeat' | 'pong';
  stream?: Stream;
  data?: Event | Memory;
}

// Memory types
export type MemoryType = 'L1' | 'L2' | 'L3';

export interface Memory {
  memory_id: string;
  memory_type: MemoryType;
  content: string;
  created_at: string;
  updated_at: string;
  relevance_score: number;
  access_count: number;
  metadata_json: Record<string, unknown> | null;
}

export interface MemoryListResponse {
  memories: Memory[];
  total: number;
  limit: number;
  offset: number;
}

export interface CoreMemoriesResponse {
  core_memories: Memory[];
  recent_memories: Memory[];
}
