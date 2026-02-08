"""SigmaVault Desktop UI views.

Full-page views for the ViewStack navigation.
"""

from sigmavault_desktop.views.dashboard_view import DashboardView
from sigmavault_desktop.views.jobs_view import JobsListView
from sigmavault_desktop.views.job_detail_view import JobDetailView
from sigmavault_desktop.views.storage_view import StorageView
from sigmavault_desktop.views.agents_view import AgentsView
from sigmavault_desktop.views.system_settings_view import SystemSettingsView

__all__ = [
    "DashboardView",
    "JobsListView",
    "JobDetailView",
    "StorageView",
    "AgentsView",
    "SystemSettingsView",
]
