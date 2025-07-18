#!/usr/bin/env python3
"""
APM (Android Package Manager) - Command-line package manager for Android FOSS apps
"""

import os
import sys
import json
import subprocess
import click
from pathlib import Path
import yaml
import requests

class AndroidPackageManager:
    def __init__(self, config_path="config.yaml"):
        self.config = self.load_config(config_path)
        self.mappings = self.load_mappings()
        self.repo_cache = {}
        self.adb_path = self.find_adb()
    
    def load_config(self, path):
        """Load configuration from YAML file"""
        # Check different config locations
        config_locations = [
            path,
            os.path.expanduser("~/.config/apm/config.yaml"),
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
        default_path = os.path.expanduser("~/.config/apm/config.yaml")
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
            'cache_dir': '~/.cache/apm',
            'download_dir': '~/.cache/apm/apks',
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
        mappings_path = os.path.expanduser("~/.config/apm/package_mappings.yaml")
        
        if os.path.exists(mappings_path):
            try:
                with open(mappings_path, 'r') as f:
                    raw_mappings = yaml.safe_load(f)
                
                if not raw_mappings:
                    click.echo("Warning: Package mappings file is empty")
                    return self.create_default_mappings(mappings_path)
                
                # Flatten nested mappings
                flat_mappings = {}
                for category, packages in raw_mappings.items():
                    if isinstance(packages, dict):
                        for pkg_name, pkg_info in packages.items():
                            if isinstance(pkg_name, str):  # Only process string keys
                                flat_mappings[pkg_name] = pkg_info
                    elif isinstance(category, str):
                        flat_mappings[category] = packages
                
                return flat_mappings
                
            except yaml.YAMLError as e:
                click.echo(f"Error parsing YAML in mappings file: {e}")
                return {}
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
                "tor-browser": "org.torproject.torbrowser_alpha",
                "privacy-browser": "com.stoutner.privacybrowser.standard"
            },
            "communication": {
                "signal": "org.thoughtcrime.securesms",
                "telegram": "org.telegram.messenger",
                "element": "im.vector.app",
                "briar": "org.briarproject.briar.android"
            },
            "media": {
                "vlc": "org.videolan.vlc",
                "newpipe": "org.schabi.newpipe",
                "antennapod": "de.danoeh.antennapod"
            },
            "development": {
                "termux": "com.termux",
                "markor": "net.gsantner.markor",
                "octodroid": "com.gh4a"
            },
            "security": {
                "orbot": "org.torproject.android",
                "keepass": "com.kunzisoft.keepass.libre",
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
        
        # Handle case where mappings might be None or empty
        if not self.mappings:
            click.echo(f"No package mappings available")
            return package_name
        
        # Check direct mappings first
        if package_name in self.mappings:
            resolved = self.mappings[package_name]
            # Handle case where mapping value is a dict with metadata
            if isinstance(resolved, dict):
                package_id = resolved.get('package_id', resolved.get('id', ''))
                if package_id:
                    click.echo(f"Resolved '{package_name}' -> '{package_id}'")
                    return package_id
            else:
                click.echo(f"Resolved '{package_name}' -> '{resolved}'")
                return resolved
        
        # Check for partial matches - only check string keys
        matches = []
        for name in self.mappings.keys():
            if isinstance(name, str) and isinstance(package_name, str):
                if package_name.lower() in name.lower():
                    matches.append(name)
        
        if len(matches) == 1:
            resolved_name = matches[0]
            resolved_value = self.mappings[resolved_name]
            
            # Handle dict values
            if isinstance(resolved_value, dict):
                package_id = resolved_value.get('package_id', resolved_value.get('id', ''))
                if package_id:
                    click.echo(f"Resolved '{package_name}' -> '{resolved_name}' -> '{package_id}'")
                    return package_id
            else:
                click.echo(f"Resolved '{package_name}' -> '{resolved_name}' -> '{resolved_value}'")
                return resolved_value
                
        elif len(matches) > 1:
            click.echo(f"Multiple matches found for '{package_name}':")
            for match in matches[:5]:  # Show first 5 matches
                value = self.mappings[match]
                if isinstance(value, dict):
                    package_id = value.get('package_id', value.get('id', str(value)))
                    click.echo(f"  {match} -> {package_id}")
                else:
                    click.echo(f"  {match} -> {value}")
            if len(matches) > 5:
                click.echo(f"  ... and {len(matches) - 5} more matches")
            return None
        
        # If no mapping found, return original name
        click.echo(f"No mapping found for '{package_name}', using as-is")
        return package_name
    
    def find_adb(self):
        """Find ADB executable in PATH"""
        # Check if adb is in PATH
        for path in os.environ.get('PATH', '').split(os.pathsep):
            adb_path = os.path.join(path, 'adb')
            if os.path.isfile(adb_path) and os.access(adb_path, os.X_OK):
                return adb_path
        
        # Try common locations
        common_paths = [
            '/usr/bin/adb',
            '/usr/local/bin/adb',
            os.path.expanduser('~/android-sdk/platform-tools/adb'),
            os.path.expanduser('~/Android/Sdk/platform-tools/adb'),
            '/opt/android-sdk/platform-tools/adb'
        ]
        
        for path in common_paths:
            if os.path.isfile(path) and os.access(path, os.X_OK):
                return path
        
        # If not found, warn user but don't fail
        click.echo("Warning: ADB not found in PATH. Install Android SDK platform-tools.")
        return None
    
    def run_adb_command(self, command, capture_output=True):
        """Execute ADB command"""
        if not self.adb_path:
            click.echo("ADB not available. Cannot execute command.")
            return None
            
        cmd = [self.adb_path] + command
        try:
            result = subprocess.run(cmd, capture_output=capture_output, text=True, check=True)
            return result.stdout.strip() if capture_output else None
        except subprocess.CalledProcessError as e:
            click.echo(f"ADB command failed: {e}")
            return None
    
    def get_connected_devices(self):
        """Get list of connected Android devices"""
        if not self.adb_path:
            return []
            
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
        except FileNotFoundError:
            click.echo("fdroidcl not found. Please install it first.")
    
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
        except FileNotFoundError:
            click.echo("fdroidcl not found. Please install it first.")
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
        except FileNotFoundError:
            click.echo("fdroidcl not found. Please install it first.")
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
    """APM (Android Package Manager) - Command-line package manager for Android FOSS apps"""
    ctx.ensure_object(dict)
    ctx.obj['pm'] = AndroidPackageManager()

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
        if isinstance(package_id, dict):
            real_id = package_id.get('package_id', package_id.get('id', str(package_id)))
            click.echo(f"  {name:<25} -> {real_id}")
        else:
            click.echo(f"  {name:<25} -> {package_id}")

@cli.command()
@click.argument('friendly_name')
@click.argument('package_id')
@click.pass_context
def add_mapping(ctx, friendly_name, package_id):
    """Add a new package mapping"""
    mappings_path = os.path.expanduser("~/.config/apm/package_mappings.yaml")
    
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
    mappings_path = os.path.expanduser("~/.config/apm/package_mappings.yaml")
    
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
    mappings_path = os.path.expanduser("~/.config/apm/package_mappings.yaml")
    
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

@cli.command()
@click.argument('package_name', required=False)
@click.pass_context
def debug_mappings(ctx, package_name):
    """Debug package mappings"""
    pm = ctx.obj['pm']
    
    if not pm.mappings:
        click.echo("No mappings loaded")
        return
    
    click.echo(f"Total mappings: {len(pm.mappings)}")
    
    if package_name:
        click.echo(f"\nSearching for '{package_name}':")
        
        # Direct match
        if package_name in pm.mappings:
            value = pm.mappings[package_name]
            click.echo(f"Direct match: {package_name} -> {value}")
        
        # Partial matches
        matches = [name for name in pm.mappings.keys() 
                  if isinstance(name, str) and isinstance(package_name, str) 
                  and package_name.lower() in name.lower()]
        
        if matches:
            click.echo(f"Partial matches ({len(matches)}):")
            for match in matches[:10]:
                value = pm.mappings[match]
                click.echo(f"  {match} -> {value}")
        else:
            click.echo("No matches found")
    else:
        click.echo("\nFirst 10 mappings:")
        for i, (key, value) in enumerate(pm.mappings.items()):
            if i >= 10:
                break
            click.echo(f"  {key} -> {value}")

if __name__ == '__main__':
    cli()
