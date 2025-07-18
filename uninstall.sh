#!/usr/bin/env bash
# APM (Android Package Manager) Uninstall Script
# Removes APM and optionally cleans up configuration files

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Directories and files
APM_HOME="$HOME/.config/apm"
CACHE_DIR="$HOME/.cache/apm"
LOCAL_BIN="$HOME/.local/bin"
BASH_COMPLETION_DIR="$HOME/.local/share/bash-completion/completions"
APPLICATIONS_DIR="$HOME/.local/share/applications"

echo -e "${BLUE}🗑️  APM (Android Package Manager) Uninstaller${NC}"
echo "=================================================="

# Helper functions
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check what's currently installed
echo "🔍 Checking current APM installation..."

APM_COMMAND_PATH=""
if command -v apm >/dev/null 2>&1; then
    APM_COMMAND_PATH=$(which apm)
    print_info "APM command found at: $APM_COMMAND_PATH"
else
    print_warning "APM command not found in PATH"
fi

if [ -d "$APM_HOME" ]; then
    CONFIG_SIZE=$(du -sh "$APM_HOME" 2>/dev/null | cut -f1 || echo "unknown")
    print_info "Configuration directory: $APM_HOME ($CONFIG_SIZE)"
else
    print_warning "No configuration directory found"
fi

if [ -d "$CACHE_DIR" ]; then
    CACHE_SIZE=$(du -sh "$CACHE_DIR" 2>/dev/null | cut -f1 || echo "unknown")
    print_info "Cache directory: $CACHE_DIR ($CACHE_SIZE)"
else
    print_warning "No cache directory found"
fi

echo ""

# Uninstall options
echo "📋 Uninstall Options:"
echo "1) Quick removal (command + cache only, keep configs)"
echo "2) Complete removal (everything including configs)"
echo "3) Custom removal (choose what to remove)"
echo "4) Cancel"
echo ""

read -p "Choose an option [1-4]: " choice

case $choice in
    1)
        REMOVE_COMMAND=true
        REMOVE_CACHE=true
        REMOVE_CONFIG=false
        REMOVE_EXTRAS=true
        ;;
    2)
        REMOVE_COMMAND=true
        REMOVE_CACHE=true
        REMOVE_CONFIG=true
        REMOVE_EXTRAS=true
        ;;
    3)
        echo ""
        echo "📝 Custom Removal Options:"
        
        read -p "Remove APM command/symlink? [y/N]: " -n 1 -r
        echo
        REMOVE_COMMAND=${REPLY,,} == "y"
        
        read -p "Remove configuration files (~/.config/apm)? [y/N]: " -n 1 -r
        echo
        REMOVE_CONFIG=${REPLY,,} == "y"
        
        read -p "Remove cache files (~/.cache/apm)? [y/N]: " -n 1 -r
        echo
        REMOVE_CACHE=${REPLY,,} == "y"
        
        read -p "Remove bash completion and desktop entry? [y/N]: " -n 1 -r
        echo
        REMOVE_EXTRAS=${REPLY,,} == "y"
        ;;
    4)
        echo "Cancelled."
        exit 0
        ;;
    *)
        print_error "Invalid option"
        exit 1
        ;;
esac

echo ""
echo "🚀 Starting uninstallation..."

# Remove APM command/symlink
if [ "$REMOVE_COMMAND" = true ]; then
    echo ""
    echo "🔧 Removing APM command..."
    
    # Remove from common locations
    for location in "/usr/local/bin/apm" "$LOCAL_BIN/apm"; do
        if [ -f "$location" ] || [ -L "$location" ]; then
            if rm -f "$location" 2>/dev/null; then
                print_success "Removed: $location"
            else
                print_warning "Could not remove: $location (permission denied)"
            fi
        fi
    done
    
    # Remove update script
    if [ -f "$LOCAL_BIN/update-apm" ]; then
        rm -f "$LOCAL_BIN/update-apm"
        print_success "Removed: update-apm script"
    fi
fi

# Remove configuration files
if [ "$REMOVE_CONFIG" = true ]; then
    echo ""
    echo "📁 Removing configuration files..."
    
    if [ -d "$APM_HOME" ]; then
        echo "Contents of $APM_HOME:"
        ls -la "$APM_HOME" 2>/dev/null || true
        echo ""
        read -p "Are you sure you want to delete all configuration files? [y/N]: " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            if rm -rf "$APM_HOME"; then
                print_success "Removed: $APM_HOME"
            else
                print_error "Failed to remove: $APM_HOME"
            fi
        else
            print_info "Skipped: Configuration files kept"
        fi
    else
        print_info "No configuration directory to remove"
    fi
fi

# Remove cache files
if [ "$REMOVE_CACHE" = true ]; then
    echo ""
    echo "🗂️  Removing cache files..."
    
    if [ -d "$CACHE_DIR" ]; then
        if rm -rf "$CACHE_DIR"; then
            print_success "Removed: $CACHE_DIR"
        else
            print_error "Failed to remove: $CACHE_DIR"
        fi
    else
        print_info "No cache directory to remove"
    fi
fi

# Remove extras (bash completion, desktop entry)
if [ "$REMOVE_EXTRAS" = true ]; then
    echo ""
    echo "✨ Removing extras..."
    
    # Bash completion
    if [ -f "$BASH_COMPLETION_DIR/apm" ]; then
        rm -f "$BASH_COMPLETION_DIR/apm"
        print_success "Removed: Bash completion"
    fi
    
    # Desktop entry
    if [ -f "$APPLICATIONS_DIR/apm.desktop" ]; then
        rm -f "$APPLICATIONS_DIR/apm.desktop"
        print_success "Removed: Desktop entry"
    fi
    
    # Remove empty directories if they exist
    rmdir "$HOME/.local/share/apm" 2>/dev/null || true
fi

# Optional: Clean up fdroidcl repositories
echo ""
read -p "🔗 Remove APM-added repositories from fdroidcl? [y/N]: " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if command -v fdroidcl >/dev/null 2>&1; then
        echo "📡 Checking fdroidcl repositories..."
        
        # List of repositories that might have been added by APM
        APM_REPOS=(
            "https://f-droid.org/repo"
            "https://apt.izzysoft.de/fdroid/repo"
            "https://guardianproject.info/fdroid/repo"
            "https://microg.org/fdroid/repo"
            "https://fdroid.bromite.org/fdroid/repo"
            "https://calyxos.gitlab.io/calyx-fdroid-repo/fdroid/repo"
            "https://www.collaboraoffice.com/downloads/fdroid/repo"
            "https://mobileapp.bitwarden.com/fdroid/repo"
            "https://archive.newpipe.net/fdroid/repo"
            "https://fdroid.fedilab.app/repo"
            "https://fdroid.getsession.org/fdroid/repo"
            "https://molly.im/fdroid/repo"
            "https://releases.threema.ch/fdroid/repo"
            "https://seamlessupdate.app/fdroid/repo"
            "https://divestos.org/fdroid/official"
            "https://briarproject.org/fdroid/repo"
            "https://fdroid.funkwhale.audio/fdroid/repo"
        )
        
        echo "⚠️  This will attempt to remove repositories that may have been added by APM."
        echo "⚠️  This may affect other F-Droid tools you use."
        echo ""
        read -p "Continue with repository cleanup? [y/N]: " -n 1 -r
        echo
        
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            for repo in "${APM_REPOS[@]}"; do
                if fdroidcl repo remove "$repo" >/dev/null 2>&1; then
                    print_success "Removed fdroidcl repo: $repo"
                fi
            done
        else
            print_info "Skipped: fdroidcl repository cleanup"
        fi
    else
        print_info "fdroidcl not found, skipping repository cleanup"
    fi
else
    print_info "Skipped: fdroidcl repository cleanup"
fi

# Optional: Remove dependencies
echo ""
read -p "🗑️  Remove APM-installed dependencies (fdroidcl, Python packages)? [y/N]: " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "⚠️  WARNING: This may affect other programs that use these dependencies!"
    read -p "Are you sure? [y/N]: " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Remove fdroidcl
        if command -v fdroidcl >/dev/null 2>&1; then
            FDROIDCL_PATH=$(which fdroidcl)
            if [[ $FDROIDCL_PATH == *"go/bin"* ]]; then
                rm -f "$FDROIDCL_PATH" 2>/dev/null || true
                print_success "Removed: fdroidcl"
            else
                print_warning "fdroidcl not in Go path, skipped removal"
            fi
        fi
        
        # Remove Python packages (be careful here)
        echo "📦 Python packages that could be removed:"
        echo "   - pyyaml, requests, click, fdroidserver, fdroid-dl"
        echo "⚠️  These packages may be used by other programs!"
        read -p "Remove Python packages? [y/N]: " -n 1 -r
        echo
        
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            pip3 uninstall -y pyyaml requests click fdroidserver fdroid-dl 2>/dev/null || true
            print_success "Attempted to remove Python packages"
        fi
    fi
else
    print_info "Skipped: Dependency removal"
fi

# Cleanup summary
echo ""
echo "🎉 Uninstallation Summary:"
echo "=========================="

if [ "$REMOVE_COMMAND" = true ]; then
    print_success "APM command removed"
fi

if [ "$REMOVE_CONFIG" = true ]; then
    print_success "Configuration files removed"
else
    print_info "Configuration files preserved at: $APM_HOME"
fi

if [ "$REMOVE_CACHE" = true ]; then
    print_success "Cache files removed"
fi

if [ "$REMOVE_EXTRAS" = true ]; then
    print_success "Bash completion and desktop entry removed"
fi

echo ""
echo "✅ APM uninstallation completed!"

# Final checks
if command -v apm >/dev/null 2>&1; then
    print_warning "APM command still found in PATH. You may need to restart your shell or check your PATH."
else
    print_success "APM command successfully removed from PATH"
fi

if [ -d "$APM_HOME" ]; then
    print_info "Configuration files still exist at: $APM_HOME"
fi

echo ""
echo "🔄 You may want to restart your shell or run: source ~/.bashrc"
echo ""
echo "Thank you for using APM! 🤖📱"
