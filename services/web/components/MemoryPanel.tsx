'use client';

import { useEffect, useState } from 'react';
import { clsx } from 'clsx';
import type { Memory, MemoryType } from '@/lib/types';
import { api } from '@/lib/api';

interface MemoryPanelProps {
  onMemoryClick?: (memory: Memory) => void;
  maxCoreMemories?: number;
  maxRecentMemories?: number;
}

const memoryTypeLabels: Record<MemoryType, string> = {
  L3: 'Core',
  L2: 'Consolidated',
  L1: 'Recent',
};

function MemoryCard({
  memory,
  onClick,
}: {
  memory: Memory;
  onClick?: () => void;
}) {
  const formatDate = (ts: string) => {
    const date = new Date(ts);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    });
  };

  return (
    <div
      className={clsx('memory-card', `memory-card-${memory.memory_type}`)}
      onClick={onClick}
    >
      <div className="flex items-center justify-between mb-2">
        <span className={clsx('memory-badge', `memory-${memory.memory_type}`)}>
          {memoryTypeLabels[memory.memory_type]}
        </span>
        <span className="text-xs text-gray-500 dark:text-gray-400">
          {formatDate(memory.created_at)}
        </span>
      </div>
      <p className="text-sm text-gray-700 dark:text-gray-300 line-clamp-3">
        {memory.content}
      </p>
      {memory.access_count > 0 && (
        <div className="mt-2 text-xs text-gray-400 dark:text-gray-500">
          Accessed {memory.access_count} time{memory.access_count !== 1 ? 's' : ''}
        </div>
      )}
    </div>
  );
}

export default function MemoryPanel({
  onMemoryClick,
  maxCoreMemories = 5,
  maxRecentMemories = 10,
}: MemoryPanelProps) {
  const [coreMemories, setCoreMemories] = useState<Memory[]>([]);
  const [recentMemories, setRecentMemories] = useState<Memory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadMemories = async () => {
      try {
        const data = await api.getCoreMemories({
          core_limit: maxCoreMemories,
          recent_limit: maxRecentMemories,
        });
        setCoreMemories(data.core_memories);
        setRecentMemories(data.recent_memories);
        setError(null);
      } catch (err) {
        console.error('Failed to load memories:', err);
        setError('Failed to load memories');
      } finally {
        setLoading(false);
      }
    };

    loadMemories();

    // Refresh memories every 30 seconds
    const interval = setInterval(loadMemories, 30000);
    return () => clearInterval(interval);
  }, [maxCoreMemories, maxRecentMemories]);

  const totalMemories = coreMemories.length + recentMemories.length;

  return (
    <div className="flex flex-col h-full border-t-4 border-amber-500 rounded-lg bg-white dark:bg-gray-800 shadow">
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b dark:border-gray-700">
        <h3 className="font-semibold text-gray-900 dark:text-gray-100">Memories</h3>
        <div className="flex items-center gap-2">
          <div
            className={clsx(
              'w-2 h-2 rounded-full',
              loading ? 'bg-yellow-500' : error ? 'bg-red-500' : 'bg-green-500'
            )}
          />
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {totalMemories}
          </span>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-2 space-y-3">
        {loading ? (
          <div className="text-center text-gray-500 dark:text-gray-400 py-8">
            <p className="text-sm">Loading memories...</p>
          </div>
        ) : error ? (
          <div className="text-center text-red-500 py-8">
            <p className="text-sm">{error}</p>
          </div>
        ) : totalMemories === 0 ? (
          <div className="text-center text-gray-500 dark:text-gray-400 py-8">
            <p className="text-sm">No memories yet</p>
            <p className="text-xs mt-1">Memories will appear after sleep consolidation</p>
          </div>
        ) : (
          <>
            {/* Core memories (L3) at the top */}
            {coreMemories.length > 0 && (
              <div>
                <div className="flex items-center gap-2 mb-2 px-1">
                  <span className="text-xs font-medium text-amber-600 dark:text-amber-400 uppercase tracking-wide">
                    Core Identity
                  </span>
                  <div className="flex-1 h-px bg-amber-200 dark:bg-amber-700" />
                </div>
                <div className="space-y-2">
                  {coreMemories.map((memory) => (
                    <MemoryCard
                      key={memory.memory_id}
                      memory={memory}
                      onClick={() => onMemoryClick?.(memory)}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Recent memories (L1/L2) */}
            {recentMemories.length > 0 && (
              <div>
                <div className="flex items-center gap-2 mb-2 px-1">
                  <span className="text-xs font-medium text-teal-600 dark:text-teal-400 uppercase tracking-wide">
                    Recent
                  </span>
                  <div className="flex-1 h-px bg-teal-200 dark:bg-teal-700" />
                </div>
                <div className="space-y-2">
                  {recentMemories.map((memory) => (
                    <MemoryCard
                      key={memory.memory_id}
                      memory={memory}
                      onClick={() => onMemoryClick?.(memory)}
                    />
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
