/**
 * SigmaVault NAS OS - Card Component
 * @module components/ui/Card
 *
 * Flexible card container with header, content, and footer sections.
 */

import * as React from "react";

// ============================================================================
// Types
// ============================================================================

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Visual style variant */
  variant?: "default" | "outlined" | "elevated" | "ghost";
  /** Padding size */
  padding?: "none" | "sm" | "md" | "lg";
  /** Whether the card is interactive (hoverable) */
  interactive?: boolean;
}

export interface CardHeaderProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'title'> {
  /** Title text */
  title?: React.ReactNode;
  /** Subtitle or description */
  subtitle?: React.ReactNode;
  /** Action elements (buttons, icons) */
  actions?: React.ReactNode;
}

export interface CardContentProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Remove default padding */
  noPadding?: boolean;
  /** Padding size */
  padding?: "none" | "sm" | "md" | "lg";
}

export interface CardFooterProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Alignment of footer content */
  align?: "left" | "center" | "right" | "between";
}

// ============================================================================
// Styles
// ============================================================================

const baseStyles = "rounded-xl overflow-hidden";

const variantStyles: Record<NonNullable<CardProps["variant"]>, string> = {
  default: "bg-bg-secondary border border-border-primary",
  outlined: "bg-transparent border border-border-secondary",
  elevated: "bg-bg-secondary shadow-lg shadow-black/20",
  ghost: "bg-transparent",
};

const paddingStyles: Record<NonNullable<CardProps["padding"]>, string> = {
  none: "",
  sm: "p-3",
  md: "p-4",
  lg: "p-6",
};

const interactiveStyles = `
  cursor-pointer
  transition-all duration-200
  hover:border-border-hover hover:shadow-md hover:shadow-black/10
  focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-bg-primary
`;

// ============================================================================
// Card Component
// ============================================================================

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
  (
    {
      className = "",
      variant = "default",
      padding = "none",
      interactive = false,
      children,
      ...props
    },
    ref
  ) => {
    const combinedClassName = [
      baseStyles,
      variantStyles[variant],
      paddingStyles[padding],
      interactive ? interactiveStyles : "",
      className,
    ]
      .join(" ")
      .replace(/\s+/g, " ")
      .trim();

    return (
      <div
        ref={ref}
        className={combinedClassName}
        role={interactive ? "button" : undefined}
        tabIndex={interactive ? 0 : undefined}
        {...props}
      >
        {children}
      </div>
    );
  }
);

Card.displayName = "Card";

// ============================================================================
// Card Header Component
// ============================================================================

export const CardHeader = React.forwardRef<HTMLDivElement, CardHeaderProps>(
  ({ className = "", title, subtitle, actions, children, ...props }, ref) => {
    const hasCustomChildren = !!children;

    return (
      <div
        ref={ref}
        className={`
          flex items-start justify-between gap-4
          px-4 py-3 border-b border-border-primary
          ${className}
        `.trim()}
        {...props}
      >
        {hasCustomChildren ? (
          children
        ) : (
          <>
            <div className="flex-1 min-w-0">
              {title && (
                <h3 className="text-lg font-semibold text-text-primary truncate">
                  {title}
                </h3>
              )}
              {subtitle && (
                <p className="text-sm text-text-secondary mt-0.5 truncate">
                  {subtitle}
                </p>
              )}
            </div>
            {actions && (
              <div className="flex items-center gap-2 shrink-0">{actions}</div>
            )}
          </>
        )}
      </div>
    );
  }
);

CardHeader.displayName = "CardHeader";

// ============================================================================
// Card Content Component
// ============================================================================

const contentPaddingStyles: Record<NonNullable<CardContentProps["padding"]>, string> = {
  none: "",
  sm: "p-3",
  md: "p-4",
  lg: "p-6",
};

export const CardContent = React.forwardRef<HTMLDivElement, CardContentProps>(
  ({ className = "", noPadding = false, padding, children, ...props }, ref) => {
    // padding prop takes precedence over noPadding
    const paddingClass = padding 
      ? contentPaddingStyles[padding] 
      : (noPadding ? "" : "p-4");
    
    return (
      <div
        ref={ref}
        className={`
          ${paddingClass}
          ${className}
        `.trim()}
        {...props}
      >
        {children}
      </div>
    );
  }
);

CardContent.displayName = "CardContent";

// ============================================================================
// Card Footer Component
// ============================================================================

const footerAlignStyles: Record<
  NonNullable<CardFooterProps["align"]>,
  string
> = {
  left: "justify-start",
  center: "justify-center",
  right: "justify-end",
  between: "justify-between",
};

export const CardFooter = React.forwardRef<HTMLDivElement, CardFooterProps>(
  ({ className = "", align = "right", children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={`
          flex items-center gap-3
          px-4 py-3 border-t border-border-primary
          ${footerAlignStyles[align]}
          ${className}
        `.trim()}
        {...props}
      >
        {children}
      </div>
    );
  }
);

CardFooter.displayName = "CardFooter";

// ============================================================================
// Convenience Export
// ============================================================================

export default Object.assign(Card, {
  Header: CardHeader,
  Content: CardContent,
  Footer: CardFooter,
});
