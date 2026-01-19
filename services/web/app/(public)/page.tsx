'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';
import type { Trace, OverviewMetrics } from '@/lib/types';

export default function PublicHomePage() {
  const [traces, setTraces] = useState<Trace[]>([]);
  const [overview, setOverview] = useState<OverviewMetrics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      try {
        const [tracesData, overviewData] = await Promise.all([
          api.listTraces({ limit: 10 }),
          api.getOverview().catch(() => null),
        ]);
        setTraces(tracesData.traces);
        setOverview(overviewData);
      } catch (error) {
        console.error('Failed to load data:', error);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, []);

  const formatDate = (ts: string) => {
    return new Date(ts).toLocaleString();
  };

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 shadow">
        <div className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                SIMA
              </h1>
              <p className="text-gray-600 dark:text-gray-400">
                Consciousness Research Agent
              </p>
            </div>
            <Link
              href="/lab"
              className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition"
            >
              Lab Access
            </Link>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        {/* Overview stats */}
        {overview && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
              <p className="text-sm text-gray-500 dark:text-gray-400">Total Traces</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {overview.total_traces}
              </p>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
              <p className="text-sm text-gray-500 dark:text-gray-400">Total Events</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {overview.total_events}
              </p>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
              <p className="text-sm text-gray-500 dark:text-gray-400">Tokens Used</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {overview.total_tokens.toLocaleString()}
              </p>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
              <p className="text-sm text-gray-500 dark:text-gray-400">Total Cost</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                ${overview.total_cost_usd.toFixed(2)}
              </p>
            </div>
          </div>
        )}

        {/* Recent traces */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
          <div className="p-4 border-b dark:border-gray-700">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Recent Traces
            </h2>
          </div>
          <div className="divide-y dark:divide-gray-700">
            {loading ? (
              <div className="p-8 text-center text-gray-500">Loading...</div>
            ) : traces.length === 0 ? (
              <div className="p-8 text-center text-gray-500">No traces yet</div>
            ) : (
              traces.map((trace) => (
                <Link
                  key={trace.trace_id}
                  href={`/traces/${trace.trace_id}`}
                  className="block p-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                        {trace.user_message || `${trace.input_type} trace`}
                      </p>
                      {trace.response_message && (
                        <p className="text-sm text-gray-500 dark:text-gray-400 truncate mt-1">
                          {trace.response_message}
                        </p>
                      )}
                    </div>
                    <div className="ml-4 flex-shrink-0 text-right">
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        {formatDate(trace.started_at)}
                      </p>
                      <p className="text-xs text-gray-400 dark:text-gray-500">
                        {trace.total_tokens} tokens
                      </p>
                    </div>
                  </div>
                </Link>
              ))
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
