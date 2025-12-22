/**
 * SigmaVault NAS OS - Sidebar Navigation Component
 * @module components/layout/Sidebar
 *
 * Main navigation sidebar with agent status indicators.
 */

import * as React from "react";
import { Link, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  HardDrive,
  Shield,
  Network,
  Bot,
  Settings,
  Activity,
  FolderArchive,
  Lock,
  BarChart3,
  ChevronLeft,
  ChevronRight,
  Cpu,
} from "lucide-react";
import { useAppStore } from "@stores/appStore";
import { Badge, Tooltip, SimpleTooltip } from "@components/ui";

// ============================================================================
// Types
// ============================================================================

interface NavItem {
  id: string;
  label: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string | number;
  badgeVariant?: "default" | "primary" | "success" | "warning" | "error";
}

interface NavGroup {
  id: string;
  title: string;
  items: NavItem[];
}

// ============================================================================
// Navigation Configuration
// ============================================================================

const navigationGroups: NavGroup[] = [
  {
    id: "main",
    title: "Main",
    items: [
      { id: "dashboard", label: "Dashboard", href: "/", icon: LayoutDashboard },
      { id: "storage", label: "Storage", href: "/storage", icon: HardDrive },
      {
        id: "compression",
        label: "Compression",
        href: "/compression",
        icon: FolderArchive,
      },
    ],
  },
  {
    id: "security",
    title: "Security",
    items: [
      { id: "security", label: "Security", href: "/security", icon: Shield },
      {
        id: "encryption",
        label: "Encryption",
        href: "/encryption",
        icon: Lock,
      },
    ],
  },
  {
    id: "network",
    title: "Network",
    items: [
      { id: "network", label: "PhantomMesh", href: "/network", icon: Network },
    ],
  },
  {
    id: "ai",
    title: "AI Agents",
    items: [
      { id: "agents", label: "Agent Swarm", href: "/agents", icon: Bot },
      {
        id: "analytics",
        label: "Analytics",
        href: "/analytics",
        icon: BarChart3,
      },
    ],
  },
  {
    id: "system",
    title: "System",
    items: [
      {
        id: "monitoring",
        label: "Monitoring",
        href: "/monitoring",
        icon: Activity,
      },
      { id: "settings", label: "Settings", href: "/settings", icon: Settings },
    ],
  },
];

// ============================================================================
// Sidebar Component
// ============================================================================

export function Sidebar() {
  const location = useLocation();
  const [collapsed, setCollapsed] = React.useState(false);

  // Get agent summary from store
  const agents = useAppStore((state) => state.agents);
  const activeAgentCount = agents.filter((a) => a.status === "active").length;

  return (
    <aside
      className={`
        flex flex-col h-full
        bg-bg-secondary border-r border-border-primary
        transition-all duration-300 ease-out
        ${collapsed ? "w-16" : "w-64"}
      `}
    >
      {/* Logo */}
      <div className="flex items-center h-16 px-4 border-b border-border-primary">
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-primary/20">
            <Cpu className="w-5 h-5 text-primary" />
          </div>
          {!collapsed && (
            <div className="flex flex-col">
              <span className="text-sm font-bold text-text-primary">
                SigmaVault
              </span>
              <span className="text-xs text-text-muted">NAS OS</span>
            </div>
          )}
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-4 scrollbar-thin">
        {navigationGroups.map((group) => (
          <div key={group.id} className="mb-6">
            {!collapsed && (
              <h3 className="px-4 mb-2 text-xs font-semibold uppercase tracking-wider text-text-muted">
                {group.title}
              </h3>
            )}

            <ul className="space-y-1 px-2">
              {group.items.map((item) => {
                const isActive = location.pathname === item.href;
                const Icon = item.icon;

                const linkContent = (
                  <Link
                    to={item.href}
                    className={`
                      flex items-center gap-3 px-3 py-2 rounded-lg
                      transition-colors duration-150
                      ${
                        isActive
                          ? "bg-primary/10 text-primary"
                          : "text-text-secondary hover:bg-bg-tertiary hover:text-text-primary"
                      }
                      ${collapsed ? "justify-center" : ""}
                    `}
                  >
                    <Icon className="w-5 h-5 shrink-0" />

                    {!collapsed && (
                      <>
                        <span className="flex-1 text-sm font-medium">
                          {item.label}
                        </span>

                        {item.badge !== undefined && (
                          <Badge
                            variant={item.badgeVariant || "default"}
                            size="sm"
                          >
                            {item.badge}
                          </Badge>
                        )}
                      </>
                    )}
                  </Link>
                );

                if (collapsed) {
                  return (
                    <li key={item.id}>
                      <SimpleTooltip content={item.label} side="right">
                        {linkContent}
                      </SimpleTooltip>
                    </li>
                  );
                }

                return <li key={item.id}>{linkContent}</li>;
              })}
            </ul>
          </div>
        ))}
      </nav>

      {/* Agent Status Summary */}
      <div
        className={`
        px-4 py-3 border-t border-border-primary
        ${collapsed ? "flex justify-center" : ""}
      `}
      >
        {collapsed ? (
          <SimpleTooltip
            content={`${activeAgentCount} agents active`}
            side="right"
          >
            <div className="flex items-center justify-center w-8 h-8 rounded-full bg-agent-active/20">
              <Bot className="w-4 h-4 text-agent-active" />
            </div>
          </SimpleTooltip>
        ) : (
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center w-8 h-8 rounded-full bg-agent-active/20">
              <Bot className="w-4 h-4 text-agent-active" />
            </div>
            <div className="flex-1">
              <div className="text-sm font-medium text-text-primary">
                Agent Swarm
              </div>
              <div className="text-xs text-text-muted">
                {activeAgentCount} of 40 active
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Collapse Toggle */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="
          flex items-center justify-center
          h-10 border-t border-border-primary
          text-text-muted hover:text-text-primary hover:bg-bg-tertiary
          transition-colors duration-150
        "
        aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
      >
        {collapsed ? (
          <ChevronRight className="w-5 h-5" />
        ) : (
          <ChevronLeft className="w-5 h-5" />
        )}
      </button>
    </aside>
  );
}

export default Sidebar;
