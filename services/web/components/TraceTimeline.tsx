'use client';

import { clsx } from 'clsx';
import type { Event } from '@/lib/types';
import EventCard from './EventCard';

interface TraceTimelineProps {
  events: Event[];
  onEventClick?: (event: Event) => void;
}

export default function TraceTimeline({ events, onEventClick }: TraceTimelineProps) {
  // Group events by actor for a visual timeline
  const actors = ['perception', 'memory', 'planner', 'critic', 'attention_gate', 'workspace', 'metacog', 'ast', 'speaker'];

  return (
    <div className="space-y-2">
      {events.map((event) => (
        <div
          key={event.event_id}
          className="relative"
        >
          {/* Timeline line */}
          <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-gray-200 dark:bg-gray-700" />

          {/* Event */}
          <div className="ml-8">
            <EventCard
              event={event}
              onClick={() => onEventClick?.(event)}
              compact
            />
          </div>

          {/* Timeline dot */}
          <div
            className={clsx(
              'absolute left-2 top-3 w-4 h-4 rounded-full border-2 border-white dark:border-gray-900',
              event.stream === 'external' && 'bg-blue-500',
              event.stream === 'conscious' && 'bg-purple-500',
              event.stream === 'subconscious' && 'bg-gray-400',
              event.stream === 'sleep' && 'bg-indigo-500'
            )}
          />
        </div>
      ))}
    </div>
  );
}
