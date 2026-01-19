'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { use } from 'react';
import { api } from '@/lib/api';
import type { Trace } from '@/lib/types';

interface Props {
  params: Promise<{ traceId: string }>;
}

export default function PublicTraceDetailPage({ params }: Props) {
  const { traceId } = use(params);
  const [trace, setTrace] = useState<Trace | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadTrace = async () => {
      try {
        const data = await api.getTracePublic(traceId);
        setTrace(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load trace');
      } finally {
        setLoading(false);
      }
    };
    loadTrace();
  }, [traceId]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-gray-500">Loading...</p>
      </div>
    );
  }

  if (error || !trace) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center">
        <p className="text-red-500 mb-4">{error || 'Trace not found'}</p>
        <Link href="/" className="text-purple-600 hover:underline">
          Back to home
        </Link>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 shadow">
        <div className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
          <div className="flex items-center gap-4">
            <Link href="/" className="text-gray-500 hover:text-gray-700">
              &larr; Back
            </Link>
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                Trace Detail
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400 font-mono">
                {trace.trace_id.slice(0, 8)}...
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <div className="space-y-6">
            {/* Input */}
            {trace.user_message && (
              <div>
                <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">
                  User Message
                </h3>
                <p className="text-gray-900 dark:text-white bg-gray-50 dark:bg-gray-700 p-4 rounded">
                  {trace.user_message}
                </p>
              </div>
            )}

            {/* Response */}
            {trace.response_message && (
              <div>
                <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">
                  Response
                </h3>
                <p className="text-gray-900 dark:text-white bg-purple-50 dark:bg-purple-900/20 p-4 rounded">
                  {trace.response_message}
                </p>
              </div>
            )}

            {/* Metadata */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-4 border-t dark:border-gray-700">
              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400">Type</p>
                <p className="text-sm font-medium text-gray-900 dark:text-white">
                  {trace.input_type}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400">Started</p>
                <p className="text-sm font-medium text-gray-900 dark:text-white">
                  {new Date(trace.started_at).toLocaleString()}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400">Tokens</p>
                <p className="text-sm font-medium text-gray-900 dark:text-white">
                  {trace.total_tokens}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400">Cost</p>
                <p className="text-sm font-medium text-gray-900 dark:text-white">
                  ${trace.total_cost_usd.toFixed(4)}
                </p>
              </div>
            </div>

            {/* Lab access prompt */}
            <div className="pt-4 border-t dark:border-gray-700 text-center">
              <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">
                View full trace with all events and module outputs
              </p>
              <Link
                href={`/lab/traces/${trace.trace_id}`}
                className="inline-block px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700 transition"
              >
                View in Lab
              </Link>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
