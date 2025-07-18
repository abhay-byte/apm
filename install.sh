#!/bin/bash
# FOSS Package Manager Installation Script

set -e

echo "Installing FOSS Package Manager..."

# Check prerequisites
command -v python3 >/dev/null 2>&1 || { echo "Python 3 is required but not installed. Aborting." >&2; exit 1; }
command -v adb >/dev/null 2>&1 || { echo "ADB is required but not installed. Aborting." >&2; exit 1; }

# Create directories
mkdir -p ~/.config/foss-pm
mkdir -p ~/.cache/foss-pm/apks
mkdir -p ~/.cache/foss-pm/logs

# Install Python dependencies
pip3 install --user pyyaml requests click fdroidserver fdroid-dl --break-system-packages

# Install Go if not present
if ! command -v go >/dev/null 2>&1; then
    echo "Go is required for fdroidcl. Please install Go and run: go install mvdan.cc/fdroidcl@latest"
    exit 1
fi

# Install fdroidcl
go install mvdan.cc/fdroidcl@latest

# Copy configuration files if they exist, otherwise create defaults
if [ -f "config.yaml" ]; then
    cp config.yaml ~/.config/foss-pm/
else
    echo "Creating default config.yaml..."
    cat > ~/.config/foss-pm/config.yaml << 'EOF'
# FOSS Package Manager Configuration

repositories:
  - name: "F-Droid"
    url: "https://f-droid.org/repo"
    enabled: true
    priority: 1
    
  - name: "IzzyOnDroid"
    url: "https://apt.izzysoft.de/fdroid/repo"
    enabled: true
    priority: 2
    
  - name: "Guardian Project"
    url: "https://guardianproject.info/fdroid/repo"
    enabled: false
    priority: 3

# Package filtering
filters:
  approved_licenses:
    - "GPL-3.0"
    - "Apache-2.0"
    - "MIT"
    - "BSD-3-Clause"
    - "ISC"
    
  approved_categories:
    - "System"
    - "Development"
    - "Internet"
    - "Security"
    - "Graphics"
    - "Multimedia"
    
  blocked_anti_features:
    - "Ads"
    - "Tracking"
    - "NonFreeNet"
    - "NonFreeAdd"

# Installation settings
installation:
  auto_update: true
  batch_size: 10
  timeout: 300
  retry_count: 3
  verify_signatures: true

# Paths
paths:
  cache_dir: "~/.cache/foss-pm"
  download_dir: "~/.cache/foss-pm/apks"
  log_dir: "~/.cache/foss-pm/logs"
  config_dir: "~/.config/foss-pm"

# Logging
logging:
  level: "INFO"
  file: "foss-pm.log"
  max_size: "10MB"
  backup_count: 5
EOF
fi

if [ -f "curation_config.yaml" ]; then
    cp curation_config.yaml ~/.config/foss-pm/
else
    echo "Creating default curation_config.yaml..."
    cat > ~/.config/foss-pm/curation_config.yaml << 'EOF'
# Package Curation Configuration

approved_licenses:
  - "GPL-3.0"
  - "GPL-2.0"
  - "Apache-2.0"
  - "MIT"
  - "BSD-3-Clause"
  - "ISC"
  - "LGPL-3.0"
  - "LGPL-2.1"
  - "MPL-2.0"

approved_categories:
  - "System"
  - "Development"
  - "Internet"
  - "Security"
  - "Graphics"
  - "Multimedia"
  - "Office"
  - "Games"
  - "Science & Education"
  - "Money"
  - "Sports & Health"
  - "Navigation"
  - "Phone & SMS"
  - "Reading"
  - "Time"
  - "Writing"

blocked_anti_features:
  - "Ads"
  - "Tracking"
  - "NonFreeNet"
  - "NonFreeAdd"
  - "NonFreeDep"
  - "UpstreamNonFree"

# Minimum requirements
min_added_timestamp: 1577836800  # 2020-01-01
min_target_sdk: 26
max_age_days: 1095  # 3 years

# Quality filters
quality_filters:
  min_downloads: 100
  min_rating: 3.0
  require_source_code: true
  require_reproducible_builds: false
EOF
fi

# Add this section after creating configuration files
if [ -f "package_mappings.yaml" ]; then
    cp package_mappings.yaml ~/.config/foss-pm/
else
    echo "Creating default package_mappings.yaml..."
    cat > ~/.config/foss-pm/package_mappings.yaml << 'EOF'
# Package Name Mappings
browsers:
  firefox: "org.mozilla.fennec_fdroid"
  firefox-focus: "org.mozilla.focus"
  brave: "com.brave.browser"
  chromium: "org.chromium.chrome"
  tor-browser: "org.torproject.torbrowser_alpha"

development:
  termux: "com.termux"
  git: "com.github.git"
  code-editor: "com.github.android.codeeditor"
  terminal: "jackpal.androidterm"

media:
  vlc: "org.videolan.vlc"
  newpipe: "org.schabi.newpipe"
  kodi: "org.xbmc.kodi"

communication:
  signal: "org.thoughtcrime.securesms"
  telegram: "org.telegram.messenger"
  element: "im.vector.app"
  briar: "org.briarproject.briar.android"

security:
  orbot: "org.torproject.android"
  keepass: "com.kunzisoft.keepass.libre"
  bitwarden: "com.x8bit.bitwarden"
  aegis: "com.beemdevelopment.aegis"

system:
  fdroid: "org.fdroid.fdroid"
  magisk: "com.topjohnwu.magisk"
  adaway: "org.adaway"
  greenify: "com.oasisfeng.greenify"
EOF
fi


# Make main script executable
chmod +x foss-pm.py

# Create symlink for global access
sudo ln -sf "$(pwd)/foss-pm.py" /usr/local/bin/foss-pm

echo "Installation complete!"
echo "Configuration files created in ~/.config/foss-pm/"
echo "Run 'foss-pm update' to get started."
