/**
 * SigmaVault NAS OS - Modal Component
 * @module components/ui/Modal
 *
 * Accessible modal dialog using Radix Dialog primitives.
 */

import * as React from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { Button, IconButton } from "./Button";

// ============================================================================
// Types
// ============================================================================

export interface ModalProps {
  /** Whether the modal is open */
  open: boolean;
  /** Callback when open state changes */
  onOpenChange: (open: boolean) => void;
  /** Modal title */
  title?: React.ReactNode;
  /** Modal description */
  description?: React.ReactNode;
  /** Modal content */
  children: React.ReactNode;
  /** Size of the modal */
  size?: "sm" | "md" | "lg" | "xl" | "full";
  /** Whether to show close button */
  showCloseButton?: boolean;
  /** Whether clicking outside closes the modal */
  closeOnOverlayClick?: boolean;
  /** Footer content */
  footer?: React.ReactNode;
}

export interface ConfirmModalProps {
  /** Whether the modal is open */
  open: boolean;
  /** Callback when open state changes */
  onOpenChange: (open: boolean) => void;
  /** Modal title */
  title: string;
  /** Modal description */
  description: React.ReactNode;
  /** Confirm button text */
  confirmText?: string;
  /** Cancel button text */
  cancelText?: string;
  /** Confirm button variant */
  confirmVariant?: "primary" | "danger";
  /** Loading state */
  loading?: boolean;
  /** Callback when confirmed */
  onConfirm: () => void;
}

// ============================================================================
// Styles
// ============================================================================

const sizeStyles = {
  sm: "max-w-sm",
  md: "max-w-md",
  lg: "max-w-lg",
  xl: "max-w-xl",
  full: "max-w-[calc(100vw-2rem)] max-h-[calc(100vh-2rem)]",
};

// ============================================================================
// Modal Component
// ============================================================================

export function Modal({
  open,
  onOpenChange,
  title,
  description,
  children,
  size = "md",
  showCloseButton = true,
  closeOnOverlayClick = true,
  footer,
}: ModalProps) {
  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        {/* Overlay */}
        <DialogPrimitive.Overlay
          className="
            fixed inset-0 z-50
            bg-black/60 backdrop-blur-sm
            data-[state=open]:animate-in data-[state=closed]:animate-out
            data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0
          "
        />

        {/* Content */}
        <DialogPrimitive.Content
          className={`
            fixed left-1/2 top-1/2 z-50
            -translate-x-1/2 -translate-y-1/2
            w-full ${sizeStyles[size]}
            bg-bg-secondary
            border border-border-primary
            rounded-xl shadow-xl shadow-black/30
            overflow-hidden
            data-[state=open]:animate-in data-[state=closed]:animate-out
            data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0
            data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95
            data-[state=closed]:slide-out-to-left-1/2 data-[state=closed]:slide-out-to-top-[48%]
            data-[state=open]:slide-in-from-left-1/2 data-[state=open]:slide-in-from-top-[48%]
            duration-200
            focus:outline-none
          `}
          onPointerDownOutside={(e) => {
            if (!closeOnOverlayClick) {
              e.preventDefault();
            }
          }}
          onEscapeKeyDown={(e) => {
            if (!closeOnOverlayClick) {
              e.preventDefault();
            }
          }}
        >
          {/* Header */}
          {(title || description || showCloseButton) && (
            <div className="flex items-start justify-between gap-4 px-6 py-4 border-b border-border-primary">
              <div className="flex-1 min-w-0">
                {title && (
                  <DialogPrimitive.Title className="text-lg font-semibold text-text-primary">
                    {title}
                  </DialogPrimitive.Title>
                )}
                {description && (
                  <DialogPrimitive.Description className="text-sm text-text-secondary mt-1">
                    {description}
                  </DialogPrimitive.Description>
                )}
              </div>

              {showCloseButton && (
                <DialogPrimitive.Close asChild>
                  <IconButton
                    icon={<X className="h-4 w-4" />}
                    aria-label="Close modal"
                    size="sm"
                    variant="ghost"
                  />
                </DialogPrimitive.Close>
              )}
            </div>
          )}

          {/* Body */}
          <div className="px-6 py-4 max-h-[calc(100vh-16rem)] overflow-y-auto">
            {children}
          </div>

          {/* Footer */}
          {footer && (
            <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-border-primary">
              {footer}
            </div>
          )}
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}

// ============================================================================
// Confirm Modal Component
// ============================================================================

export function ConfirmModal({
  open,
  onOpenChange,
  title,
  description,
  confirmText = "Confirm",
  cancelText = "Cancel",
  confirmVariant = "primary",
  loading = false,
  onConfirm,
}: ConfirmModalProps) {
  const handleConfirm = () => {
    onConfirm();
  };

  return (
    <Modal
      open={open}
      onOpenChange={onOpenChange}
      title={title}
      description={description}
      size="sm"
      footer={
        <>
          <DialogPrimitive.Close asChild>
            <Button variant="secondary" disabled={loading}>
              {cancelText}
            </Button>
          </DialogPrimitive.Close>
          <Button
            variant={confirmVariant}
            onClick={handleConfirm}
            loading={loading}
          >
            {confirmText}
          </Button>
        </>
      }
    >
      {/* Description is in the header */}
      <span className="sr-only">{description}</span>
    </Modal>
  );
}

// ============================================================================
// Modal Trigger (for controlled usage)
// ============================================================================

export const ModalTrigger = DialogPrimitive.Trigger;
export const ModalClose = DialogPrimitive.Close;

export default Modal;
