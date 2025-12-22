/**
 * SigmaVault NAS OS - Input Component
 * @module components/ui/Input
 * 
 * Accessible form input component with validation states.
 */

import * as React from 'react';
import { AlertCircle, Check, Eye, EyeOff } from 'lucide-react';

// ============================================================================
// Types
// ============================================================================

export interface InputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'size'> {
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Validation state */
  state?: 'default' | 'error' | 'success';
  /** Error message to display */
  error?: string;
  /** Left icon or element */
  leftElement?: React.ReactNode;
  /** Right icon or element */
  rightElement?: React.ReactNode;
  /** Full width */
  fullWidth?: boolean;
}

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  /** Validation state */
  state?: 'default' | 'error' | 'success';
  /** Error message to display */
  error?: string;
  /** Auto-resize based on content */
  autoResize?: boolean;
}

export interface PasswordInputProps extends Omit<InputProps, 'type' | 'rightElement'> {
  /** Show password toggle button */
  showToggle?: boolean;
}

// ============================================================================
// Styles
// ============================================================================

const inputBaseStyles = `
  w-full
  bg-bg-tertiary text-text-primary
  border border-border-primary rounded-lg
  transition-all duration-200
  placeholder:text-text-muted
  focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent
  disabled:opacity-50 disabled:cursor-not-allowed
`;

const inputSizeStyles = {
  sm: 'h-8 px-3 text-sm',
  md: 'h-10 px-4 text-sm',
  lg: 'h-12 px-4 text-base',
};

const inputStateStyles = {
  default: 'focus:ring-primary',
  error: 'border-status-error focus:ring-status-error',
  success: 'border-status-success focus:ring-status-success',
};

// ============================================================================
// Input Component
// ============================================================================

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  (
    {
      className = '',
      size = 'md',
      state = 'default',
      error,
      leftElement,
      rightElement,
      fullWidth = true,
      disabled,
      ...props
    },
    ref
  ) => {
    const actualState = error ? 'error' : state;
    
    const combinedClassName = [
      inputBaseStyles,
      inputSizeStyles[size],
      inputStateStyles[actualState],
      leftElement ? 'pl-10' : '',
      rightElement ? 'pr-10' : '',
      fullWidth ? 'w-full' : 'w-auto',
      className,
    ]
      .join(' ')
      .replace(/\s+/g, ' ')
      .trim();

    return (
      <div className={`relative ${fullWidth ? 'w-full' : 'inline-flex'}`}>
        {leftElement && (
          <div className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted pointer-events-none">
            {leftElement}
          </div>
        )}
        
        <input
          ref={ref}
          className={combinedClassName}
          disabled={disabled}
          aria-invalid={actualState === 'error'}
          aria-describedby={error ? `${props.id}-error` : undefined}
          {...props}
        />
        
        {rightElement && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted">
            {rightElement}
          </div>
        )}
        
        {actualState === 'error' && !rightElement && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2 text-status-error">
            <AlertCircle className="h-4 w-4" />
          </div>
        )}
        
        {actualState === 'success' && !rightElement && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2 text-status-success">
            <Check className="h-4 w-4" />
          </div>
        )}
        
        {error && (
          <p
            id={`${props.id}-error`}
            className="mt-1.5 text-sm text-status-error"
            role="alert"
          >
            {error}
          </p>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';

// ============================================================================
// Textarea Component
// ============================================================================

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  (
    {
      className = '',
      state = 'default',
      error,
      autoResize = false,
      ...props
    },
    ref
  ) => {
    const actualState = error ? 'error' : state;
    const internalRef = React.useRef<HTMLTextAreaElement>(null);
    const combinedRef = useCombinedRefs(ref, internalRef);

    // Auto-resize logic
    React.useEffect(() => {
      if (autoResize && internalRef.current) {
        const textarea = internalRef.current;
        textarea.style.height = 'auto';
        textarea.style.height = `${textarea.scrollHeight}px`;
      }
    }, [autoResize, props.value]);

    const combinedClassName = [
      inputBaseStyles,
      'min-h-[80px] py-2 px-4 resize-y',
      inputStateStyles[actualState],
      autoResize ? 'resize-none overflow-hidden' : '',
      className,
    ]
      .join(' ')
      .replace(/\s+/g, ' ')
      .trim();

    return (
      <div className="relative w-full">
        <textarea
          ref={combinedRef}
          className={combinedClassName}
          aria-invalid={actualState === 'error'}
          aria-describedby={error ? `${props.id}-error` : undefined}
          {...props}
        />
        
        {error && (
          <p
            id={`${props.id}-error`}
            className="mt-1.5 text-sm text-status-error"
            role="alert"
          >
            {error}
          </p>
        )}
      </div>
    );
  }
);

Textarea.displayName = 'Textarea';

// ============================================================================
// Password Input Component
// ============================================================================

export const PasswordInput = React.forwardRef<HTMLInputElement, PasswordInputProps>(
  ({ showToggle = true, ...props }, ref) => {
    const [showPassword, setShowPassword] = React.useState(false);

    const toggleVisibility = () => {
      setShowPassword((prev) => !prev);
    };

    return (
      <Input
        ref={ref}
        type={showPassword ? 'text' : 'password'}
        rightElement={
          showToggle ? (
            <button
              type="button"
              onClick={toggleVisibility}
              className="p-1 hover:text-text-primary transition-colors focus:outline-none focus:ring-2 focus:ring-primary rounded"
              aria-label={showPassword ? 'Hide password' : 'Show password'}
            >
              {showPassword ? (
                <EyeOff className="h-4 w-4" />
              ) : (
                <Eye className="h-4 w-4" />
              )}
            </button>
          ) : undefined
        }
        {...props}
      />
    );
  }
);

PasswordInput.displayName = 'PasswordInput';

// ============================================================================
// Label Component
// ============================================================================

export interface LabelProps extends React.LabelHTMLAttributes<HTMLLabelElement> {
  /** Whether the field is required */
  required?: boolean;
  /** Optional hint text */
  hint?: string;
}

export const Label = React.forwardRef<HTMLLabelElement, LabelProps>(
  ({ className = '', required, hint, children, ...props }, ref) => {
    return (
      <div className="mb-1.5">
        <label
          ref={ref}
          className={`text-sm font-medium text-text-primary ${className}`}
          {...props}
        >
          {children}
          {required && <span className="text-status-error ml-1">*</span>}
        </label>
        {hint && (
          <p className="text-xs text-text-muted mt-0.5">{hint}</p>
        )}
      </div>
    );
  }
);

Label.displayName = 'Label';

// ============================================================================
// Utilities
// ============================================================================

function useCombinedRefs<T>(
  ...refs: (React.Ref<T> | undefined)[]
): React.RefCallback<T> {
  return React.useCallback((element: T) => {
    refs.forEach((ref) => {
      if (typeof ref === 'function') {
        ref(element);
      } else if (ref && typeof ref === 'object') {
        (ref as React.MutableRefObject<T | null>).current = element;
      }
    });
  }, refs);
}

export default Input;
