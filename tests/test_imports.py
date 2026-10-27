"""Core contracts must remain usable when ML packages are absent."""
import subprocess
import sys
import unittest


class ImportIsolationTests(unittest.TestCase):
    def test_core_without_ml_packages(self):
        code = '''
import importlib.abc, sys
class NoML(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'torch', 'torchvision', 'transformers'}:
            raise ModuleNotFoundError(fullname)
sys.meta_path.insert(0, NoML())
from ocr_module import OCRResult, run_pipeline
from ocr_module.config import OCRModuleConfig
assert OCRResult(text='x', ok=True).ok
assert OCRModuleConfig().model.device == 'cpu'
assert not run_pipeline(b'bad input').ok
assert not any(n in sys.modules for n in ('torch', 'torchvision', 'transformers'))
'''
        result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
