/**
 * SigmaVault NAS OS - Tooltip Component
 * @module components/ui/Tooltip
 *
 * Accessible tooltip using Radix Tooltip primitive.
 */

import * as React from "react";
import * as TooltipPrimitive from "@radix-ui/react-tooltip";

// ============================================================================
// Types
// ============================================================================

export interface TooltipProps {
  /** Tooltip trigger element */
  children: React.ReactNode;
  /** Tooltip content */
  content: React.ReactNode;
  /** Side to show tooltip */
  side?: "top" | "right" | "bottom" | "left";
  /** Alignment relative to trigger */
  align?: "start" | "center" | "end";
  /** Delay before showing (ms) */
  delayDuration?: number;
  /** Skip delay on hover */
  skipDelayDuration?: number;
  /** Whether tooltip is open (controlled) */
  open?: boolean;
  /** Callback when open state changes */
  onOpenChange?: (open: boolean) => void;
  /** Offset from trigger (px) */
  sideOffset?: number;
}

// ============================================================================
// Provider
// ============================================================================

export function TooltipProvider({
  children,
  delayDuration = 300,
  skipDelayDuration = 100,
}: {
  children: React.ReactNode;
  delayDuration?: number;
  skipDelayDuration?: number;
}) {
  return (
    <TooltipPrimitive.Provider
      delayDuration={delayDuration}
      skipDelayDuration={skipDelayDuration}
    >
      {children}
    </TooltipPrimitive.Provider>
  );
}

// ============================================================================
// Tooltip Component
// ============================================================================

export function Tooltip({
  children,
  content,
  side = "top",
  align = "center",
  delayDuration,
  open,
  onOpenChange,
  sideOffset = 4,
}: TooltipProps) {
  return (
    <TooltipPrimitive.Root
      open={open}
      onOpenChange={onOpenChange}
      delayDuration={delayDuration}
    >
      <TooltipPrimitive.Trigger asChild>{children}</TooltipPrimitive.Trigger>

      <TooltipPrimitive.Portal>
        <TooltipPrimitive.Content
          side={side}
          align={align}
          sideOffset={sideOffset}
          className="
            z-50
            px-3 py-1.5
            text-sm text-text-primary
            bg-bg-tertiary
            border border-border-primary
            rounded-lg shadow-lg shadow-black/20
            select-none
            animate-in fade-in-0 zoom-in-95
            data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95
            data-[side=bottom]:slide-in-from-top-2
            data-[side=left]:slide-in-from-right-2
            data-[side=right]:slide-in-from-left-2
            data-[side=top]:slide-in-from-bottom-2
          "
        >
          {content}
          <TooltipPrimitive.Arrow
            className="fill-bg-tertiary"
            width={12}
            height={6}
          />
        </TooltipPrimitive.Content>
      </TooltipPrimitive.Portal>
    </TooltipPrimitive.Root>
  );
}

// ============================================================================
// Simple Tooltip (without provider)
// ============================================================================

export function SimpleTooltip({ children, content, ...props }: TooltipProps) {
  return (
    <TooltipPrimitive.Provider delayDuration={200}>
      <Tooltip content={content} {...props}>
        {children}
      </Tooltip>
    </TooltipPrimitive.Provider>
  );
}

export default Tooltip;
