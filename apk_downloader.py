import os
import requests
import hashlib
from pathlib import Path
import json

class APKDownloader:
    def __init__(self, cache_dir):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
    def download_apk(self, app_id, version=None, repo_url="https://f-droid.org/repo"):
        """Download APK from F-Droid repository"""
        # Get app metadata
        index_url = f"{repo_url}/index-v1.json"
        
        try:
            response = requests.get(index_url)
            response.raise_for_status()
            index_data = response.json()
            
            if app_id not in index_data.get('apps', {}):
                raise ValueError(f"App {app_id} not found in repository")
            
            app_data = index_data['apps'][app_id]
            packages = index_data.get('packages', {}).get(app_id, [])
            
            # Select version
            if version:
                package = next((p for p in packages if p['versionName'] == version), None)
            else:
                package = max(packages, key=lambda p: p['versionCode'])
            
            if not package:
                raise ValueError(f"Version {version} not found for {app_id}")
            
            # Download APK
            apk_name = package['apkName']
            apk_url = f"{repo_url}/{apk_name}"
            
            local_path = self.cache_dir / apk_name
            
            if local_path.exists():
                # Verify existing file
                if self._verify_apk(local_path, package.get('hash')):
                    return local_path
            
            # Download new file
            response = requests.get(apk_url, stream=True)
            response.raise_for_status()
            
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Verify download
            if not self._verify_apk(local_path, package.get('hash')):
                local_path.unlink()
                raise ValueError("Downloaded APK verification failed")
            
            return local_path
            
        except requests.RequestException as e:
            raise ValueError(f"Failed to download APK: {e}")
    
    def _verify_apk(self, file_path, expected_hash):
        """Verify APK file hash"""
        if not expected_hash:
            return True
        
        sha256_hash = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        
        return sha256_hash.hexdigest() == expected_hash
