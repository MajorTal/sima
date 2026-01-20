'use client';

import { useState } from 'react';
import Link from 'next/link';
import type { Event, Memory } from '@/lib/types';
import FourPanelLayout from '@/components/FourPanelLayout';

export default function PublicHomePage() {
  const [selectedEvent, setSelectedEvent] = useState<Event | null>(null);
  const [selectedMemory, setSelectedMemory] = useState<Memory | null>(null);

  const handleEventClick = (event: Event) => {
    setSelectedEvent(event);
    setSelectedMemory(null);
  };

  const handleMemoryClick = (memory: Memory) => {
    setSelectedMemory(memory);
    setSelectedEvent(null);
  };

  const closeModal = () => {
    setSelectedEvent(null);
    setSelectedMemory(null);
  };

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 shadow flex-shrink-0">
        <div className="max-w-full mx-auto px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                SIMA
              </h1>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Consciousness Research Agent
              </p>
            </div>
            <Link
              href="/lab"
              className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition text-sm"
            >
              Lab Access
            </Link>
          </div>
        </div>
      </header>

      {/* Main content - 4 panel layout */}
      <main className="flex-1 p-4 overflow-hidden">
        <FourPanelLayout
          onEventClick={handleEventClick}
          onMemoryClick={handleMemoryClick}
        />
      </main>

      {/* Event detail modal */}
      {selectedEvent && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50"
          onClick={closeModal}
        >
          <div
            className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] overflow-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-4 border-b dark:border-gray-700 flex items-center justify-between">
              <h3 className="font-semibold text-gray-900 dark:text-white">
                Event Details
              </h3>
              <button
                onClick={closeModal}
                className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="p-4 space-y-3">
              <div>
                <span className="text-xs text-gray-500 dark:text-gray-400 uppercase">Actor</span>
                <p className="text-gray-900 dark:text-white">{selectedEvent.actor}</p>
              </div>
              <div>
                <span className="text-xs text-gray-500 dark:text-gray-400 uppercase">Stream</span>
                <p className="text-gray-900 dark:text-white">{selectedEvent.stream}</p>
              </div>
              <div>
                <span className="text-xs text-gray-500 dark:text-gray-400 uppercase">Type</span>
                <p className="text-gray-900 dark:text-white">{selectedEvent.event_type}</p>
              </div>
              <div>
                <span className="text-xs text-gray-500 dark:text-gray-400 uppercase">Time</span>
                <p className="text-gray-900 dark:text-white">
                  {new Date(selectedEvent.ts).toLocaleString()}
                </p>
              </div>
              {selectedEvent.content_text && (
                <div>
                  <span className="text-xs text-gray-500 dark:text-gray-400 uppercase">Content</span>
                  <p className="text-gray-900 dark:text-white whitespace-pre-wrap">
                    {selectedEvent.content_text}
                  </p>
                </div>
              )}
              {selectedEvent.content_json && (
                <div>
                  <span className="text-xs text-gray-500 dark:text-gray-400 uppercase">Data</span>
                  <pre className="text-sm text-gray-900 dark:text-white bg-gray-100 dark:bg-gray-700 p-2 rounded overflow-auto">
                    {JSON.stringify(selectedEvent.content_json, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Memory detail modal */}
      {selectedMemory && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50"
          onClick={closeModal}
        >
          <div
            className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] overflow-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-4 border-b dark:border-gray-700 flex items-center justify-between">
              <h3 className="font-semibold text-gray-900 dark:text-white">
                Memory Details
              </h3>
              <button
                onClick={closeModal}
                className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="p-4 space-y-3">
              <div>
                <span className="text-xs text-gray-500 dark:text-gray-400 uppercase">Type</span>
                <p className="text-gray-900 dark:text-white">
                  {selectedMemory.memory_type === 'L3' ? 'Core Identity (L3)' :
                   selectedMemory.memory_type === 'L2' ? 'Consolidated (L2)' :
                   'Recent (L1)'}
                </p>
              </div>
              <div>
                <span className="text-xs text-gray-500 dark:text-gray-400 uppercase">Created</span>
                <p className="text-gray-900 dark:text-white">
                  {new Date(selectedMemory.created_at).toLocaleString()}
                </p>
              </div>
              <div>
                <span className="text-xs text-gray-500 dark:text-gray-400 uppercase">
                  Relevance Score
                </span>
                <p className="text-gray-900 dark:text-white">
                  {selectedMemory.relevance_score.toFixed(2)}
                </p>
              </div>
              <div>
                <span className="text-xs text-gray-500 dark:text-gray-400 uppercase">
                  Access Count
                </span>
                <p className="text-gray-900 dark:text-white">{selectedMemory.access_count}</p>
              </div>
              <div>
                <span className="text-xs text-gray-500 dark:text-gray-400 uppercase">Content</span>
                <p className="text-gray-900 dark:text-white whitespace-pre-wrap">
                  {selectedMemory.content}
                </p>
              </div>
              {selectedMemory.metadata_json && (
                <div>
                  <span className="text-xs text-gray-500 dark:text-gray-400 uppercase">Metadata</span>
                  <pre className="text-sm text-gray-900 dark:text-white bg-gray-100 dark:bg-gray-700 p-2 rounded overflow-auto">
                    {JSON.stringify(selectedMemory.metadata_json, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
