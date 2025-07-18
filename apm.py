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

    def get_installed_packages(self, device_id=None):
        """Get list of installed packages on device"""
        if not self.adb_path:
            return []
        
        cmd = ['shell', 'pm', 'list', 'packages', '-3']  # -3 for third-party apps only
        if device_id:
            cmd = ['-s', device_id] + cmd
        
        output = self.run_adb_command(cmd)
        if not output:
            return []
        
        packages = []
        for line in output.split('\n'):
            if line.startswith('package:'):
                package_name = line.replace('package:', '').strip()
                packages.append(package_name)
        
        return packages

    def get_package_version(self, package_name, device_id=None):
        """Get installed version of a package on device"""
        if not self.adb_path:
            return None
        
        cmd = ['shell', 'dumpsys', 'package', package_name]
        if device_id:
            cmd = ['-s', device_id] + cmd
        
        output = self.run_adb_command(cmd)
        if not output:
            return None
        
        for line in output.split('\n'):
            if 'versionName=' in line:
                version = line.split('versionName=')[1].split()[0]
                return version.strip()
        
        return None

    def get_available_updates(self, device_id=None):
        """Check for available updates for installed packages"""
        installed_packages = self.get_installed_packages(device_id)
        updates_available = []
        
        if not installed_packages:
            return updates_available
        
        click.echo(f"Checking for updates for {len(installed_packages)} installed packages...")
        
        # Use fdroidcl to check for updates
        try:
            for package in installed_packages:
                # Get current version
                current_version = self.get_package_version(package, device_id)
                
                # Check if package is available in repositories
                result = subprocess.run(['fdroidcl', 'show', package], 
                                    capture_output=True, text=True)
                
                if result.returncode == 0:
                    # Parse fdroidcl output to get latest version
                    output = result.stdout
                    latest_version = None
                    
                    for line in output.split('\n'):
                        if 'Version:' in line:
                            latest_version = line.split('Version:')[1].strip()
                            break
                    
                    if latest_version and current_version and latest_version != current_version:
                        updates_available.append({
                            'package': package,
                            'current_version': current_version,
                            'latest_version': latest_version
                        })
        
        except subprocess.CalledProcessError:
            click.echo("Error checking for updates")
        
        return updates_available

    def update_device_packages(self, device_id=None, auto_update=False):
        """Update packages on connected device"""
        try:
            updates = self.get_available_updates(device_id)
        except Exception as e:
            click.echo(f"⚠️  Could not check for updates: {e}")
            # Try to continue with cached repository data
            updates = []
        
        if not updates:
            click.echo("✓ All packages are up to date (or no updates could be determined)")
            return True
        
        click.echo(f"Found {len(updates)} package updates available:")
        for update in updates:
            click.echo(f"  {update['package']}: {update['current_version']} → {update['latest_version']}")
        
        if not auto_update:
            if not click.confirm(f"Update {len(updates)} packages?"):
                return False
        
        # Update packages
        success_count = 0
        for update in updates:
            package = update['package']
            click.echo(f"Updating {package}...")
            
            if device_id:
                os.environ['ANDROID_SERIAL'] = device_id
            
            try:
                subprocess.run(['fdroidcl', 'install', package], check=True)
                click.echo(f"✓ Updated {package}")
                success_count += 1
            except subprocess.CalledProcessError as e:
                click.echo(f"⚠️  Failed to update {package}: {e}")
                # Continue with other packages
        
        click.echo(f"Successfully updated {success_count}/{len(updates)} packages")
        return success_count > 0  # Return True if at least one package was updated

    def test_repository_connectivity(self, repo_url):
        """Test if a repository is reachable"""
        try:
            from urllib.parse import urljoin
            # Test the index file specifically
            index_url = urljoin(repo_url, 'index-v1.jar')
            
            response = requests.head(index_url, timeout=10, allow_redirects=True)
            return response.status_code in [200, 304]  # 304 = Not Modified (cached)
            
        except requests.exceptions.RequestException:
            return False

    def get_enabled_repositories(self):
        """Get list of enabled repositories from config"""
        repositories = self.config.get('repositories', [])
        enabled_repos = [repo for repo in repositories if repo.get('enabled', True)]
        return enabled_repos

    def update_repositories(self):
        """Update repository indices with robust error handling"""
        click.echo("Updating repository indices...")
        
        # Get repositories from config only - no defaults
        repositories = self.get_enabled_repositories()
        
        if not repositories:
            click.echo("❌ No repositories configured or all repositories are disabled")
            click.echo("   Please check your configuration file: ~/.config/apm/config.yaml")
            return False
        
        click.echo(f"Found {len(repositories)} enabled repositories in configuration")
        
        # Test repository connectivity first
        working_repos = []
        failed_repos = []
        
        for repo in repositories:
            repo_name = repo['name']
            repo_url = repo['url']
            
            click.echo(f"Testing {repo_name} connectivity...")
            
            if self.test_repository_connectivity(repo_url):
                click.echo(f"✓ {repo_name} is reachable")
                working_repos.append(repo)
            else:
                click.echo(f"⚠️  {repo_name} is unreachable - skipping")
                failed_repos.append(repo_name)
        
        if not working_repos:
            click.echo("❌ No repositories are currently reachable")
            click.echo("   Will attempt device updates with cached data...")
            self.check_device_updates()
            return False
        
        click.echo(f"Proceeding with {len(working_repos)} working repositories")
        
        # Update fdroidcl repositories
        try:
            result = subprocess.run(['fdroidcl', 'update'], 
                                  capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                click.echo("✓ Repository indices updated successfully")
                repo_success = True
            else:
                # Parse stderr to identify specific repository failures
                stderr_lines = result.stderr.split('\n') if result.stderr else []
                
                click.echo("⚠️  Repository update completed with some errors:")
                for line in stderr_lines:
                    if line.strip():
                        # Filter out known problematic repositories from error display
                        if any(failed_repo.lower().replace(' ', '') in line.lower() 
                               for failed_repo in failed_repos):
                            continue  # Skip showing errors for already identified failed repos
                        click.echo(f"   {line}")
                
                repo_success = len(working_repos) > len(failed_repos)
                    
        except subprocess.TimeoutExpired:
            click.echo("⚠️  Repository update timed out")
            repo_success = False
        except subprocess.CalledProcessError as e:
            click.echo(f"⚠️  Repository update failed: {e}")
            repo_success = False
        except FileNotFoundError:
            click.echo("❌ fdroidcl not found. Please install it first.")
            return False
        
        # Summary of repository status
        if failed_repos:
            click.echo(f"\n⚠️  Unreachable repositories: {', '.join(failed_repos)}")
            click.echo("   These repositories will be skipped")
        
        if working_repos:
            working_names = [repo['name'] for repo in working_repos]
            click.echo(f"✓ Working repositories: {', '.join(working_names)}")
        
        # Continue with device updates regardless of repository status
        if self.config.get('updates', {}).get('continue_on_repo_failure', True):
            click.echo("\nContinuing with device package updates...")
            self.check_device_updates()
        
        return repo_success or len(working_repos) > 0

    def check_device_updates(self):
        """Check for device updates regardless of repository status"""
        devices = self.get_connected_devices()
        
        if not devices:
            click.echo("No Android devices connected")
            return
        
        click.echo(f"Found {len(devices)} connected device(s)")
        
        # Update packages on each device
        for device in devices:
            click.echo(f"\nChecking device: {device}")
            
            # Get device info
            device_info = self.get_device_info(device)
            if device_info:
                click.echo(f"Device: {device_info}")
            
            # Update packages on this device
            try:
                self.update_device_packages(device, auto_update=False)
            except Exception as e:
                click.echo(f"⚠️  Error updating device {device}: {e}")

    def get_device_info(self, device_id):
        """Get basic device information"""
        if not self.adb_path:
            return None
        
        try:
            # Get device model
            model_result = self.run_adb_command(['-s', device_id, 'shell', 'getprop', 'ro.product.model'])
            brand_result = self.run_adb_command(['-s', device_id, 'shell', 'getprop', 'ro.product.brand'])
            
            if model_result and brand_result:
                return f"{brand_result} {model_result}"
            
            return device_id
        except:
            return device_id

    def load_config(self, path):
        """Load configuration from YAML file - NO DEFAULTS"""
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
                        config = yaml.safe_load(f)
                        if config:
                            return config
                except Exception as e:
                    click.echo(f"Error loading config from {config_path}: {e}")
                    continue
        
        # NO DEFAULT CONFIG - fail if no config found
        click.echo("❌ No configuration file found!")
        click.echo("Expected locations:")
        for loc in config_locations:
            click.echo(f"  - {loc}")
        click.echo("Please run the installation script first or create a configuration file.")
        sys.exit(1)
    
    def load_mappings(self):
        """Load package name mappings"""
        mappings_path = os.path.expanduser("~/.config/apm/package_mappings.yaml")
        
        if os.path.exists(mappings_path):
            try:
                with open(mappings_path, 'r') as f:
                    raw_mappings = yaml.safe_load(f)
                
                if not raw_mappings:
                    click.echo("Warning: Package mappings file is empty")
                    return {}
                
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
            click.echo("❌ Package mappings file not found!")
            click.echo(f"Expected location: {mappings_path}")
            click.echo("Please run the installation script first.")
            return {}
    
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
    """Update repository indices and device packages"""
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

# Repository management commands
@cli.command()
@click.pass_context
def repo_status(ctx):
    """Check status of all configured repositories"""
    pm = ctx.obj['pm']
    repositories = pm.config.get('repositories', [])
    
    if not repositories:
        click.echo("No repositories configured")
        return
    
    click.echo("Repository Status Check:")
    click.echo("=" * 60)
    
    for repo in repositories:
        repo_name = repo['name']
        repo_url = repo['url']
        enabled = repo.get('enabled', True)
        priority = repo.get('priority', 'N/A')
        
        status_icon = "🔴 DISABLED" if not enabled else "🟡 CHECKING..."
        click.echo(f"{repo_name:<25} {status_icon} (Priority: {priority})")
        
        if enabled:
            if pm.test_repository_connectivity(repo_url):
                click.echo(f"{repo_name:<25} 🟢 ONLINE")
            else:
                click.echo(f"{repo_name:<25} 🔴 OFFLINE")
        
        click.echo(f"{'  URL:':<25} {repo_url}")
        if 'description' in repo:
            click.echo(f"{'  Description:':<25} {repo['description']}")
        click.echo()

@cli.command()
@click.pass_context
def repo_list(ctx):
    """List all configured repositories"""
    pm = ctx.obj['pm']
    repositories = pm.config.get('repositories', [])
    
    if not repositories:
        click.echo("No repositories configured")
        return
    
    click.echo("Configured Repositories:")
    click.echo("=" * 80)
    
    enabled_count = 0
    for repo in repositories:
        name = repo['name']
        url = repo['url']
        enabled = repo.get('enabled', True)
        priority = repo.get('priority', 'N/A')
        
        status = "✓ ENABLED " if enabled else "✗ DISABLED"
        click.echo(f"{status} {name:<25} (Priority: {priority})")
        click.echo(f"{'  URL:':<30} {url}")
        
        if 'description' in repo:
            click.echo(f"{'  Description:':<30} {repo['description']}")
        
        if enabled:
            enabled_count += 1
        
        click.echo()
    
    click.echo(f"Total: {len(repositories)} repositories ({enabled_count} enabled)")

if __name__ == '__main__':
    cli()
