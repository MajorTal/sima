'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import type { TheoryIndicators } from '@/lib/types';
import {
  MetricCard,
  ProgressBar,
  IndicatorSection,
} from '@/components/IndicatorChart';

export default function IndicatorsDashboardPage() {
  const [indicators, setIndicators] = useState<TheoryIndicators | null>(null);
  const [loading, setLoading] = useState(true);
  const [windowHours, setWindowHours] = useState(24);

  useEffect(() => {
    const loadIndicators = async () => {
      setLoading(true);
      try {
        const data = await api.getIndicators(windowHours);
        setIndicators(data);
      } catch (error) {
        console.error('Failed to load indicators:', error);
      } finally {
        setLoading(false);
      }
    };
    loadIndicators();
  }, [windowHours]);

  if (loading || !indicators) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-gray-500">Loading indicators...</p>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Theory Indicators
          </h1>
          <p className="text-gray-500">
            Metrics from consciousness theory implementations
          </p>
        </div>
        <select
          value={windowHours}
          onChange={(e) => setWindowHours(Number(e.target.value))}
          className="px-3 py-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600"
        >
          <option value={1}>Last hour</option>
          <option value={6}>Last 6 hours</option>
          <option value={24}>Last 24 hours</option>
          <option value={72}>Last 3 days</option>
          <option value={168}>Last week</option>
        </select>
      </div>

      {/* Overview */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <MetricCard
          title="Total Traces"
          value={indicators.overview.total_traces}
          color="blue"
        />
        <MetricCard
          title="Total Events"
          value={indicators.overview.total_events}
          color="purple"
        />
        <MetricCard
          title="Tokens Used"
          value={indicators.overview.total_tokens.toLocaleString()}
          color="green"
        />
        <MetricCard
          title="Total Cost"
          value={`$${indicators.overview.total_cost_usd.toFixed(2)}`}
          color="yellow"
        />
      </div>

      {/* Theory sections */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* RPT */}
        <IndicatorSection
          title="Recurrent Processing Theory (RPT)"
          description="Measures of recurrent processing and stability"
        >
          <ProgressBar
            label="Avg Recurrence Steps"
            value={indicators.rpt.avg_recurrence_steps}
            max={5}
            color="green"
          />
          <ProgressBar
            label="Avg Stability Score"
            value={indicators.rpt.avg_stability_score}
            max={1}
            color="green"
          />
          <ProgressBar
            label="Revision Frequency"
            value={indicators.rpt.revision_frequency}
            max={1}
            color="yellow"
          />
        </IndicatorSection>

        {/* GWT */}
        <IndicatorSection
          title="Global Workspace Theory (GWT)"
          description="Workspace capacity and broadcasting metrics"
        >
          <div className="grid grid-cols-2 gap-4">
            <MetricCard
              title="Parallel Modules"
              value={indicators.gwt.parallel_module_count}
              color="purple"
            />
            <MetricCard
              title="Avg Selected"
              value={indicators.gwt.avg_selected_items.toFixed(1)}
              color="purple"
            />
          </div>
          <ProgressBar
            label="Avg Candidates/Trace"
            value={indicators.gwt.avg_candidates_per_trace}
            max={20}
            color="purple"
          />
          <ProgressBar
            label="Broadcast Rate"
            value={indicators.gwt.broadcast_rate}
            max={1}
            color="purple"
          />
        </IndicatorSection>

        {/* HOT */}
        <IndicatorSection
          title="Higher-Order Thought (HOT)"
          description="Metacognition and belief monitoring"
        >
          <ProgressBar
            label="Avg Confidence"
            value={indicators.hot.avg_confidence}
            max={1}
            color="blue"
          />
          <ProgressBar
            label="Belief Revision Rate"
            value={indicators.hot.belief_revision_rate}
            max={1}
            color="blue"
          />
          <ProgressBar
            label="Metacog Reports/Trace"
            value={indicators.hot.metacog_reports_per_trace}
            max={3}
            color="blue"
          />
        </IndicatorSection>

        {/* AST */}
        <IndicatorSection
          title="Attention Schema Theory (AST)"
          description="Attention modeling and prediction"
        >
          <ProgressBar
            label="Prediction Accuracy"
            value={indicators.ast.prediction_accuracy}
            max={1}
            color="red"
          />
          <ProgressBar
            label="Focus Shift Rate"
            value={indicators.ast.focus_shift_rate}
            max={1}
            color="red"
          />
        </IndicatorSection>
      </div>
    </div>
  );
}
