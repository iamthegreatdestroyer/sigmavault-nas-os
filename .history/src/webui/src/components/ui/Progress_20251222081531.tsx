/**
 * SigmaVault NAS OS - Progress Component
 * @module components/ui/Progress
 * 
 * Progress indicators using Radix Progress primitive.
 */

import * as React from 'react';
import * as ProgressPrimitive from '@radix-ui/react-progress';

// ============================================================================
// Types
// ============================================================================

export interface ProgressProps {
  /** Current progress value (0-100) */
  value: number;
  /** Maximum value */
  max?: number;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Color variant */
  variant?: 'primary' | 'success' | 'warning' | 'error';
  /** Show percentage label */
  showLabel?: boolean;
  /** Custom label */
  label?: string;
  /** Accessible label */
  'aria-label'?: string;
  /** Additional class names */
  className?: string;
}

export interface CircularProgressProps {
  /** Current progress value (0-100) */
  value: number;
  /** Size in pixels */
  size?: number;
  /** Stroke width */
  strokeWidth?: number;
  /** Color variant */
  variant?: 'primary' | 'success' | 'warning' | 'error';
  /** Show percentage in center */
  showLabel?: boolean;
  /** Custom label */
  label?: React.ReactNode;
  /** Additional class names */
  className?: string;
}

// ============================================================================
// Styles
// ============================================================================

const sizeStyles = {
  sm: 'h-1',
  md: 'h-2',
  lg: 'h-3',
};

const variantStyles = {
  primary: 'bg-primary',
  success: 'bg-status-success',
  warning: 'bg-status-warning',
  error: 'bg-status-error',
};

// ============================================================================
// Linear Progress Component
// ============================================================================

export const Progress = React.forwardRef<HTMLDivElement, ProgressProps>(
  (
    {
      value,
      max = 100,
      size = 'md',
      variant = 'primary',
      showLabel = false,
      label,
      className = '',
      ...props
    },
    ref
  ) => {
    const percentage = Math.min(100, Math.max(0, (value / max) * 100));

    return (
      <div className={`w-full ${className}`}>
        {(showLabel || label) && (
          <div className="flex justify-between items-center mb-1">
            {label && (
              <span className="text-sm text-text-secondary">{label}</span>
            )}
            {showLabel && (
              <span className="text-sm font-medium text-text-primary">
                {Math.round(percentage)}%
              </span>
            )}
          </div>
        )}
        
        <ProgressPrimitive.Root
          ref={ref}
          className={`
            relative overflow-hidden rounded-full
            bg-bg-tertiary
            ${sizeStyles[size]}
          `}
          value={value}
          max={max}
          {...props}
        >
          <ProgressPrimitive.Indicator
            className={`
              h-full rounded-full
              transition-transform duration-300 ease-out
              ${variantStyles[variant]}
            `}
            style={{ transform: `translateX(-${100 - percentage}%)` }}
          />
        </ProgressPrimitive.Root>
      </div>
    );
  }
);

Progress.displayName = 'Progress';

// ============================================================================
// Circular Progress Component
// ============================================================================

export function CircularProgress({
  value,
  size = 48,
  strokeWidth = 4,
  variant = 'primary',
  showLabel = true,
  label,
  className = '',
}: CircularProgressProps) {
  const percentage = Math.min(100, Math.max(0, value));
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (percentage / 100) * circumference;

  const variantColors = {
    primary: 'var(--color-primary)',
    success: 'var(--color-status-success)',
    warning: 'var(--color-status-warning)',
    error: 'var(--color-status-error)',
  };

  return (
    <div
      className={`relative inline-flex items-center justify-center ${className}`}
      style={{ width: size, height: size }}
      role="progressbar"
      aria-valuenow={percentage}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <svg width={size} height={size} className="-rotate-90">
        {/* Background circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth={strokeWidth}
          className="text-bg-tertiary"
        />
        
        {/* Progress circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={variantColors[variant]}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="transition-all duration-300 ease-out"
        />
      </svg>
      
      {showLabel && (
        <div className="absolute inset-0 flex items-center justify-center">
          {label || (
            <span className="text-sm font-medium text-text-primary">
              {Math.round(percentage)}%
            </span>
          )}
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Indeterminate Progress Component
// ============================================================================

export interface IndeterminateProgressProps {
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Color variant */
  variant?: 'primary' | 'success' | 'warning' | 'error';
  /** Additional class names */
  className?: string;
}

export function IndeterminateProgress({
  size = 'md',
  variant = 'primary',
  className = '',
}: IndeterminateProgressProps) {
  return (
    <div
      className={`
        relative overflow-hidden rounded-full
        bg-bg-tertiary
        ${sizeStyles[size]}
        ${className}
      `}
    >
      <div
        className={`
          absolute inset-y-0 w-1/3 rounded-full
          ${variantStyles[variant]}
          animate-[indeterminate_1.5s_ease-in-out_infinite]
        `}
        style={{
          animation: 'indeterminate 1.5s ease-in-out infinite',
        }}
      />
      <style>{`
        @keyframes indeterminate {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(400%); }
        }
      `}</style>
    </div>
  );
}

export default Progress;
