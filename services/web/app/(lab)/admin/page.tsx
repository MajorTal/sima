'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import type { SystemStatus } from '@/lib/types';

export default function AdminPage() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    const loadStatus = async () => {
      try {
        const data = await api.getSystemStatus();
        setStatus(data);
      } catch (error) {
        console.error('Failed to load status:', error);
      } finally {
        setLoading(false);
      }
    };
    loadStatus();
  }, []);

  const handlePauseToggle = async () => {
    if (!status) return;
    setActionLoading(true);
    try {
      const newStatus = await api.setSystemPaused(!status.paused);
      setStatus(newStatus);
    } catch (error) {
      console.error('Failed to toggle pause:', error);
    } finally {
      setActionLoading(false);
    }
  };

  const handleTriggerTick = async (tickType: string) => {
    setActionLoading(true);
    try {
      await api.triggerTick(tickType);
      alert(`Triggered ${tickType} tick`);
    } catch (error) {
      console.error('Failed to trigger tick:', error);
      alert('Failed to trigger tick');
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-gray-500">Loading...</p>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">
        Admin Controls
      </h1>

      {/* System Status */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">System Status</h2>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div
              className={`w-4 h-4 rounded-full ${
                status?.paused ? 'bg-yellow-500' : 'bg-green-500'
              }`}
            />
            <span className="text-lg font-medium">
              {status?.paused ? 'Paused' : 'Running'}
            </span>
          </div>
          <button
            onClick={handlePauseToggle}
            disabled={actionLoading}
            className={`px-4 py-2 rounded-lg font-medium transition ${
              status?.paused
                ? 'bg-green-600 text-white hover:bg-green-700'
                : 'bg-yellow-600 text-white hover:bg-yellow-700'
            } disabled:opacity-50`}
          >
            {actionLoading
              ? '...'
              : status?.paused
              ? 'Resume System'
              : 'Pause System'}
          </button>
        </div>
        <p className="text-sm text-gray-500 mt-2">
          {status?.paused
            ? 'The system is paused. No new traces will be processed.'
            : 'The system is running normally.'}
        </p>
      </div>

      {/* Manual Triggers */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">Manual Triggers</h2>
        <p className="text-sm text-gray-500 mb-4">
          Manually trigger cognitive events for testing purposes.
        </p>
        <div className="flex gap-4">
          <button
            onClick={() => handleTriggerTick('minute')}
            disabled={actionLoading || status?.paused}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition"
          >
            Trigger Minute Tick
          </button>
          <button
            onClick={() => handleTriggerTick('autonomous')}
            disabled={actionLoading || status?.paused}
            className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 transition"
          >
            Trigger Autonomous Tick
          </button>
        </div>
        {status?.paused && (
          <p className="text-sm text-yellow-600 mt-2">
            System is paused. Resume to trigger ticks.
          </p>
        )}
      </div>
    </div>
  );
}
