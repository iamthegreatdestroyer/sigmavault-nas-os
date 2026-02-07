project(
  'sigmavault-settings',
  version: '0.1.0',
  meson_version: '>= 0.62.0',
)

python = import('python')
gnome = import('gnome')

py_installation = python.find_installation('python3')

# ─── GSettings Schema ──────────────────────────────────────────
install_data(
  'data/com.sigmavault.Settings.gschema.xml',
  install_dir: get_option('datadir') / 'glib-2.0' / 'schemas',
)

# ─── Desktop File ───────────────────────────────────────────────
desktop_conf = configuration_data()
desktop_file = configure_file(
  input: 'data/com.sigmavault.Settings.desktop.in',
  output: 'com.sigmavault.Settings.desktop',
  configuration: desktop_conf,
)
install_data(
  desktop_file,
  install_dir: get_option('datadir') / 'applications',
)

# ─── GResource Bundle ──────────────────────────────────────────
sigmavault_resources = gnome.compile_resources(
  'sigmavault-resources',
  'resources/sigmavault.gresource.xml',
  source_dir: 'resources',
  gresource_bundle: true,
  install: true,
  install_dir: py_installation.get_install_dir() / 'sigmavault',
)

# ─── Python Sources ─────────────────────────────────────────────
sigmavault_sources = [
  '__init__.py',
  'main.py',
]

ui_sources = [
  'ui/__init__.py',
  'ui/window.py',
  'ui/pages/__init__.py',
  'ui/pages/dashboard.py',
  'ui/pages/storage.py',
  'ui/pages/compression.py',
  'ui/pages/agents.py',
  'ui/pages/shares.py',
  'ui/pages/network.py',
  'ui/pages/settings.py',
  'ui/widgets/__init__.py',
  'ui/widgets/agent_card.py',
  'ui/widgets/pool_widget.py',
  'ui/widgets/job_row.py',
  'ui/widgets/metric_gauge.py',
  'ui/widgets/status_indicator.py',
]

api_sources = [
  'api/__init__.py',
  'api/client.py',
  'api/websocket.py',
  'api/dbus_service.py',
]

install_data(
  sigmavault_sources + ui_sources + api_sources,
  install_dir: py_installation.get_install_dir() / 'sigmavault',
  preserve_path: true,
)

# ─── Nautilus Extension ─────────────────────────────────────────
install_data(
  'nautilus-sigmavault.py',
  install_dir: get_option('datadir') / 'nautilus-python' / 'extensions',
)

# ─── Launcher Script ───────────────────────────────────────────
install_data(
  'data/sigmavault-settings',
  install_dir: get_option('bindir'),
  install_mode: 'rwxr-xr-x',
)

# ─── Post-install: compile schemas ─────────────────────────────
meson.add_install_script('sh', '-c',
  'glib-compile-schemas "$MESON_INSTALL_DESTDIR_PREFIX"/share/glib-2.0/schemas || true'
)
