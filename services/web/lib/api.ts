/**
 * API client for SIMA backend.
 */

import type {
  Trace,
  TraceDetail,
  TraceListResponse,
  Event,
  TheoryIndicators,
  SystemStatus,
  Memory,
  MemoryListResponse,
  CoreMemoriesResponse,
} from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

class ApiClient {
  private token: string | null = null;
  private adminToken: string | null = null;

  setToken(token: string) {
    this.token = token;
    if (typeof window !== 'undefined') {
      localStorage.setItem('sima_token', token);
    }
  }

  getToken(): string | null {
    if (this.token) return this.token;
    if (typeof window !== 'undefined') {
      this.token = localStorage.getItem('sima_token');
    }
    return this.token;
  }

  clearToken() {
    this.token = null;
    if (typeof window !== 'undefined') {
      localStorage.removeItem('sima_token');
    }
  }

  setAdminToken(token: string) {
    this.adminToken = token;
    if (typeof window !== 'undefined') {
      localStorage.setItem('sima_admin_token', token);
    }
  }

  getAdminToken(): string | null {
    if (this.adminToken) return this.adminToken;
    if (typeof window !== 'undefined') {
      this.adminToken = localStorage.getItem('sima_admin_token');
    }
    return this.adminToken;
  }

  clearAdminToken() {
    this.adminToken = null;
    if (typeof window !== 'undefined') {
      localStorage.removeItem('sima_admin_token');
    }
  }

  private async fetch<T>(
    path: string,
    options: RequestInit = {}
  ): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...((options.headers as Record<string, string>) || {}),
    };

    const token = this.getToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      if (response.status === 401) {
        this.clearToken();
      }
      const error = await response.json().catch(() => ({ detail: 'Request failed' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  // Auth
  async checkAuthRequired(): Promise<{ auth_required: boolean }> {
    return this.fetch('/auth/check');
  }

  async login(password: string): Promise<{ access_token: string; expires_at: string }> {
    const response = await this.fetch<{ access_token: string; expires_at: string }>(
      '/auth/login',
      {
        method: 'POST',
        body: JSON.stringify({ password }),
      }
    );
    this.setToken(response.access_token);
    return response;
  }

  // Traces
  async listTraces(params?: {
    limit?: number;
    offset?: number;
    input_type?: string;
  }): Promise<TraceListResponse> {
    const query = new URLSearchParams();
    if (params?.limit) query.set('limit', params.limit.toString());
    if (params?.offset) query.set('offset', params.offset.toString());
    if (params?.input_type) query.set('input_type', params.input_type);

    const queryString = query.toString();
    return this.fetch(`/traces${queryString ? `?${queryString}` : ''}`);
  }

  async getTrace(traceId: string): Promise<TraceDetail> {
    return this.fetch(`/traces/${traceId}`);
  }

  async getTracePublic(traceId: string): Promise<Trace> {
    return this.fetch(`/traces/${traceId}/public`);
  }

  // Events
  async getEvent(eventId: string): Promise<Event> {
    return this.fetch(`/events/${eventId}`);
  }

  async listEvents(params?: {
    limit?: number;
    offset?: number;
    stream?: string;
  }): Promise<{ events: Event[]; total: number }> {
    const query = new URLSearchParams();
    if (params?.limit) query.set('limit', params.limit.toString());
    if (params?.offset) query.set('offset', params.offset.toString());
    if (params?.stream) query.set('stream', params.stream);

    const queryString = query.toString();
    return this.fetch(`/events${queryString ? `?${queryString}` : ''}`);
  }

  async searchEvents(q: string, limit = 20): Promise<{ results: Event[]; query: string }> {
    return this.fetch(`/events/search?q=${encodeURIComponent(q)}&limit=${limit}`);
  }

  // Metrics
  async getIndicators(windowHours = 24): Promise<TheoryIndicators> {
    return this.fetch(`/metrics/indicators?window_hours=${windowHours}`);
  }

  async getOverview(): Promise<TheoryIndicators['overview']> {
    return this.fetch('/metrics/overview');
  }

  // Admin
  async getSystemStatus(): Promise<SystemStatus> {
    return this.fetch('/admin/status');
  }

  async setSystemPaused(paused: boolean): Promise<SystemStatus> {
    return this.fetch('/admin/pause', {
      method: 'POST',
      body: JSON.stringify({ paused }),
    });
  }

  async triggerTick(tickType: string): Promise<{ status: string; tick_type: string }> {
    return this.fetch(`/admin/trigger-tick?tick_type=${tickType}`, {
      method: 'POST',
    });
  }

  async adminLogin(username: string, password: string): Promise<{ access_token: string; expires_at: string }> {
    const response = await this.fetch<{ access_token: string; expires_at: string }>(
      '/admin/login',
      {
        method: 'POST',
        body: JSON.stringify({ username, password }),
      }
    );
    this.setAdminToken(response.access_token);
    return response;
  }

  async resetSystem(): Promise<{
    status: string;
    events_deleted: number;
    traces_deleted: number;
    memories_deleted: number;
  }> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    const adminToken = this.getAdminToken();
    if (adminToken) {
      headers['Authorization'] = `Bearer ${adminToken}`;
    }

    const response = await fetch(`${API_BASE}/admin/reset`, {
      method: 'POST',
      headers,
    });

    if (!response.ok) {
      if (response.status === 401 || response.status === 403) {
        this.clearAdminToken();
      }
      const error = await response.json().catch(() => ({ detail: 'Request failed' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  // Memories
  async listMemories(params?: {
    limit?: number;
    offset?: number;
    memory_type?: string;
  }): Promise<MemoryListResponse> {
    const query = new URLSearchParams();
    if (params?.limit) query.set('limit', params.limit.toString());
    if (params?.offset) query.set('offset', params.offset.toString());
    if (params?.memory_type) query.set('memory_type', params.memory_type);

    const queryString = query.toString();
    return this.fetch(`/memories${queryString ? `?${queryString}` : ''}`);
  }

  async getCoreMemories(params?: {
    core_limit?: number;
    recent_limit?: number;
  }): Promise<CoreMemoriesResponse> {
    const query = new URLSearchParams();
    if (params?.core_limit) query.set('core_limit', params.core_limit.toString());
    if (params?.recent_limit) query.set('recent_limit', params.recent_limit.toString());

    const queryString = query.toString();
    return this.fetch(`/memories/core${queryString ? `?${queryString}` : ''}`);
  }

  async getMemory(memoryId: string): Promise<Memory> {
    return this.fetch(`/memories/${memoryId}`);
  }

  async searchMemories(q: string, limit = 20): Promise<{ results: Memory[]; query: string }> {
    return this.fetch(`/memories/search?q=${encodeURIComponent(q)}&limit=${limit}`);
  }
}

export const api = new ApiClient();
