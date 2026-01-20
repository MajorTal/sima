'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import type { SystemStatus } from '@/lib/types';

export default function AdminPage() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);

  // Admin authentication state
  const [adminAuthenticated, setAdminAuthenticated] = useState(false);
  const [adminUsername, setAdminUsername] = useState('');
  const [adminPassword, setAdminPassword] = useState('');
  const [adminError, setAdminError] = useState('');
  const [adminLoading, setAdminLoading] = useState(false);

  // Reset confirmation state
  const [showResetConfirm, setShowResetConfirm] = useState(false);
  const [resetLoading, setResetLoading] = useState(false);
  const [resetResult, setResetResult] = useState<{
    events_deleted: number;
    traces_deleted: number;
    memories_deleted: number;
  } | null>(null);

  useEffect(() => {
    // Check if admin is already authenticated
    const adminToken = api.getAdminToken();
    if (adminToken) {
      setAdminAuthenticated(true);
    }

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

  const handleAdminLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setAdminError('');
    setAdminLoading(true);
    try {
      await api.adminLogin(adminUsername, adminPassword);
      setAdminAuthenticated(true);
      setAdminUsername('');
      setAdminPassword('');
    } catch (err) {
      setAdminError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setAdminLoading(false);
    }
  };

  const handleAdminLogout = () => {
    api.clearAdminToken();
    setAdminAuthenticated(false);
    setResetResult(null);
  };

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

  const handleReset = async () => {
    setResetLoading(true);
    try {
      const result = await api.resetSystem();
      setResetResult(result);
      setShowResetConfirm(false);
    } catch (error) {
      console.error('Failed to reset system:', error);
      if (error instanceof Error && error.message.includes('Admin access required')) {
        setAdminAuthenticated(false);
        api.clearAdminToken();
      }
      alert(error instanceof Error ? error.message : 'Reset failed');
    } finally {
      setResetLoading(false);
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
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 mb-6">
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

      {/* System Reset - Admin Only */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 border-2 border-red-200 dark:border-red-900">
        <h2 className="text-lg font-semibold mb-4 text-red-600 dark:text-red-400">
          System Reset
        </h2>
        <p className="text-sm text-gray-500 mb-4">
          Completely reset the system by deleting all events, traces, and memories.
          This action requires admin authentication and cannot be undone.
        </p>

        {!adminAuthenticated ? (
          <form onSubmit={handleAdminLogin} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Username
                </label>
                <input
                  type="text"
                  value={adminUsername}
                  onChange={(e) => setAdminUsername(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600"
                  placeholder="Admin username"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Password
                </label>
                <input
                  type="password"
                  value={adminPassword}
                  onChange={(e) => setAdminPassword(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600"
                  placeholder="Admin password"
                />
              </div>
            </div>
            {adminError && <p className="text-red-500 text-sm">{adminError}</p>}
            <button
              type="submit"
              disabled={adminLoading}
              className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition disabled:opacity-50"
            >
              {adminLoading ? 'Authenticating...' : 'Authenticate as Admin'}
            </button>
          </form>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-green-600 dark:text-green-400 text-sm font-medium">
                Authenticated as admin
              </span>
              <button
                onClick={handleAdminLogout}
                className="text-sm text-gray-500 hover:text-gray-700"
              >
                Logout
              </button>
            </div>

            {resetResult && (
              <div className="bg-red-50 dark:bg-red-900/20 p-4 rounded-lg">
                <p className="font-medium text-red-800 dark:text-red-200">Reset Complete</p>
                <ul className="text-sm text-red-700 dark:text-red-300 mt-2">
                  <li>Events deleted: {resetResult.events_deleted}</li>
                  <li>Traces deleted: {resetResult.traces_deleted}</li>
                  <li>Memories deleted: {resetResult.memories_deleted}</li>
                </ul>
              </div>
            )}

            {!showResetConfirm ? (
              <button
                onClick={() => setShowResetConfirm(true)}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition"
              >
                Reset System
              </button>
            ) : (
              <div className="bg-red-50 dark:bg-red-900/20 p-4 rounded-lg">
                <p className="font-bold text-red-800 dark:text-red-200 mb-4">
                  Are you sure?
                </p>
                <p className="text-sm text-red-700 dark:text-red-300 mb-4">
                  This will permanently delete all events, traces, and memories.
                  This action cannot be undone.
                </p>
                <div className="flex gap-4">
                  <button
                    onClick={handleReset}
                    disabled={resetLoading}
                    className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition disabled:opacity-50"
                  >
                    {resetLoading ? 'Resetting...' : 'Yes, Reset Everything'}
                  </button>
                  <button
                    onClick={() => setShowResetConfirm(false)}
                    disabled={resetLoading}
                    className="px-4 py-2 bg-gray-300 text-gray-700 rounded-lg hover:bg-gray-400 transition disabled:opacity-50"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
