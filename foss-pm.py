#!/usr/bin/env python3
"""
FOSS Package Manager - Command-line package manager for Android FOSS apps
"""

import os
import sys
import json
import subprocess
import click
from pathlib import Path
import yaml
import requests

class FOSSPackageManager:
    def __init__(self, config_path="config.yaml"):
        self.config = self.load_config(config_path)
        self.mappings = self.load_mappings()  # Initialize mappings
        self.repo_cache = {}
        self.adb_path = self.find_adb()
    
    def load_config(self, path):
        """Load configuration from YAML file"""
        # Check different config locations
        config_locations = [
            path,
            os.path.expanduser("~/.config/foss-pm/config.yaml"),
            "./config.yaml"
        ]
        
        for config_path in config_locations:
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r') as f:
                        return yaml.safe_load(f)
                except Exception as e:
                    click.echo(f"Error loading config from {config_path}: {e}")
                    continue
        
        # Create default config if none found
        default_path = os.path.expanduser("~/.config/foss-pm/config.yaml")
        return self.create_default_config(default_path)
    
    def create_default_config(self, path):
        """Create default configuration"""
        default_config = {
            'repositories': [
                {
                    'name': 'F-Droid',
                    'url': 'https://f-droid.org/repo',
                    'enabled': True
                },
                {
                    'name': 'IzzyOnDroid',
                    'url': 'https://apt.izzysoft.de/fdroid/repo',
                    'enabled': True
                }
            ],
            'cache_dir': '~/.cache/foss-pm',
            'download_dir': '~/.cache/foss-pm/apks',
            'auto_update': True,
            'filters': {
                'license_whitelist': ['GPL-3.0', 'Apache-2.0', 'MIT', 'BSD-3-Clause'],
                'categories': ['System', 'Development', 'Internet', 'Security']
            }
        }
        
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False)
        
        return default_config
    
    def load_mappings(self):
        """Load package name mappings"""
        mappings_path = os.path.expanduser("~/.config/foss-pm/package_mappings.yaml")
        
        if os.path.exists(mappings_path):
            try:
                with open(mappings_path, 'r') as f:
                    raw_mappings = yaml.safe_load(f)
                
                # Flatten nested mappings
                flat_mappings = {}
                for category, packages in raw_mappings.items():
                    if isinstance(packages, dict):
                        flat_mappings.update(packages)
                    else:
                        flat_mappings[category] = packages
                
                return flat_mappings
            except Exception as e:
                click.echo(f"Error loading mappings: {e}")
                return {}
        else:
            return self.create_default_mappings(mappings_path)
    
    def create_default_mappings(self, path):
        """Create default package mappings"""
        default_mappings = {
            "browsers": {
                "firefox": "org.mozilla.fennec_fdroid",
                "firefox-focus": "org.mozilla.focus",
                "brave": "com.brave.browser",
                "chromium": "org.chromium.chrome",
                "tor-browser": "org.torproject.torbrowser_alpha"
            },
            "development": {
                "termux": "com.termux",
                "git": "com.github.git",
                "code-editor": "com.github.android.codeeditor",
                "terminal": "jackpal.androidterm"
            },
            "media": {
                "vlc": "org.videolan.vlc",
                "newpipe": "org.schabi.newpipe",
                "kodi": "org.xbmc.kodi"
            },
            "communication": {
                "signal": "org.thoughtcrime.securesms",
                "telegram": "org.telegram.messenger",
                "element": "im.vector.app",
                "briar": "org.briarproject.briar.android"
            },
            "security": {
                "orbot": "org.torproject.android",
                "keepass": "com.kunzisoft.keepass.libre",
                "bitwarden": "com.x8bit.bitwarden",
                "aegis": "com.beemdevelopment.aegis"
            }
        }
        
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            yaml.dump(default_mappings, f, default_flow_style=False)
        
        # Return flattened mappings
        flat_mappings = {}
        for category, packages in default_mappings.items():
            if isinstance(packages, dict):
                flat_mappings.update(packages)
        
        return flat_mappings
    
    def resolve_package_name(self, package_name):
        """Resolve friendly name to actual package ID"""
        # Check if it's already a package ID (contains dots)
        if '.' in package_name:
            return package_name
        
        # Check mappings
        if package_name in self.mappings:
            resolved = self.mappings[package_name]
            click.echo(f"Resolved '{package_name}' -> '{resolved}'")
            return resolved
        
        # Check for partial matches
        matches = [name for name in self.mappings.keys() if package_name.lower() in name.lower()]
        
        if len(matches) == 1:
            resolved = self.mappings[matches[0]]
            click.echo(f"Resolved '{package_name}' -> '{matches[0]}' -> '{resolved}'")
            return resolved
        elif len(matches) > 1:
            click.echo(f"Multiple matches found for '{package_name}':")
            for match in matches:
                click.echo(f"  {match} -> {self.mappings[match]}")
            return None
        
        # If no mapping found, return original name
        click.echo(f"No mapping found for '{package_name}', using as-is")
        return package_name
    
    def find_adb(self):
        """Find ADB executable in PATH"""
        for path in os.environ.get('PATH', '').split(os.pathsep):
            adb_path = os.path.join(path, 'adb')
            if os.path.isfile(adb_path) and os.access(adb_path, os.X_OK):
                return adb_path
        
        # Try common locations
        common_paths = [
            '/usr/bin/adb',
            '/usr/local/bin/adb',
            os.path.expanduser('~/android-sdk/platform-tools/adb')
        ]
        
        for path in common_paths:
            if os.path.isfile(path) and os.access(path, os.X_OK):
                return path
        
        raise FileNotFoundError("ADB not found in PATH")
    
    def run_adb_command(self, command, capture_output=True):
        """Execute ADB command"""
        cmd = [self.adb_path] + command
        try:
            result = subprocess.run(cmd, capture_output=capture_output, text=True, check=True)
            return result.stdout.strip() if capture_output else None
        except subprocess.CalledProcessError as e:
            click.echo(f"ADB command failed: {e}")
            return None
    
    def get_connected_devices(self):
        """Get list of connected Android devices"""
        output = self.run_adb_command(['devices'])
        if not output:
            return []
        
        devices = []
        for line in output.split('\n')[1:]:
            if line.strip() and 'device' in line:
                device_id = line.split('\t')[0]
                devices.append(device_id)
        
        return devices
    
    def update_repositories(self):
        """Update repository indices"""
        click.echo("Updating repository indices...")
        
        # Use fdroidcl to update
        try:
            subprocess.run(['fdroidcl', 'update'], check=True)
            click.echo("Repository indices updated successfully")
        except subprocess.CalledProcessError:
            click.echo("Failed to update repository indices")
    
    def search_packages(self, query=None, category=None):
        """Search for packages in repositories"""
        try:
            cmd = ['fdroidcl', 'search']
            if query:
                cmd.append(query)
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return result.stdout
        except subprocess.CalledProcessError:
            return None
    
    def install_package(self, package_name, device_id=None):
        """Install package with name resolution"""
        package_id = self.resolve_package_name(package_name)
        
        if not package_id:
            click.echo(f"Could not resolve package name: {package_name}")
            return False
        
        if device_id:
            os.environ['ANDROID_SERIAL'] = device_id
        
        try:
            subprocess.run(['fdroidcl', 'install', package_id], check=True)
            click.echo(f"Successfully installed {package_id}")
            return True
        except subprocess.CalledProcessError:
            click.echo(f"Failed to install {package_id}")
            return False
    
    def batch_install(self, package_list_file, device_id=None):
        """Install multiple packages from file"""
        try:
            with open(package_list_file, 'r') as f:
                packages = [line.strip() for line in f if line.strip()]
            
            for package in packages:
                click.echo(f"Installing {package}...")
                self.install_package(package, device_id)
                
        except FileNotFoundError:
            click.echo(f"Package list file not found: {package_list_file}")

# CLI Interface
@click.group()
@click.pass_context
def cli(ctx):
    """FOSS Package Manager - Command-line package manager for Android FOSS apps"""
    ctx.ensure_object(dict)
    ctx.obj['pm'] = FOSSPackageManager()

@cli.command()
@click.pass_context
def update(ctx):
    """Update repository indices"""
    ctx.obj['pm'].update_repositories()

@cli.command()
@click.argument('query', required=False)
@click.option('--category', help='Filter by category')
@click.pass_context
def search(ctx, query, category):
    """Search for packages"""
    result = ctx.obj['pm'].search_packages(query, category)
    if result:
        click.echo(result)

@cli.command()
@click.argument('package_id')
@click.option('--device', help='Target device ID')
@click.pass_context
def install(ctx, package_id, device):
    """Install a package"""
    ctx.obj['pm'].install_package(package_id, device)

@cli.command()
@click.argument('package_list_file')
@click.option('--device', help='Target device ID')
@click.pass_context
def batch_install(ctx, package_list_file, device):
    """Install multiple packages from file"""
    ctx.obj['pm'].batch_install(package_list_file, device)

@cli.command()
@click.pass_context
def devices(ctx):
    """List connected devices"""
    devices = ctx.obj['pm'].get_connected_devices()
    if devices:
        click.echo("Connected devices:")
        for device in devices:
            click.echo(f"  {device}")
    else:
        click.echo("No devices connected")

# NEW MAPPING MANAGEMENT COMMANDS
@cli.command()
@click.pass_context
def mappings(ctx):
    """List all package mappings"""
    mappings = ctx.obj['pm'].mappings
    
    if not mappings:
        click.echo("No package mappings found")
        return
    
    click.echo("Package Mappings:")
    for name, package_id in sorted(mappings.items()):
        click.echo(f"  {name:<20} -> {package_id}")

@cli.command()
@click.argument('friendly_name')
@click.argument('package_id')
@click.pass_context
def add_mapping(ctx, friendly_name, package_id):
    """Add a new package mapping"""
    mappings_path = os.path.expanduser("~/.config/foss-pm/package_mappings.yaml")
    
    # Load existing mappings
    if os.path.exists(mappings_path):
        with open(mappings_path, 'r') as f:
            mappings = yaml.safe_load(f)
    else:
        mappings = {"custom": {}}
    
    # Add new mapping to custom category
    if "custom" not in mappings:
        mappings["custom"] = {}
    
    mappings["custom"][friendly_name] = package_id
    
    # Save updated mappings
    with open(mappings_path, 'w') as f:
        yaml.dump(mappings, f, default_flow_style=False)
    
    # Reload mappings in current instance
    ctx.obj['pm'].mappings = ctx.obj['pm'].load_mappings()
    
    click.echo(f"Added mapping: {friendly_name} -> {package_id}")

@cli.command()
@click.argument('package_name')
@click.pass_context
def resolve(ctx, package_name):
    """Resolve a package name to its actual ID"""
    package_id = ctx.obj['pm'].resolve_package_name(package_name)
    if package_id:
        click.echo(f"Resolved: {package_name} -> {package_id}")
    else:
        click.echo(f"Could not resolve: {package_name}")

@cli.command()
@click.argument('friendly_name')
@click.pass_context
def remove_mapping(ctx, friendly_name):
    """Remove a package mapping"""
    mappings_path = os.path.expanduser("~/.config/foss-pm/package_mappings.yaml")
    
    if not os.path.exists(mappings_path):
        click.echo("No mappings file found")
        return
    
    with open(mappings_path, 'r') as f:
        mappings = yaml.safe_load(f)
    
    # Find and remove the mapping
    removed = False
    for category, packages in mappings.items():
        if isinstance(packages, dict) and friendly_name in packages:
            del packages[friendly_name]
            removed = True
            click.echo(f"Removed mapping: {friendly_name}")
            break
    
    if not removed:
        click.echo(f"Mapping '{friendly_name}' not found")
        return
    
    # Save updated mappings
    with open(mappings_path, 'w') as f:
        yaml.dump(mappings, f, default_flow_style=False)
    
    # Reload mappings in current instance
    ctx.obj['pm'].mappings = ctx.obj['pm'].load_mappings()

@cli.command()
@click.pass_context
def list_categories(ctx):
    """List all available categories"""
    mappings_path = os.path.expanduser("~/.config/foss-pm/package_mappings.yaml")
    
    if not os.path.exists(mappings_path):
        click.echo("No mappings file found")
        return
    
    with open(mappings_path, 'r') as f:
        mappings = yaml.safe_load(f)
    
    click.echo("Available Categories:")
    for category, packages in mappings.items():
        if isinstance(packages, dict):
            click.echo(f"  {category} ({len(packages)} packages)")
        else:
            click.echo(f"  {category}")

if __name__ == '__main__':
    cli()
