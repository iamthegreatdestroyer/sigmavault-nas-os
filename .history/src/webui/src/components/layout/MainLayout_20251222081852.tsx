/**
 * SigmaVault NAS OS - Main Layout Component
 * @module components/layout/MainLayout
 * 
 * Root layout wrapper with sidebar and header.
 */

import * as React from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';

// ============================================================================
// Main Layout Component
// ============================================================================

export function MainLayout() {
  return (
    <div className="flex h-screen bg-bg-primary text-text-primary overflow-hidden">
      {/* Sidebar */}
      <Sidebar />

      {/* Main Content Area */}
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        {/* Header */}
        <Header />

        {/* Page Content */}
        <main className="flex-1 overflow-auto">
          <div className="container mx-auto px-6 py-6">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}

// ============================================================================
// Page Header Component
// ============================================================================

export interface PageHeaderProps {
  /** Page title */
  title: string;
  /** Optional description */
  description?: string;
  /** Optional action buttons */
  actions?: React.ReactNode;
  /** Optional breadcrumbs */
  breadcrumbs?: React.ReactNode;
}

export function PageHeader({
  title,
  description,
  actions,
  breadcrumbs,
}: PageHeaderProps) {
  return (
    <div className="mb-6">
      {breadcrumbs && <div className="mb-2">{breadcrumbs}</div>}
      
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">{title}</h1>
          {description && (
            <p className="mt-1 text-sm text-text-secondary">{description}</p>
          )}
        </div>
        
        {actions && <div className="flex items-center gap-3">{actions}</div>}
      </div>
    </div>
  );
}

// ============================================================================
// Page Section Component
// ============================================================================

export interface PageSectionProps {
  /** Section title */
  title?: string;
  /** Optional description */
  description?: string;
  /** Content */
  children: React.ReactNode;
  /** Additional class names */
  className?: string;
}

export function PageSection({
  title,
  description,
  children,
  className = '',
}: PageSectionProps) {
  return (
    <section className={`mb-8 ${className}`}>
      {(title || description) && (
        <div className="mb-4">
          {title && (
            <h2 className="text-lg font-semibold text-text-primary">{title}</h2>
          )}
          {description && (
            <p className="mt-1 text-sm text-text-secondary">{description}</p>
          )}
        </div>
      )}
      
      {children}
    </section>
  );
}

// ============================================================================
// Grid Layouts
// ============================================================================

export interface GridProps {
  children: React.ReactNode;
  columns?: 1 | 2 | 3 | 4;
  gap?: 'sm' | 'md' | 'lg';
  className?: string;
}

const columnStyles = {
  1: 'grid-cols-1',
  2: 'grid-cols-1 md:grid-cols-2',
  3: 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3',
  4: 'grid-cols-1 md:grid-cols-2 lg:grid-cols-4',
};

const gapStyles = {
  sm: 'gap-3',
  md: 'gap-4',
  lg: 'gap-6',
};

export function Grid({
  children,
  columns = 3,
  gap = 'md',
  className = '',
}: GridProps) {
  return (
    <div
      className={`grid ${columnStyles[columns]} ${gapStyles[gap]} ${className}`}
    >
      {children}
    </div>
  );
}

// ============================================================================
// Exports
// ============================================================================

export default MainLayout;
