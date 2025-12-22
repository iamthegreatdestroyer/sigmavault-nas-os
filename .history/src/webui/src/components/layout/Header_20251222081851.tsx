/**
 * SigmaVault NAS OS - Header Component
 * @module components/layout/Header
 * 
 * Top header with connection status, search, and user actions.
 */

import * as React from 'react';
import {
  Bell,
  Search,
  Wifi,
  WifiOff,
  Moon,
  Sun,
  User,
  LogOut,
  Settings,
  ChevronDown,
  X,
  Check,
  AlertTriangle,
  Info,
} from 'lucide-react';
import * as DropdownMenu from '@radix-ui/react-dropdown-menu';
import { useAppStore, type NotificationType } from '@stores/appStore';
import { Button, IconButton, Badge, SimpleTooltip } from '@components/ui';

// ============================================================================
// Connection Status Component
// ============================================================================

function ConnectionStatus() {
  const { isConnected, isReconnecting } = useAppStore((state) => ({
    isConnected: state.isConnected,
    isReconnecting: state.isReconnecting,
  }));

  if (isReconnecting) {
    return (
      <SimpleTooltip content="Reconnecting to server...">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-status-warning/20">
          <WifiOff className="w-4 h-4 text-status-warning animate-pulse" />
          <span className="text-xs font-medium text-status-warning">
            Reconnecting
          </span>
        </div>
      </SimpleTooltip>
    );
  }

  if (!isConnected) {
    return (
      <SimpleTooltip content="Disconnected from server">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-status-error/20">
          <WifiOff className="w-4 h-4 text-status-error" />
          <span className="text-xs font-medium text-status-error">
            Offline
          </span>
        </div>
      </SimpleTooltip>
    );
  }

  return (
    <SimpleTooltip content="Connected to server">
      <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-status-success/20">
        <Wifi className="w-4 h-4 text-status-success" />
        <span className="text-xs font-medium text-status-success">
          Connected
        </span>
      </div>
    </SimpleTooltip>
  );
}

// ============================================================================
// Search Bar Component
// ============================================================================

function SearchBar() {
  const [query, setQuery] = React.useState('');
  const [isOpen, setIsOpen] = React.useState(false);
  const inputRef = React.useRef<HTMLInputElement>(null);

  // Keyboard shortcut: Cmd/Ctrl + K
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsOpen(true);
        inputRef.current?.focus();
      }
      if (e.key === 'Escape') {
        setIsOpen(false);
        setQuery('');
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <div className="relative">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => setIsOpen(true)}
          placeholder="Search..."
          className="
            w-64 h-9 pl-9 pr-12
            bg-bg-tertiary border border-border-primary rounded-lg
            text-sm text-text-primary placeholder:text-text-muted
            focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary
            transition-all duration-150
          "
        />
        <kbd className="
          absolute right-3 top-1/2 -translate-y-1/2
          px-1.5 py-0.5
          text-xs font-medium text-text-muted
          bg-bg-secondary border border-border-primary rounded
        ">
          ⌘K
        </kbd>
      </div>

      {/* Search results dropdown would go here */}
      {isOpen && query.length > 0 && (
        <div className="
          absolute top-full left-0 right-0 mt-2 z-50
          bg-bg-secondary border border-border-primary rounded-lg shadow-xl
          p-2
        ">
          <p className="text-sm text-text-muted text-center py-4">
            Search coming soon...
          </p>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Notifications Dropdown
// ============================================================================

function NotificationsDropdown() {
  const { notifications, dismissNotification, clearNotifications } = useAppStore(
    (state) => ({
      notifications: state.notifications,
      dismissNotification: state.dismissNotification,
      clearNotifications: state.clearNotifications,
    })
  );

  const unreadCount = notifications.filter((n) => !n.read).length;

  const getIcon = (type: NotificationType) => {
    switch (type) {
      case 'success':
        return <Check className="w-4 h-4 text-status-success" />;
      case 'error':
        return <X className="w-4 h-4 text-status-error" />;
      case 'warning':
        return <AlertTriangle className="w-4 h-4 text-status-warning" />;
      default:
        return <Info className="w-4 h-4 text-status-info" />;
    }
  };

  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <button className="relative p-2 rounded-lg text-text-secondary hover:text-text-primary hover:bg-bg-tertiary transition-colors">
          <Bell className="w-5 h-5" />
          {unreadCount > 0 && (
            <span className="
              absolute -top-1 -right-1
              flex items-center justify-center
              min-w-[18px] h-[18px] px-1
              text-xs font-bold text-white
              bg-status-error rounded-full
            ">
              {unreadCount > 9 ? '9+' : unreadCount}
            </span>
          )}
        </button>
      </DropdownMenu.Trigger>

      <DropdownMenu.Portal>
        <DropdownMenu.Content
          align="end"
          sideOffset={8}
          className="
            z-50 w-80
            bg-bg-secondary border border-border-primary rounded-xl shadow-xl
            animate-in fade-in-0 zoom-in-95
          "
        >
          <div className="flex items-center justify-between px-4 py-3 border-b border-border-primary">
            <h3 className="text-sm font-semibold text-text-primary">
              Notifications
            </h3>
            {notifications.length > 0 && (
              <button
                onClick={clearNotifications}
                className="text-xs text-primary hover:text-primary-hover transition-colors"
              >
                Clear all
              </button>
            )}
          </div>

          <div className="max-h-80 overflow-y-auto">
            {notifications.length === 0 ? (
              <div className="px-4 py-8 text-center">
                <Bell className="w-8 h-8 mx-auto mb-2 text-text-muted" />
                <p className="text-sm text-text-muted">No notifications</p>
              </div>
            ) : (
              notifications.map((notification) => (
                <div
                  key={notification.id}
                  className={`
                    flex items-start gap-3 px-4 py-3
                    border-b border-border-primary last:border-0
                    ${notification.read ? 'opacity-60' : ''}
                  `}
                >
                  <div className="shrink-0 mt-0.5">
                    {getIcon(notification.type)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-text-primary truncate">
                      {notification.title}
                    </p>
                    <p className="text-xs text-text-muted mt-0.5 line-clamp-2">
                      {notification.message}
                    </p>
                    <p className="text-xs text-text-muted mt-1">
                      {new Date(notification.timestamp).toLocaleTimeString()}
                    </p>
                  </div>
                  <button
                    onClick={() => dismissNotification(notification.id)}
                    className="shrink-0 p-1 text-text-muted hover:text-text-primary transition-colors"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              ))
            )}
          </div>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}

// ============================================================================
// User Menu Dropdown
// ============================================================================

function UserMenu() {
  const { theme, setTheme } = useAppStore((state) => ({
    theme: state.theme,
    setTheme: state.setTheme,
  }));

  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <button className="
          flex items-center gap-2 px-3 py-1.5
          rounded-lg
          text-text-secondary hover:text-text-primary hover:bg-bg-tertiary
          transition-colors
        ">
          <div className="flex items-center justify-center w-8 h-8 rounded-full bg-primary/20">
            <User className="w-4 h-4 text-primary" />
          </div>
          <span className="text-sm font-medium text-text-primary">Admin</span>
          <ChevronDown className="w-4 h-4 text-text-muted" />
        </button>
      </DropdownMenu.Trigger>

      <DropdownMenu.Portal>
        <DropdownMenu.Content
          align="end"
          sideOffset={8}
          className="
            z-50 w-56
            bg-bg-secondary border border-border-primary rounded-xl shadow-xl
            p-1
            animate-in fade-in-0 zoom-in-95
          "
        >
          <DropdownMenu.Item
            className="
              flex items-center gap-3 px-3 py-2 rounded-lg
              text-text-secondary hover:text-text-primary hover:bg-bg-tertiary
              cursor-pointer outline-none
            "
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          >
            {theme === 'dark' ? (
              <>
                <Sun className="w-4 h-4" />
                <span className="text-sm">Light Mode</span>
              </>
            ) : (
              <>
                <Moon className="w-4 h-4" />
                <span className="text-sm">Dark Mode</span>
              </>
            )}
          </DropdownMenu.Item>

          <DropdownMenu.Item className="
            flex items-center gap-3 px-3 py-2 rounded-lg
            text-text-secondary hover:text-text-primary hover:bg-bg-tertiary
            cursor-pointer outline-none
          ">
            <Settings className="w-4 h-4" />
            <span className="text-sm">Settings</span>
          </DropdownMenu.Item>

          <DropdownMenu.Separator className="h-px bg-border-primary my-1" />

          <DropdownMenu.Item className="
            flex items-center gap-3 px-3 py-2 rounded-lg
            text-status-error hover:bg-status-error/10
            cursor-pointer outline-none
          ">
            <LogOut className="w-4 h-4" />
            <span className="text-sm">Sign Out</span>
          </DropdownMenu.Item>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}

// ============================================================================
// Header Component
// ============================================================================

export function Header() {
  return (
    <header className="
      flex items-center justify-between
      h-16 px-6
      bg-bg-secondary border-b border-border-primary
    ">
      {/* Left side - Search */}
      <div className="flex items-center gap-4">
        <SearchBar />
      </div>

      {/* Right side - Status & Actions */}
      <div className="flex items-center gap-4">
        <ConnectionStatus />
        <NotificationsDropdown />
        <UserMenu />
      </div>
    </header>
  );
}

export default Header;
