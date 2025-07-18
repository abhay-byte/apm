import unittest
import tempfile
import shutil
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from foss_pm import FOSSPackageManager

class TestFOSSPackageManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "test_config.yaml"
        self.pm = FOSSPackageManager(str(self.config_path))
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    def test_config_creation(self):
        """Test configuration file creation"""
        self.assertTrue(self.config_path.exists())
        self.assertIn('repositories', self.pm.config)
    
    def test_repository_update(self):
        """Test repository update functionality"""
        # Mock test - in real implementation, use proper mocking
        pass
    
    def test_package_search(self):
        """Test package search functionality"""
        # Mock test - in real implementation, use proper mocking
        pass

if __name__ == '__main__':
    unittest.main()
