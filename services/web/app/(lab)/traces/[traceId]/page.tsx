'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { use } from 'react';
import { api } from '@/lib/api';
import type { TraceDetail, Event } from '@/lib/types';
import EventCard from '@/components/EventCard';
import TraceTimeline from '@/components/TraceTimeline';

interface Props {
  params: Promise<{ traceId: string }>;
}

export default function LabTraceDetailPage({ params }: Props) {
  const { traceId } = use(params);
  const [trace, setTrace] = useState<TraceDetail | null>(null);
  const [selectedEvent, setSelectedEvent] = useState<Event | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'timeline' | 'stream'>('timeline');

  useEffect(() => {
    const loadTrace = async () => {
      try {
        const data = await api.getTrace(traceId);
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
        <Link href="/traces" className="text-purple-600 hover:underline">
          Back to traces
        </Link>
      </div>
    );
  }

  const eventsByStream = trace.events.reduce(
    (acc, event) => {
      if (!acc[event.stream]) acc[event.stream] = [];
      acc[event.stream].push(event);
      return acc;
    },
    {} as Record<string, Event[]>
  );

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <Link href="/traces" className="text-sm text-gray-500 hover:text-gray-700">
            &larr; All Traces
          </Link>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
            Trace Detail
          </h1>
          <p className="text-sm text-gray-500 font-mono">{trace.trace_id}</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setViewMode('timeline')}
            className={`px-3 py-1 rounded text-sm ${
              viewMode === 'timeline'
                ? 'bg-purple-600 text-white'
                : 'bg-gray-200 dark:bg-gray-700'
            }`}
          >
            Timeline
          </button>
          <button
            onClick={() => setViewMode('stream')}
            className={`px-3 py-1 rounded text-sm ${
              viewMode === 'stream'
                ? 'bg-purple-600 text-white'
                : 'bg-gray-200 dark:bg-gray-700'
            }`}
          >
            By Stream
          </button>
        </div>
      </div>

      {/* Summary */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 mb-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <p className="text-xs text-gray-500">Type</p>
            <p className="font-medium">{trace.input_type}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Events</p>
            <p className="font-medium">{trace.events.length}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Tokens</p>
            <p className="font-medium">{trace.total_tokens}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Cost</p>
            <p className="font-medium">${trace.total_cost_usd.toFixed(4)}</p>
          </div>
        </div>

        {trace.user_message && (
          <div className="mt-4 pt-4 border-t dark:border-gray-700">
            <p className="text-xs text-gray-500 mb-1">User Message</p>
            <p className="text-gray-900 dark:text-white">{trace.user_message}</p>
          </div>
        )}

        {trace.response_message && (
          <div className="mt-4 pt-4 border-t dark:border-gray-700">
            <p className="text-xs text-gray-500 mb-1">Response</p>
            <p className="text-gray-900 dark:text-white">{trace.response_message}</p>
          </div>
        )}
      </div>

      {/* Events */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Events list */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
          <h2 className="text-lg font-semibold mb-4">Events</h2>
          {viewMode === 'timeline' ? (
            <TraceTimeline
              events={trace.events}
              onEventClick={setSelectedEvent}
            />
          ) : (
            <div className="space-y-4">
              {Object.entries(eventsByStream).map(([stream, events]) => (
                <div key={stream}>
                  <h3 className="text-sm font-medium text-gray-500 mb-2 uppercase">
                    {stream}
                  </h3>
                  <div className="space-y-2">
                    {events.map((event) => (
                      <EventCard
                        key={event.event_id}
                        event={event}
                        onClick={() => setSelectedEvent(event)}
                        compact
                      />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Event detail */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
          <h2 className="text-lg font-semibold mb-4">Event Detail</h2>
          {selectedEvent ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-gray-500">Actor</p>
                  <p className="font-medium">{selectedEvent.actor}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Type</p>
                  <p className="font-medium">{selectedEvent.event_type}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Stream</p>
                  <p className="font-medium">{selectedEvent.stream}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Time</p>
                  <p className="font-medium text-sm">
                    {new Date(selectedEvent.ts).toLocaleTimeString()}
                  </p>
                </div>
              </div>

              {selectedEvent.content_text && (
                <div>
                  <p className="text-xs text-gray-500 mb-1">Content</p>
                  <p className="text-sm whitespace-pre-wrap bg-gray-50 dark:bg-gray-700 p-3 rounded">
                    {selectedEvent.content_text}
                  </p>
                </div>
              )}

              {selectedEvent.content_json && (
                <div>
                  <p className="text-xs text-gray-500 mb-1">JSON</p>
                  <pre className="text-xs overflow-auto bg-gray-50 dark:bg-gray-700 p-3 rounded max-h-96">
                    {JSON.stringify(selectedEvent.content_json, null, 2)}
                  </pre>
                </div>
              )}

              {(selectedEvent.tokens_in || selectedEvent.tokens_out) && (
                <div className="flex gap-4 text-sm text-gray-500">
                  {selectedEvent.tokens_in && (
                    <span>In: {selectedEvent.tokens_in}</span>
                  )}
                  {selectedEvent.tokens_out && (
                    <span>Out: {selectedEvent.tokens_out}</span>
                  )}
                  {selectedEvent.latency_ms && (
                    <span>{selectedEvent.latency_ms}ms</span>
                  )}
                  {selectedEvent.cost_usd && (
                    <span>${selectedEvent.cost_usd.toFixed(4)}</span>
                  )}
                </div>
              )}
            </div>
          ) : (
            <p className="text-gray-500 text-center py-8">
              Select an event to view details
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
