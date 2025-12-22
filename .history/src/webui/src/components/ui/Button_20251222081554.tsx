/**
 * SigmaVault NAS OS - Button Component
 * @module components/ui/Button
 *
 * Accessible button component with multiple variants and sizes.
 * Uses Radix Slot for composition (asChild pattern).
 */

import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { Loader2 } from "lucide-react";

// ============================================================================
// Types
// ============================================================================

export type ButtonVariant =
  | "primary"
  | "secondary"
  | "ghost"
  | "danger"
  | "success"
  | "outline";

export type ButtonSize = "sm" | "md" | "lg" | "icon";

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  /** Visual style variant */
  variant?: ButtonVariant;
  /** Size of the button */
  size?: ButtonSize;
  /** Render as child component (for links styled as buttons) */
  asChild?: boolean;
  /** Show loading spinner */
  loading?: boolean;
  /** Icon to show before children */
  leftIcon?: React.ReactNode;
  /** Icon to show after children */
  rightIcon?: React.ReactNode;
}

// ============================================================================
// Styles
// ============================================================================

const baseStyles = `
  inline-flex items-center justify-center gap-2
  font-medium rounded-lg
  transition-all duration-200
  focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-bg-primary
  disabled:pointer-events-none disabled:opacity-50
  select-none
`;

const variantStyles: Record<ButtonVariant, string> = {
  primary: `
    bg-primary text-white
    hover:bg-primary-hover
    active:bg-primary-active
    shadow-sm hover:shadow-md
  `,
  secondary: `
    bg-bg-tertiary text-text-primary
    hover:bg-bg-hover
    active:bg-bg-tertiary
    border border-border-primary
  `,
  ghost: `
    text-text-secondary
    hover:bg-bg-hover hover:text-text-primary
    active:bg-bg-tertiary
  `,
  danger: `
    bg-status-error text-white
    hover:bg-red-600
    active:bg-red-700
    shadow-sm hover:shadow-md
  `,
  success: `
    bg-status-success text-white
    hover:bg-green-600
    active:bg-green-700
    shadow-sm hover:shadow-md
  `,
  outline: `
    border-2 border-primary text-primary
    hover:bg-primary hover:text-white
    active:bg-primary-active
  `,
};

const sizeStyles: Record<ButtonSize, string> = {
  sm: "h-8 px-3 text-sm",
  md: "h-10 px-4 text-sm",
  lg: "h-12 px-6 text-base",
  icon: "h-10 w-10 p-0",
};

// ============================================================================
// Component
// ============================================================================

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className = "",
      variant = "primary",
      size = "md",
      asChild = false,
      loading = false,
      leftIcon,
      rightIcon,
      disabled,
      children,
      ...props
    },
    ref
  ) => {
    const Comp = asChild ? Slot : "button";
    const isDisabled = disabled || loading;

    // Combine all styles
    const combinedClassName = [
      baseStyles,
      variantStyles[variant],
      sizeStyles[size],
      className,
    ]
      .join(" ")
      .replace(/\s+/g, " ")
      .trim();

    return (
      <Comp
        className={combinedClassName}
        ref={ref}
        disabled={isDisabled}
        aria-disabled={isDisabled}
        aria-busy={loading}
        {...props}
      >
        {loading ? (
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
        ) : leftIcon ? (
          <span className="shrink-0" aria-hidden="true">
            {leftIcon}
          </span>
        ) : null}

        {children}

        {rightIcon && !loading && (
          <span className="shrink-0" aria-hidden="true">
            {rightIcon}
          </span>
        )}
      </Comp>
    );
  }
);

Button.displayName = "Button";

// ============================================================================
// Icon Button Variant
// ============================================================================

export interface IconButtonProps
  extends Omit<ButtonProps, "size" | "leftIcon" | "rightIcon" | "children"> {
  /** Accessible label for the button */
  "aria-label": string;
  /** Icon to display */
  icon: React.ReactNode;
  /** Size of the icon button */
  size?: "sm" | "md" | "lg";
}

const iconSizeStyles: Record<"sm" | "md" | "lg", string> = {
  sm: "h-8 w-8 p-0",
  md: "h-10 w-10 p-0",
  lg: "h-12 w-12 p-0",
};

export const IconButton = React.forwardRef<HTMLButtonElement, IconButtonProps>(
  ({ icon, size = "md", className = "", ...props }, ref) => {
    const combinedClassName = [
      baseStyles,
      variantStyles[props.variant || "ghost"],
      iconSizeStyles[size],
      className,
    ]
      .join(" ")
      .replace(/\s+/g, " ")
      .trim();

    return (
      <button className={combinedClassName} ref={ref} {...props}>
        {props.loading ? (
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
        ) : (
          <span aria-hidden="true">{icon}</span>
        )}
      </button>
    );
  }
);

IconButton.displayName = "IconButton";

export default Button;
