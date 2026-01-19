'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { use } from 'react';
import { api } from '@/lib/api';
import type { Event } from '@/lib/types';

interface Props {
  params: Promise<{ eventId: string }>;
}

export default function EventDetailPage({ params }: Props) {
  const { eventId } = use(params);
  const [event, setEvent] = useState<Event | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadEvent = async () => {
      try {
        const data = await api.getEvent(eventId);
        setEvent(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load event');
      } finally {
        setLoading(false);
      }
    };
    loadEvent();
  }, [eventId]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-gray-500">Loading...</p>
      </div>
    );
  }

  if (error || !event) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center">
        <p className="text-red-500 mb-4">{error || 'Event not found'}</p>
        <Link href="/traces" className="text-purple-600 hover:underline">
          Back to traces
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="mb-6">
        <Link
          href={`/traces/${event.trace_id}`}
          className="text-sm text-gray-500 hover:text-gray-700"
        >
          &larr; Back to Trace
        </Link>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
          Event Detail
        </h1>
        <p className="text-sm text-gray-500 font-mono">{event.event_id}</p>
      </div>

      {/* Event info */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 space-y-6">
        {/* Metadata */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <p className="text-xs text-gray-500">Actor</p>
            <p className="font-medium">{event.actor}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Event Type</p>
            <p className="font-medium">{event.event_type}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Stream</p>
            <p className="font-medium">{event.stream}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Timestamp</p>
            <p className="font-medium text-sm">
              {new Date(event.ts).toLocaleString()}
            </p>
          </div>
        </div>

        {/* Model info */}
        {event.model_provider && (
          <div className="pt-4 border-t dark:border-gray-700">
            <h3 className="text-sm font-medium text-gray-500 mb-2">Model</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <p className="text-xs text-gray-500">Provider</p>
                <p className="font-medium">{event.model_provider}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Model</p>
                <p className="font-medium">{event.model_id}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Tokens In</p>
                <p className="font-medium">{event.tokens_in || '-'}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Tokens Out</p>
                <p className="font-medium">{event.tokens_out || '-'}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Latency</p>
                <p className="font-medium">{event.latency_ms ? `${event.latency_ms}ms` : '-'}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Cost</p>
                <p className="font-medium">
                  {event.cost_usd ? `$${event.cost_usd.toFixed(4)}` : '-'}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Content text */}
        {event.content_text && (
          <div className="pt-4 border-t dark:border-gray-700">
            <h3 className="text-sm font-medium text-gray-500 mb-2">Content</h3>
            <p className="whitespace-pre-wrap bg-gray-50 dark:bg-gray-700 p-4 rounded">
              {event.content_text}
            </p>
          </div>
        )}

        {/* Content JSON */}
        {event.content_json && (
          <div className="pt-4 border-t dark:border-gray-700">
            <h3 className="text-sm font-medium text-gray-500 mb-2">JSON Content</h3>
            <pre className="text-sm overflow-auto bg-gray-50 dark:bg-gray-700 p-4 rounded max-h-[500px]">
              {JSON.stringify(event.content_json, null, 2)}
            </pre>
          </div>
        )}

        {/* Tags */}
        {event.tags && event.tags.length > 0 && (
          <div className="pt-4 border-t dark:border-gray-700">
            <h3 className="text-sm font-medium text-gray-500 mb-2">Tags</h3>
            <div className="flex flex-wrap gap-2">
              {event.tags.map((tag) => (
                <span
                  key={tag}
                  className="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded text-sm"
                >
                  {tag}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Parent event */}
        {event.parent_event_id && (
          <div className="pt-4 border-t dark:border-gray-700">
            <h3 className="text-sm font-medium text-gray-500 mb-2">Parent Event</h3>
            <Link
              href={`/events/${event.parent_event_id}`}
              className="text-purple-600 hover:underline font-mono text-sm"
            >
              {event.parent_event_id}
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
