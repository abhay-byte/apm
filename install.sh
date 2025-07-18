#!/usr/bin/env bash
# APM (Android Package Manager) Installation Script
# Uses ONLY repositories defined in config.yaml - NO hardcoded defaults

set -euo pipefail

APM_HOME="$HOME/.config/apm"
CACHE_DIR="$HOME/.cache/apm"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_CONFIG_DIR="$SCRIPT_DIR/.config"

echo "🔧 Installing APM (Android Package Manager)..."
echo "📍 Script location: $SCRIPT_DIR"

# 1) Check prerequisites
echo "🔍 Checking prerequisites..."
command -v python3 >/dev/null 2>&1 || { echo "❌ Python 3 is required but not installed"; exit 1; }
command -v adb     >/dev/null 2>&1 || { echo "❌ ADB is required but not installed"; exit 1; }
command -v go      >/dev/null 2>&1 || { echo "❌ Go is required for fdroidcl"; exit 1; }

echo "✓ All prerequisites found"

# 2) Create directory structure
echo "📁 Creating directory structure..."
mkdir -p "$APM_HOME" \
         "$CACHE_DIR"/{apks,logs,repos} \
         "$HOME/.local/bin" \
         "$HOME/.local/share/apm" \
         "$HOME/.local/share/bash-completion/completions" \
         "$HOME/.local/share/applications"

# 3) Install Python dependencies
echo "📦 Installing Python dependencies..."
pip3 install --user pyyaml requests click fdroidserver fdroid-dl --break-system-packages

# 4) Install fdroidcl
echo "📦 Installing fdroidcl..."
go install mvdan.cc/fdroidcl@latest

# 5) Copy configuration files - REQUIRED
echo "📄 Installing configuration files..."

# Main configuration file
CONFIG_SOURCE=""
if [ -f "$REPO_CONFIG_DIR/config.yaml" ]; then
    CONFIG_SOURCE="$REPO_CONFIG_DIR/config.yaml"
    echo "✓ Found config.yaml in .config/ directory"
elif [ -f "$SCRIPT_DIR/config.yaml" ]; then
    CONFIG_SOURCE="$SCRIPT_DIR/config.yaml"
    echo "✓ Found config.yaml in root directory"
else
    echo "❌ config.yaml not found!"
    echo "   Expected locations:"
    echo "   - $REPO_CONFIG_DIR/config.yaml"
    echo "   - $SCRIPT_DIR/config.yaml"
    echo "   Please ensure your config.yaml exists before running installation."
    exit 1
fi

# Fix path inconsistencies in config before copying
echo "🔧 Fixing path inconsistencies in config..."
python3 - << PYCODE
import yaml

# Load config
with open("$CONFIG_SOURCE", 'r') as f:
    config = yaml.safe_load(f)

# Fix paths to use 'apm' instead of 'foss-pm'
if 'paths' in config:
    paths = config['paths']
    for key, value in paths.items():
        if isinstance(value, str) and 'foss-pm' in value:
            paths[key] = value.replace('foss-pm', 'apm')
            print(f"   Fixed {key}: {value} -> {paths[key]}")

# Fix top-level path settings
path_keys = ['cache_dir', 'download_dir', 'log_dir', 'config_dir']
for key in path_keys:
    if key in config and isinstance(config[key], str) and 'foss-pm' in config[key]:
        old_value = config[key]
        config[key] = config[key].replace('foss-pm', 'apm')
        print(f"   Fixed {key}: {old_value} -> {config[key]}")

# Fix logging file names
if 'logging' in config and 'file' in config['logging']:
    if 'foss-pm' in config['logging']['file']:
        old_file = config['logging']['file']
        config['logging']['file'] = config['logging']['file'].replace('foss-pm', 'apm')
        print(f"   Fixed logging file: {old_file} -> {config['logging']['file']}")

# Save corrected config
with open("$APM_HOME/config.yaml", 'w') as f:
    yaml.dump(config, f, default_flow_style=False, indent=2)

print("✓ Configuration installed with corrected paths")
PYCODE

# 6) Copy package mappings (required)
echo "📦 Installing package mappings..."
if [ -f "$REPO_CONFIG_DIR/package_mappings.yaml" ]; then
    cp "$REPO_CONFIG_DIR/package_mappings.yaml" "$APM_HOME/package_mappings.yaml"
    echo "✓ Installed package mappings from .config/"
elif [ -f "$SCRIPT_DIR/package_mappings.yaml" ]; then
    cp "$SCRIPT_DIR/package_mappings.yaml" "$APM_HOME/package_mappings.yaml"
    echo "✓ Installed package mappings from root"
else
    echo "❌ package_mappings.yaml not found!"
    echo "   This file is required for APM to function."
    exit 1
fi

# 7) Copy curation config if present
if [ -f "$REPO_CONFIG_DIR/curation_config.yaml" ]; then
    cp "$REPO_CONFIG_DIR/curation_config.yaml" "$APM_HOME/curation_config.yaml"
    echo "✓ Installed curation_config.yaml from .config/"
elif [ -f "$SCRIPT_DIR/curation_config.yaml" ]; then
    cp "$SCRIPT_DIR/curation_config.yaml" "$APM_HOME/curation_config.yaml"
    echo "✓ Installed curation_config.yaml from root"
fi

# 8) Validate configuration
echo "✅ Validating configuration..."
python3 - << PYCODE
import yaml
import os

config_path = "$APM_HOME/config.yaml"
mappings_path = "$APM_HOME/package_mappings.yaml"

# Validate config.yaml
try:
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Check for repositories
    repos = config.get('repositories', [])
    enabled_repos = [r for r in repos if r.get('enabled', True)]
    
    print(f"✓ Configuration is valid YAML")
    print(f"   📊 Total repositories: {len(repos)}")
    print(f"   ✅ Enabled repositories: {len(enabled_repos)}")
    
    if len(enabled_repos) == 0:
        print("⚠️  Warning: No enabled repositories found")
    
    # Show enabled repos
    for repo in enabled_repos[:5]:  # Show first 5
        print(f"   • {repo.get('name', 'Unknown')}")
    if len(enabled_repos) > 5:
        print(f"   ... and {len(enabled_repos) - 5} more")
        
except Exception as e:
    print(f"❌ Configuration validation failed: {e}")
    exit(1)

# Validate package mappings
try:
    with open(mappings_path, 'r') as f:
        mappings = yaml.safe_load(f)
    
    if isinstance(mappings, dict):
        categories = len(mappings)
        total_packages = sum(len(v) if isinstance(v, dict) else 1 for v in mappings.values())
        print(f"✓ Package mappings are valid YAML")
        print(f"   📂 Categories: {categories}")
        print(f"   📦 Total packages: {total_packages}")
    else:
        print("⚠️  Package mappings format may be incorrect")
        
except Exception as e:
    print(f"❌ Package mappings validation failed: {e}")
    exit(1)
PYCODE

# 9) Configure fdroidcl and add repositories from config
echo "🔗 Configuring fdroidcl..."
fdroidcl config > /dev/null 2>&1 || true

echo "📡 Adding repositories from config.yaml..."
python3 - << PYCODE
import yaml
import subprocess
import sys
import requests
from urllib.parse import urljoin

with open("$APM_HOME/config.yaml", 'r') as f:
    config = yaml.safe_load(f)

repos = config.get('repositories', [])
enabled_repos = [r for r in repos if r.get('enabled', True)]

if not enabled_repos:
    print("❌ No enabled repositories found in config.yaml")
    sys.exit(1)

success_count = 0
total_repos = len(enabled_repos)

for repo in enabled_repos:
    name = repo.get('name', 'Unknown')
    url = repo.get('url', '')
    fp = repo.get('fingerprint', '')
    priority = repo.get('priority', 'N/A')
    
    if not url:
        print(f"⚠️  Skipping '{name}' - no URL specified")
        continue
    
    # Quick connectivity test
    try:
        # For F-Droid and most : just index-v1.jar
        if url.endswith("/repo") or url.endswith("/repo/"):
            index_url = urljoin(url+"/repo", 'index-v1.jar')
        else:
            # For /fdroid/official etc
            index_url = urljoin(url + "/", 'index-v1.jar')
        print(index_url)
        response = requests.head(index_url, timeout=10, allow_redirects=True)
        if response.status_code >= 400:
            raise ValueError(f"HTTP {response.status_code}")
    except Exception as e:
        print(f"⚠️  Skipping '{name}' - unreachable ({e})")
        continue
    
    print(f"→ Adding '{name}' (priority: {priority})")
    print(f"   URL: {url}")
    
    try:
        cmd = ['fdroidcl', 'repo', 'add', url]
        if fp:
            cmd.append(fp)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            check=False
        )
        stderr_lower = result.stderr.lower() if result.stderr else ""
        if result.returncode == 0:
            print(f"   ✓ Successfully added")
            success_count += 1
        elif (
            "already configured" in stderr_lower
            or "already exists" in stderr_lower
            or "repo: a repo with the same name" in stderr_lower
            or "repository already exists" in stderr_lower
        ):
            print(f"   ✓ Already configured")
            success_count += 1
        else:
            print(f"   ⚠️  Failed to add (code {result.returncode})")
            if result.stderr.strip():
                print(f"      Error: {result.stderr.strip()}")
            print(f"      You can add manually: fdroidcl repo add {url}" + (f" {fp}" if fp else ""))
    except subprocess.TimeoutExpired:
        print(f"   ⚠️  Timed out adding repository")
    except Exception as e:
        print(f"   ⚠️  Error: {e}")

print(f"\n📊 Repository addition summary: {success_count}/{total_repos} successful")
PYCODE

# 10) Update repositories
echo "🔄 Updating repository indices..."
if fdroidcl update; then
    echo "✓ Repository update successful"
else
    echo "⚠️  Repository update had issues - some repos may not be available"
fi

# 11) Install apm script
echo "🔧 Installing APM script..."
chmod +x "$SCRIPT_DIR/apm.py"

if [ -w "/usr/local/bin" ] || [ "$(id -u)" -eq 0 ]; then
    ln -sf "$SCRIPT_DIR/apm.py" /usr/local/bin/apm
    echo "✓ Installed global 'apm' command to /usr/local/bin"
else
    ln -sf "$SCRIPT_DIR/apm.py" "$HOME/.local/bin/apm"
    echo "✓ Installed 'apm' to ~/.local/bin"
    
    # Check if ~/.local/bin is in PATH
    if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
        echo "⚠️  Add ~/.local/bin to your PATH:"
        echo "   echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc"
        echo "   source ~/.bashrc"
    fi
fi

# 12) Install bash completion
echo "🔧 Installing bash completion..."
cat > "$HOME/.local/share/bash-completion/completions/apm" << 'EOF'
_apm_complete() {
    local cur prev opts
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    
    opts="install search update devices mappings add-mapping remove-mapping resolve list-categories batch-install repo-status repo-list help"
    
    case $prev in
        install|resolve|remove-mapping)
            local packages=$(apm mappings 2>/dev/null | awk '{print $1}' | grep -v "Package" | head -50)
            COMPREPLY=($(compgen -W "$packages" -- "$cur"))
            return 0
            ;;
        --device)
            local devices=$(apm devices 2>/dev/null | grep -v "Connected devices:" | awk '{print $1}')
            COMPREPLY=($(compgen -W "$devices" -- "$cur"))
            return 0
            ;;
    esac
    
    COMPREPLY=($(compgen -W "$opts" -- "$cur"))
}

complete -F _apm_complete apm
EOF

# 13) Create desktop entry
echo "🔧 Creating desktop entry..."
cat > "$HOME/.local/share/applications/apm.desktop" << 'EOF'
[Desktop Entry]
Name=APM (Android Package Manager)
Comment=Command-line package manager for Android FOSS apps
Exec=apm
Icon=system-software-install
Terminal=true
Type=Application
Categories=System;PackageManager;
EOF

chmod +x "$HOME/.local/share/applications/apm.desktop"

# 14) Create update script
echo "🔧 Creating update script..."
cat > "$HOME/.local/bin/update-apm" << 'EOF'
#!/bin/bash
# APM (Android Package Manager) Update Script

REPO_DIR="$(dirname "$(readlink -f "$(which apm)")")"

if [ -d "$REPO_DIR/.git" ]; then
    echo "Updating APM (Android Package Manager)..."
    cd "$REPO_DIR"
    git pull
    
    # Update configuration files
    if [ -f ".config/package_mappings.yaml" ]; then
        cp .config/package_mappings.yaml ~/.config/apm/
        echo "✓ Updated package mappings"
    fi
    
    if [ -f ".config/config.yaml" ]; then
        cp .config/config.yaml ~/.config/apm/
        echo "✓ Updated configuration"
    fi
    
    echo "✓ APM updated successfully"
else
    echo "Error: APM was not installed from git repository"
    exit 1
fi
EOF

chmod +x "$HOME/.local/bin/update-apm"



echo ""
echo "🎉 APM Installation Complete!"
echo ""
echo "📊 Configuration Summary:"
echo "   📂 Config directory: $APM_HOME"
echo "   📂 Cache directory: $CACHE_DIR"
echo "   📄 Main config: $APM_HOME/config.yaml"
echo "   📦 Package mappings: $APM_HOME/package_mappings.yaml"
echo ""
echo "🚀 Usage Examples:"
echo "   apm repo-status          # Check repository connectivity"
echo "   apm repo-list            # List configured repositories"
echo "   apm update               # Update repos and device packages"
echo "   apm install firefox      # Install applications"
echo "   apm search browser       # Search for packages"
echo "   apm mappings             # List package mappings"
echo ""
echo "📚 Help:"
echo "   apm --help               # Show all commands"
echo "   update-apm               # Update APM itself"
echo ""
echo "✅ Installation successful! Happy package managing! 🤖📱"
