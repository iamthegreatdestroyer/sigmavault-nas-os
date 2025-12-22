/**
 * SigmaVault NAS OS - Spinner Component
 * @module components/ui/Spinner
 *
 * Loading indicators.
 */

import * as React from "react";
import { Loader2 } from "lucide-react";

// ============================================================================
// Types
// ============================================================================

export interface SpinnerProps {
  /** Size of the spinner */
  size?: "sm" | "md" | "lg" | "xl";
  /** Color variant */
  variant?: "default" | "primary" | "white";
  /** Additional class names */
  className?: string;
  /** Accessible label */
  label?: string;
}

export interface LoadingOverlayProps {
  /** Whether the overlay is visible */
  loading: boolean;
  /** Loading message */
  message?: string;
  /** Content to overlay */
  children: React.ReactNode;
  /** Overlay opacity */
  opacity?: number;
}

// ============================================================================
// Styles
// ============================================================================

const sizeStyles = {
  sm: "h-4 w-4",
  md: "h-6 w-6",
  lg: "h-8 w-8",
  xl: "h-12 w-12",
};

const variantStyles = {
  default: "text-text-muted",
  primary: "text-primary",
  white: "text-white",
};

// ============================================================================
// Spinner Component
// ============================================================================

export function Spinner({
  size = "md",
  variant = "default",
  className = "",
  label = "Loading...",
}: SpinnerProps) {
  return (
    <div
      role="status"
      aria-label={label}
      className={`inline-flex items-center justify-center ${className}`}
    >
      <Loader2
        className={`
          animate-spin
          ${sizeStyles[size]}
          ${variantStyles[variant]}
        `}
        aria-hidden="true"
      />
      <span className="sr-only">{label}</span>
    </div>
  );
}

// ============================================================================
// Dots Spinner
// ============================================================================

export function DotsSpinner({
  size = "md",
  variant = "default",
  className = "",
  label = "Loading...",
}: SpinnerProps) {
  const dotSize = {
    sm: "h-1.5 w-1.5",
    md: "h-2 w-2",
    lg: "h-2.5 w-2.5",
    xl: "h-3 w-3",
  };

  return (
    <div
      role="status"
      aria-label={label}
      className={`inline-flex items-center gap-1 ${className}`}
    >
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className={`
            rounded-full
            ${dotSize[size]}
            ${variantStyles[variant]}
            bg-current
            animate-pulse
          `}
          style={{
            animationDelay: `${i * 150}ms`,
            animationDuration: "600ms",
          }}
          aria-hidden="true"
        />
      ))}
      <span className="sr-only">{label}</span>
    </div>
  );
}

// ============================================================================
// Loading Overlay Component
// ============================================================================

export function LoadingOverlay({
  loading,
  message,
  children,
  opacity = 0.8,
}: LoadingOverlayProps) {
  return (
    <div className="relative">
      {children}

      {loading && (
        <div
          className="
            absolute inset-0 z-10
            flex flex-col items-center justify-center gap-3
            rounded-lg
          "
          style={{ backgroundColor: `rgba(15, 15, 15, ${opacity})` }}
        >
          <Spinner size="lg" variant="primary" />
          {message && (
            <span className="text-sm text-text-secondary">{message}</span>
          )}
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Full Page Loader
// ============================================================================

export interface FullPageLoaderProps {
  /** Loading message */
  message?: string;
  /** Logo or icon to display */
  logo?: React.ReactNode;
}

export function FullPageLoader({
  message = "Loading SigmaVault...",
  logo,
}: FullPageLoaderProps) {
  return (
    <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-bg-primary">
      {logo && <div className="mb-6">{logo}</div>}

      <div className="flex flex-col items-center gap-4">
        <Spinner size="xl" variant="primary" />
        {message && (
          <p className="text-lg text-text-secondary animate-pulse">{message}</p>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// Skeleton Loader
// ============================================================================

export interface SkeletonProps {
  /** Width of the skeleton */
  width?: string | number;
  /** Height of the skeleton */
  height?: string | number;
  /** Border radius */
  rounded?: "none" | "sm" | "md" | "lg" | "full";
  /** Additional class names */
  className?: string;
}

const roundedStyles = {
  none: "rounded-none",
  sm: "rounded-sm",
  md: "rounded-md",
  lg: "rounded-lg",
  full: "rounded-full",
};

export function Skeleton({
  width,
  height,
  rounded = "md",
  className = "",
}: SkeletonProps) {
  return (
    <div
      className={`
        bg-bg-tertiary
        animate-pulse
        ${roundedStyles[rounded]}
        ${className}
      `}
      style={{
        width: typeof width === "number" ? `${width}px` : width,
        height: typeof height === "number" ? `${height}px` : height,
      }}
      aria-hidden="true"
    />
  );
}

// ============================================================================
// Skeleton Text
// ============================================================================

export function SkeletonText({
  lines = 3,
  className = "",
}: {
  lines?: number;
  className?: string;
}) {
  return (
    <div className={`space-y-2 ${className}`}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          height={16}
          width={i === lines - 1 ? "60%" : "100%"}
          rounded="sm"
        />
      ))}
    </div>
  );
}

export default Spinner;
