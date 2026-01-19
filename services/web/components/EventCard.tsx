'use client';

import { clsx } from 'clsx';
import type { Event, Actor } from '@/lib/types';

interface EventCardProps {
  event: Event;
  onClick?: () => void;
  compact?: boolean;
}

const actorLabels: Record<Actor, string> = {
  telegram_in: 'Input',
  perception: 'Perception',
  memory: 'Memory',
  planner: 'Planner',
  critic: 'Critic',
  attention_gate: 'Attention',
  workspace: 'Workspace',
  metacog: 'Metacog',
  ast: 'AST',
  speaker: 'Speaker',
  monologue: 'Monologue',
  sleep: 'Sleep',
  telegram_out: 'Output',
  system: 'System',
};

const actorColors: Record<Actor, string> = {
  telegram_in: 'actor-perception',
  perception: 'actor-perception',
  memory: 'actor-memory',
  planner: 'actor-planner',
  critic: 'actor-critic',
  attention_gate: 'actor-attention',
  workspace: 'actor-workspace',
  metacog: 'actor-metacog',
  ast: 'actor-attention',
  speaker: 'actor-speaker',
  monologue: 'actor-workspace',
  sleep: 'actor-memory',
  telegram_out: 'actor-speaker',
  system: 'actor-critic',
};

export default function EventCard({ event, onClick, compact = false }: EventCardProps) {
  const streamClass = `stream-${event.stream}`;
  const actorClass = actorColors[event.actor] || 'actor-perception';

  const formatTime = (ts: string) => {
    const date = new Date(ts);
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  const getSummary = () => {
    if (event.content_text) {
      return event.content_text.slice(0, 150);
    }
    if (event.content_json) {
      const json = event.content_json;
      if ('message' in json && typeof json.message === 'string') {
        return json.message.slice(0, 150);
      }
      if ('workspace_summary' in json && typeof json.workspace_summary === 'string') {
        return json.workspace_summary.slice(0, 150);
      }
      if ('summary' in json && typeof json.summary === 'string') {
        return json.summary.slice(0, 150);
      }
      return JSON.stringify(json).slice(0, 150);
    }
    return '';
  };

  if (compact) {
    return (
      <div
        className={clsx(
          'p-2 rounded cursor-pointer hover:opacity-80 transition-opacity',
          streamClass
        )}
        onClick={onClick}
      >
        <div className="flex items-center gap-2 text-sm">
          <span className="text-gray-500 dark:text-gray-400 font-mono text-xs">
            {formatTime(event.ts)}
          </span>
          <span className={clsx('actor-badge', actorClass)}>
            {actorLabels[event.actor]}
          </span>
          <span className="truncate text-gray-700 dark:text-gray-300">
            {getSummary()}
          </span>
        </div>
      </div>
    );
  }

  return (
    <div
      className={clsx(
        'p-4 rounded-lg cursor-pointer hover:opacity-90 transition-opacity',
        streamClass
      )}
      onClick={onClick}
    >
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className={clsx('actor-badge', actorClass)}>
            {actorLabels[event.actor]}
          </span>
          <span className="text-xs text-gray-500 dark:text-gray-400 uppercase">
            {event.event_type.replace('_', ' ')}
          </span>
        </div>
        <span className="text-xs text-gray-500 dark:text-gray-400 font-mono">
          {formatTime(event.ts)}
        </span>
      </div>

      <p className="text-sm text-gray-700 dark:text-gray-300 line-clamp-3">
        {getSummary()}
      </p>

      {(event.tokens_in || event.tokens_out) && (
        <div className="mt-2 flex gap-4 text-xs text-gray-500 dark:text-gray-400">
          {event.tokens_in && <span>In: {event.tokens_in}</span>}
          {event.tokens_out && <span>Out: {event.tokens_out}</span>}
          {event.latency_ms && <span>{event.latency_ms}ms</span>}
        </div>
      )}
    </div>
  );
}
