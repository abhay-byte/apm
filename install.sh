#!/bin/bash
# Enhanced FOSS Package Manager Installation Script

set -e

echo "Installing FOSS Package Manager with Multiple Repositories..."

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_CONFIG_DIR="$SCRIPT_DIR/.config"

# Check prerequisites
command -v python3 >/dev/null 2>&1 || { echo "Python 3 is required but not installed. Aborting." >&2; exit 1; }
command -v adb >/dev/null 2>&1 || { echo "ADB is required but not installed. Aborting." >&2; exit 1; }

# Create directories
mkdir -p ~/.config/foss-pm
mkdir -p ~/.cache/foss-pm/apks
mkdir -p ~/.cache/foss-pm/logs
mkdir -p ~/.cache/foss-pm/repos
mkdir -p ~/.local/share/foss-pm

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install --user pyyaml requests click fdroidserver fdroid-dl --break-system-packages

# Install Go if not present
if ! command -v go >/dev/null 2>&1; then
    echo "Go is required for fdroidcl. Please install Go and run: go install mvdan.cc/fdroidcl@latest"
    exit 1
fi

# Install fdroidcl
echo "Installing fdroidcl..."
go install mvdan.cc/fdroidcl@latest

# Copy configuration files from repository
echo "Installing configuration files..."

# Main configuration
if [ -f "$REPO_CONFIG_DIR/config.yaml" ]; then
    cp "$REPO_CONFIG_DIR/config.yaml" ~/.config/foss-pm/
    echo "✓ Installed main configuration from repository"
elif [ -f "$SCRIPT_DIR/config.yaml" ]; then
    cp "$SCRIPT_DIR/config.yaml" ~/.config/foss-pm/
    echo "✓ Installed main configuration from root"
else
    echo "Creating default configuration..."
    cat > ~/.config/foss-pm/config.yaml << 'EOF'
# Enhanced FOSS Package Manager Configuration with Multiple Repositories

repositories:
  - name: "F-Droid"
    url: "https://f-droid.org/repo"
    enabled: true
    priority: 1
    description: "Official F-Droid repository"
    fingerprint: "43238D512C1E5EB2D6569F4A3AFBF5523418B82E0A3ED1552770ABB9A9C9CCAB"
    
  - name: "IzzyOnDroid"
    url: "https://apt.izzysoft.de/fdroid/repo"
    enabled: true
    priority: 3
    description: "Third-party F-Droid compatible repository"
    fingerprint: "3BF0D6ABFEAE2F401707B6D966BE743BF0EEE49C2561B9BA39073711F628937A"
    
  - name: "Guardian Project"
    url: "https://guardianproject.info/fdroid/repo"
    enabled: true
    priority: 4
    description: "Privacy and security focused apps"
    fingerprint: "B7C2EEFD8DAC7806AF67DFCD92EB18126BC08312A7F2D6F3862E46013C7A6135"
    
  - name: "microG"
    url: "https://microg.org/fdroid/repo"
    enabled: true
    priority: 6
    description: "microG Project repository"
    fingerprint: "9BD06727E62796C0130EB6DAB39B73157451582CBD138E86C468ACC395D14165"
    
  - name: "NewPipe"
    url: "https://archive.newpipe.net/fdroid/repo"
    enabled: true
    priority: 12
    description: "NewPipe YouTube client"
    fingerprint: "E2402C78F9B97C6C89E97DB914A2751FDA1D02FE2039CC0897A462BDB57E5B26"
    
  - name: "Molly"
    url: "https://molly.im/fdroid/repo"
    enabled: true
    priority: 15
    description: "Molly Signal fork"
    fingerprint: "5198DAEF37FC23C14F5087E207A778E2DE99CA98D1FB651E982F8FDD1A0B6A7C"

# Package filtering for FOSS apps only
filters:
  approved_licenses:
    - "GPL-3.0"
    - "GPL-2.0"
    - "Apache-2.0"
    - "MIT"
    - "BSD-3-Clause"
    - "ISC"
    - "LGPL-3.0"
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
    
  blocked_anti_features:
    - "Ads"
    - "Tracking"
    - "NonFreeNet"
    - "NonFreeAdd"
    - "NonFreeDep"
    - "UpstreamNonFree"

# Installation settings
installation:
  auto_update: true
  batch_size: 10
  timeout: 300
  retry_count: 3
  verify_signatures: true
  prefer_foss: true

# Paths
paths:
  cache_dir: "~/.cache/foss-pm"
  download_dir: "~/.cache/foss-pm/apks"
  log_dir: "~/.cache/foss-pm/logs"
  config_dir: "~/.config/foss-pm"
  repo_cache_dir: "~/.cache/foss-pm/repos"

# Logging
logging:
  level: "INFO"
  file: "foss-pm.log"
  max_size: "10MB"
  backup_count: 5
EOF
    echo "✓ Created default configuration"
fi

# Package mappings - Check .config directory first
if [ -f "$REPO_CONFIG_DIR/package_mappings.yaml" ]; then
    cp "$REPO_CONFIG_DIR/package_mappings.yaml" ~/.config/foss-pm/
    echo "✓ Installed package mappings database from .config/"
    
    # Count packages for user feedback
    MAPPING_COUNT=$(grep -c ":" "$REPO_CONFIG_DIR/package_mappings.yaml" 2>/dev/null || echo "unknown")
    echo "  📦 Loaded $MAPPING_COUNT package mappings"
    
elif [ -f "$SCRIPT_DIR/package_mappings.yaml" ]; then
    cp "$SCRIPT_DIR/package_mappings.yaml" ~/.config/foss-pm/
    echo "✓ Installed package mappings database from root"
else
    echo "Error: package_mappings.yaml not found in repository!" >&2
    echo "Expected location: $REPO_CONFIG_DIR/package_mappings.yaml" >&2
    exit 1
fi

# Curation configuration
if [ -f "$REPO_CONFIG_DIR/curation_config.yaml" ]; then
    cp "$REPO_CONFIG_DIR/curation_config.yaml" ~/.config/foss-pm/
    echo "✓ Installed curation configuration from .config/"
elif [ -f "$SCRIPT_DIR/curation_config.yaml" ]; then
    cp "$SCRIPT_DIR/curation_config.yaml" ~/.config/foss-pm/
    echo "✓ Installed curation configuration from root"
else
    echo "Creating default curation configuration..."
    cat > ~/.config/foss-pm/curation_config.yaml << 'EOF'
# FOSS Package Curation Configuration

approved_licenses:
  - "GPL-3.0"
  - "GPL-2.0"
  - "AGPL-3.0"
  - "Apache-2.0"
  - "MIT"
  - "BSD-2-Clause"
  - "BSD-3-Clause"
  - "ISC"
  - "LGPL-3.0"
  - "LGPL-2.1"
  - "MPL-2.0"
  - "CC0-1.0"
  - "Unlicense"
  - "WTFPL"

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
  - "Connectivity"
  - "Theming"

blocked_anti_features:
  - "Ads"
  - "Tracking"
  - "NonFreeNet"
  - "NonFreeAdd"
  - "NonFreeDep"
  - "UpstreamNonFree"
  - "NonFreeAssets"
  - "KnownVuln"
  - "NoSourceSince"
  - "ApplicationDebuggable"

# Quality requirements
quality_filters:
  min_downloads: 100
  min_rating: 3.0
  require_source_code: true
  require_reproducible_builds: false
  max_age_days: 1095  # 3 years
  min_target_sdk: 26
EOF
    echo "✓ Created default curation configuration"
fi

# Validate package mappings file
if [ -f ~/.config/foss-pm/package_mappings.yaml ]; then
    echo "Validating package mappings..."
    
    # Check if file is valid YAML
    if command -v python3 >/dev/null 2>&1; then
        python3 -c "
import yaml
try:
    with open('$HOME/.config/foss-pm/package_mappings.yaml', 'r') as f:
        data = yaml.safe_load(f)
    print('✓ Package mappings file is valid YAML')
    
    # Count categories and packages
    if isinstance(data, dict):
        categories = len(data)
        total_packages = sum(len(v) if isinstance(v, dict) else 1 for v in data.values())
        print(f'  📂 {categories} categories')
        print(f'  📦 {total_packages} total packages')
        
        # Show some categories
        print('  🏷️  Categories: ' + ', '.join(list(data.keys())[:5]) + ('...' if len(data) > 5 else ''))
except Exception as e:
    print(f'❌ Error validating package mappings: {e}')
    exit(1)
" || echo "Warning: Could not validate package mappings file"
    fi
else
    echo "✓ Package mappings file copied successfully"
fi

# Configure fdroidcl with multiple repositories
echo "Configuring fdroidcl with multiple repositories..."
fdroidcl config > /dev/null 2>&1 || true

# Add repositories from config
echo "Adding F-Droid repositories..."
repositories=(
    "https://f-droid.org/repo"
    "https://apt.izzysoft.de/fdroid/repo"
    "https://guardianproject.info/fdroid/repo"
    "https://microg.org/fdroid/repo"
    "https://archive.newpipe.net/fdroid/repo"
    "https://molly.im/fdroid/repo"
)

for repo in "${repositories[@]}"; do
    fdroidcl add-repo "$repo" 2>/dev/null || echo "Warning: Could not add repository $repo"
done

# Update repository indices
echo "Updating repository indices..."
fdroidcl update 2>/dev/null || echo "Warning: Repository update failed, continuing..."

# Make main script executable
chmod +x "$SCRIPT_DIR/foss-pm.py"

# Create symlink for global access
if [ -w "/usr/local/bin" ] || [ "$EUID" -eq 0 ]; then
    ln -sf "$SCRIPT_DIR/foss-pm.py" /usr/local/bin/foss-pm
    echo "✓ Created global symlink at /usr/local/bin/foss-pm"
else
    echo "Creating user-local symlink..."
    mkdir -p ~/.local/bin
    ln -sf "$SCRIPT_DIR/foss-pm.py" ~/.local/bin/foss-pm
    echo "✓ Created user symlink at ~/.local/bin/foss-pm"
    
    # Check if ~/.local/bin is in PATH
    if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
        echo "⚠️  Add ~/.local/bin to your PATH by adding this to ~/.bashrc:"
        echo "   export PATH=\"\$HOME/.local/bin:\$PATH\""
    fi
fi

# Create bash completion
mkdir -p ~/.local/share/bash-completion/completions
cat > ~/.local/share/bash-completion/completions/foss-pm << 'EOF'
_foss_pm_complete() {
    local cur prev opts
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    
    opts="install search update devices mappings add-mapping remove-mapping resolve list-categories batch-install help"
    
    case $prev in
        install|resolve|remove-mapping)
            # Complete with package names from mappings
            local packages=$(foss-pm mappings 2>/dev/null | awk '{print $1}' | grep -v "Package" | head -50)
            COMPREPLY=($(compgen -W "$packages" -- "$cur"))
            return 0
            ;;
        --device)
            # Complete with device IDs
            local devices=$(foss-pm devices 2>/dev/null | grep -v "Connected devices:" | awk '{print $1}')
            COMPREPLY=($(compgen -W "$devices" -- "$cur"))
            return 0
            ;;
        --source)
            COMPREPLY=($(compgen -W "fdroid auto" -- "$cur"))
            return 0
            ;;
        list-category)
            # Complete with category names
            local categories=$(foss-pm list-categories 2>/dev/null | grep -v "Available Categories:" | awk '{print $1}')
            COMPREPLY=($(compgen -W "$categories" -- "$cur"))
            return 0
            ;;
    esac
    
    COMPREPLY=($(compgen -W "$opts" -- "$cur"))
}

complete -F _foss_pm_complete foss-pm
EOF

# Create desktop entry
mkdir -p ~/.local/share/applications
cat > ~/.local/share/applications/foss-pm.desktop << 'EOF'
[Desktop Entry]
Name=FOSS Package Manager
Comment=Command-line package manager for Android FOSS apps
Exec=foss-pm
Icon=system-software-install
Terminal=true
Type=Application
Categories=System;PackageManager;
Keywords=android;foss;fdroid;package;manager;
EOF

# Set permissions
chmod +x ~/.local/share/applications/foss-pm.desktop

# Create update script for easy maintenance
cat > ~/.local/bin/update-foss-pm << 'EOF'
#!/bin/bash
# FOSS Package Manager Update Script

REPO_DIR="$(dirname "$(readlink -f "$(which foss-pm)")")"

if [ -d "$REPO_DIR/.git" ]; then
    echo "Updating FOSS Package Manager..."
    cd "$REPO_DIR"
    git pull
    
    # Update configuration files
    if [ -f ".config/package_mappings.yaml" ]; then
        cp .config/package_mappings.yaml ~/.config/foss-pm/
        echo "✓ Updated package mappings"
    fi
    
    if [ -f ".config/config.yaml" ]; then
        cp .config/config.yaml ~/.config/foss-pm/
        echo "✓ Updated configuration"
    fi
    
    echo "✓ FOSS Package Manager updated successfully"
else
    echo "Error: FOSS Package Manager was not installed from git repository"
    exit 1
fi
EOF

chmod +x ~/.local/bin/update-foss-pm

echo ""
echo "🎉 Installation complete!"
echo ""
echo "FOSS Package Manager features:"
echo "✓ Multiple F-Droid repositories configured"
echo "✓ Comprehensive FOSS package mappings database"
echo "✓ Bash completion support"
echo "✓ Desktop integration"
echo "✓ Auto-update script included"
echo ""
echo "Configuration files:"
echo "📂 Repository: $SCRIPT_DIR"
echo "📂 User config: ~/.config/foss-pm/"
echo "📂 Package mappings: ~/.config/foss-pm/package_mappings.yaml"
echo ""
echo "Usage examples:"
echo "  foss-pm install firefox signal keepass"
echo "  foss-pm search browser"
echo "  foss-pm mappings | grep -i music"
echo "  foss-pm update"
echo ""
echo "To update FOSS Package Manager in the future:"
echo "  update-foss-pm"
echo ""
echo "Run 'foss-pm help' for more information."

# Test installation
echo ""
echo "Testing installation..."
if command -v foss-pm >/dev/null 2>&1; then
    echo "✓ foss-pm command is available"
    
    # Test basic functionality
    if foss-pm mappings >/dev/null 2>&1; then
        echo "✓ Package mappings loaded successfully"
    else
        echo "⚠️  Warning: Package mappings test failed"
    fi
else
    echo "❌ Error: foss-pm command not found in PATH"
    echo "Try running: source ~/.bashrc"
fi
