#!/usr/bin/env python3
"""
Automated package curation for FOSS Package Manager
"""

import json
import yaml
import requests
from pathlib import Path

class PackageCurator:
    def __init__(self, config_path="curation_config.yaml"):
        self.config = self.load_config(config_path)
        self.approved_packages = set()
        self.rejected_packages = set()
        
    def load_config(self, path):
        """Load curation configuration"""
        with open(path, 'r') as f:
            return yaml.safe_load(f)
    
    def evaluate_package(self, package_data):
        """Evaluate if package meets FOSS criteria"""
        # Check license
        license_name = package_data.get('license', '').lower()
        approved_licenses = [l.lower() for l in self.config['approved_licenses']]
        
        if not any(license_name.startswith(al) for al in approved_licenses):
            return False, f"License {license_name} not approved"
        
        # Check categories
        categories = package_data.get('categories', [])
        if not any(cat in self.config['approved_categories'] for cat in categories):
            return False, f"Categories {categories} not approved"
        
        # Check for anti-features
        anti_features = package_data.get('antiFeatures', [])
        blocked_features = self.config.get('blocked_anti_features', [])
        
        if any(af in blocked_features for af in anti_features):
            return False, f"Contains blocked anti-features: {anti_features}"
        
        # Check minimum requirements
        if package_data.get('added', 0) < self.config.get('min_added_timestamp', 0):
            return False, "Package too old"
        
        return True, "Package approved"
    
    def curate_repository(self, repo_url):
        """Curate packages from repository"""
        index_url = f"{repo_url}/index-v1.json"
        
        try:
            response = requests.get(index_url)
            response.raise_for_status()
            index_data = response.json()
            
            apps = index_data.get('apps', {})
            curated_apps = {}
            
            for app_id, app_data in apps.items():
                approved, reason = self.evaluate_package(app_data)
                
                if approved:
                    curated_apps[app_id] = app_data
                    self.approved_packages.add(app_id)
                    print(f"✓ {app_id}: {reason}")
                else:
                    self.rejected_packages.add(app_id)
                    print(f"✗ {app_id}: {reason}")
            
            return curated_apps
            
        except requests.RequestException as e:
            print(f"Failed to fetch repository index: {e}")
            return {}
    
    def generate_curated_list(self, output_file="curated_packages.json"):
        """Generate curated package list"""
        curated_data = {
            'approved_packages': list(self.approved_packages),
            'rejected_packages': list(self.rejected_packages),
            'curation_timestamp': int(time.time())
        }
        
        with open(output_file, 'w') as f:
            json.dump(curated_data, f, indent=2)
        
        print(f"Curated {len(self.approved_packages)} packages")
        print(f"Rejected {len(self.rejected_packages)} packages")

if __name__ == '__main__':
    curator = PackageCurator()
    
    # Curate main F-Droid repository
    curator.curate_repository("https://f-droid.org/repo")
    
    # Generate output
    curator.generate_curated_list()
