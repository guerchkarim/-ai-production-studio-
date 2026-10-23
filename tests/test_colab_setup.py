"""Le setup Colab doit démarrer sans variables héritées d'un ancien notebook."""
import ast
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class ColabSetupTests(unittest.TestCase):
    def test_fresh_kernel_defines_both_locks_before_writing(self):
        notebook = json.loads((ROOT/'notebooks/AI_Production_Studio_Colab.ipynb').read_text())
        tree = ast.parse(''.join(notebook['cells'][1]['source']))
        # Injecter un Path qui redirige seulement /content vers un bac à sable.
        tree.body = [n for n in tree.body if not (isinstance(n, ast.ImportFrom) and n.module=='pathlib')]
        google = ModuleType('google')
        colab = ModuleType('google.colab')
        colab.drive = SimpleNamespace(mount=lambda path: None)
        google.colab = colab
        with tempfile.TemporaryDirectory() as d:
            previous = Path.cwd()
            sandbox = Path(d)
            def safe_path(value):
                text = str(value)
                return sandbox/text.lstrip('/') if text.startswith('/content/') else Path(value)
            os.chdir(sandbox)
            try:
                scope = {'Path':safe_path}
                completed = SimpleNamespace(stdout='preflight simulated', check_returncode=lambda: None)
                with patch.dict(sys.modules, {'google':google, 'google.colab':colab}), patch('subprocess.check_call') as calls, patch('subprocess.run',return_value=completed), patch('importlib.util.find_spec',return_value=object()), redirect_stdout(io.StringIO()):
                    exec(compile(tree,'<fresh Colab setup>','exec'),scope)
                self.assertGreater(calls.call_count,3)
                runtime = sandbox/'.studio-chatterbox-runtime'
                self.assertEqual((runtime/'requirements.txt').read_text().strip(), (ROOT/'scripts/colab/chatterbox-ar.requirements.txt').read_text().strip())
                self.assertEqual((runtime/'qwen-requirements.txt').read_text().strip(), (ROOT/'scripts/colab/qwen-voicedesign.requirements.txt').read_text().strip())
                self.assertIn('setuptools==80.9.0',scope['REQUIREMENTS'])
            finally:
                os.chdir(previous)


if __name__=='__main__':
    unittest.main()
