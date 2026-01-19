'use client';

import { clsx } from 'clsx';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  color?: 'blue' | 'purple' | 'green' | 'yellow' | 'red';
}

export function MetricCard({ title, value, subtitle, color = 'blue' }: MetricCardProps) {
  const colorClasses = {
    blue: 'border-blue-500 bg-blue-50 dark:bg-blue-900/20',
    purple: 'border-purple-500 bg-purple-50 dark:bg-purple-900/20',
    green: 'border-green-500 bg-green-50 dark:bg-green-900/20',
    yellow: 'border-yellow-500 bg-yellow-50 dark:bg-yellow-900/20',
    red: 'border-red-500 bg-red-50 dark:bg-red-900/20',
  };

  return (
    <div
      className={clsx(
        'p-4 rounded-lg border-l-4',
        colorClasses[color]
      )}
    >
      <p className="text-sm text-gray-600 dark:text-gray-400">{title}</p>
      <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">{value}</p>
      {subtitle && (
        <p className="text-xs text-gray-500 dark:text-gray-500">{subtitle}</p>
      )}
    </div>
  );
}

interface ProgressBarProps {
  label: string;
  value: number;
  max?: number;
  color?: 'blue' | 'purple' | 'green' | 'yellow' | 'red';
}

export function ProgressBar({ label, value, max = 1, color = 'blue' }: ProgressBarProps) {
  const percentage = Math.min((value / max) * 100, 100);

  const colorClasses = {
    blue: 'bg-blue-500',
    purple: 'bg-purple-500',
    green: 'bg-green-500',
    yellow: 'bg-yellow-500',
    red: 'bg-red-500',
  };

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="text-gray-600 dark:text-gray-400">{label}</span>
        <span className="font-medium text-gray-900 dark:text-gray-100">
          {typeof value === 'number' ? value.toFixed(2) : value}
        </span>
      </div>
      <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
        <div
          className={clsx('h-full rounded-full transition-all', colorClasses[color])}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}

interface IndicatorSectionProps {
  title: string;
  description?: string;
  children: React.ReactNode;
}

export function IndicatorSection({ title, description, children }: IndicatorSectionProps) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-1">
        {title}
      </h3>
      {description && (
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">{description}</p>
      )}
      <div className="space-y-4">{children}</div>
    </div>
  );
}
