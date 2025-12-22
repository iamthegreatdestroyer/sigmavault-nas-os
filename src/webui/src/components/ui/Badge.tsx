/**
 * SigmaVault NAS OS - Badge Component
 * @module components/ui/Badge
 *
 * Status indicators and labels.
 */

import * as React from "react";

// ============================================================================
// Types
// ============================================================================

export type BadgeVariant =
  | "default"
  | "primary"
  | "success"
  | "warning"
  | "error"
  | "info";

export type BadgeSize = "sm" | "md" | "lg";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  /** Visual style variant */
  variant?: BadgeVariant;
  /** Size of the badge */
  size?: BadgeSize;
  /** Show dot indicator */
  dot?: boolean;
  /** Dot color (overrides variant) */
  dotColor?: string;
}

// ============================================================================
// Styles
// ============================================================================

const baseStyles = `
  inline-flex items-center justify-center
  font-medium rounded-full
  whitespace-nowrap
`;

const variantStyles: Record<BadgeVariant, string> = {
  default: "bg-bg-tertiary text-text-secondary border border-border-primary",
  primary: "bg-primary/20 text-primary",
  success: "bg-status-success/20 text-status-success",
  warning: "bg-status-warning/20 text-status-warning",
  error: "bg-status-error/20 text-status-error",
  info: "bg-status-info/20 text-status-info",
};

const sizeStyles: Record<BadgeSize, string> = {
  sm: "h-5 px-2 text-xs gap-1",
  md: "h-6 px-2.5 text-xs gap-1.5",
  lg: "h-7 px-3 text-sm gap-2",
};

const dotVariantColors: Record<BadgeVariant, string> = {
  default: "bg-text-muted",
  primary: "bg-primary",
  success: "bg-status-success",
  warning: "bg-status-warning",
  error: "bg-status-error",
  info: "bg-status-info",
};

// ============================================================================
// Component
// ============================================================================

export const Badge = React.forwardRef<HTMLSpanElement, BadgeProps>(
  (
    {
      className = "",
      variant = "default",
      size = "md",
      dot = false,
      dotColor,
      children,
      ...props
    },
    ref
  ) => {
    const combinedClassName = [
      baseStyles,
      variantStyles[variant],
      sizeStyles[size],
      className,
    ]
      .join(" ")
      .replace(/\s+/g, " ")
      .trim();

    const dotSizes: Record<BadgeSize, string> = {
      sm: "h-1.5 w-1.5",
      md: "h-2 w-2",
      lg: "h-2.5 w-2.5",
    };

    return (
      <span ref={ref} className={combinedClassName} {...props}>
        {dot && (
          <span
            className={`
              ${dotSizes[size]} rounded-full shrink-0
              ${dotColor ? "" : dotVariantColors[variant]}
            `}
            style={dotColor ? { backgroundColor: dotColor } : undefined}
            aria-hidden="true"
          />
        )}
        {children}
      </span>
    );
  }
);

Badge.displayName = "Badge";

// ============================================================================
// Status Badge Component
// ============================================================================

export interface StatusBadgeProps extends Omit<BadgeProps, "variant" | "dot"> {
  /** Status type */
  status: "online" | "offline" | "idle" | "busy" | "error" | "warning";
}

const statusConfig: Record<
  StatusBadgeProps["status"],
  { variant: BadgeVariant; label: string }
> = {
  online: { variant: "success", label: "Online" },
  offline: { variant: "default", label: "Offline" },
  idle: { variant: "warning", label: "Idle" },
  busy: { variant: "info", label: "Busy" },
  error: { variant: "error", label: "Error" },
  warning: { variant: "warning", label: "Warning" },
};

export const StatusBadge = React.forwardRef<HTMLSpanElement, StatusBadgeProps>(
  ({ status, children, ...props }, ref) => {
    const config = statusConfig[status];

    return (
      <Badge ref={ref} variant={config.variant} dot {...props}>
        {children || config.label}
      </Badge>
    );
  }
);

StatusBadge.displayName = "StatusBadge";

export default Badge;
