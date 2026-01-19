'use client';

import { useEffect, useState } from 'react';
import { clsx } from 'clsx';
import type { Event, Stream } from '@/lib/types';
import { wsClient } from '@/lib/websocket';
import EventCard from './EventCard';

interface StreamPanelProps {
  stream: Stream;
  title: string;
  maxEvents?: number;
  onEventClick?: (event: Event) => void;
}

export default function StreamPanel({
  stream,
  title,
  maxEvents = 50,
  onEventClick,
}: StreamPanelProps) {
  const [events, setEvents] = useState<Event[]>([]);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    // Connect to WebSocket
    wsClient.connect(stream);

    // Subscribe to events
    const unsubEvent = wsClient.onEvent((event) => {
      if (event.stream === stream || stream === 'all' as unknown as Stream) {
        setEvents((prev) => {
          const updated = [event, ...prev];
          return updated.slice(0, maxEvents);
        });
      }
    });

    // Subscribe to status
    const unsubStatus = wsClient.onStatus(setConnected);

    return () => {
      unsubEvent();
      unsubStatus();
    };
  }, [stream, maxEvents]);

  const streamColors: Record<Stream, string> = {
    external: 'border-blue-500',
    conscious: 'border-purple-500',
    subconscious: 'border-gray-400',
    sleep: 'border-indigo-500',
  };

  return (
    <div
      className={clsx(
        'flex flex-col h-full border-t-4 rounded-lg bg-white dark:bg-gray-800 shadow',
        streamColors[stream]
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b dark:border-gray-700">
        <h3 className="font-semibold text-gray-900 dark:text-gray-100">{title}</h3>
        <div className="flex items-center gap-2">
          <div
            className={clsx(
              'w-2 h-2 rounded-full',
              connected ? 'bg-green-500' : 'bg-red-500'
            )}
          />
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {events.length}
          </span>
        </div>
      </div>

      {/* Events */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {events.length === 0 ? (
          <div className="text-center text-gray-500 dark:text-gray-400 py-8">
            <p className="text-sm">No events yet</p>
            <p className="text-xs mt-1">
              {connected ? 'Waiting for events...' : 'Connecting...'}
            </p>
          </div>
        ) : (
          events.map((event) => (
            <EventCard
              key={event.event_id}
              event={event}
              onClick={() => onEventClick?.(event)}
              compact
            />
          ))
        )}
      </div>
    </div>
  );
}
