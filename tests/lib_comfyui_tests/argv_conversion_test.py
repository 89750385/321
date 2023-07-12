import os
import unittest
import importlib.util

# Get the module name and file name from the global directory path
module_name = 'utils'
file_name = 'utils.py'
global_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), file_name))

# Load the module from the file path
spec = importlib.util.spec_from_file_location(module_name, global_dir)
utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(utils)
utils.setup_test_env()

from lib_comfyui import argv_conversion


class DeduplicateArgvTest(unittest.TestCase):
    def setUp(self):
        self.argv = []
        self.expected_argv = []

    def tearDown(self):
        self.argv = []
        self.expected_argv = []

    def assert_deduplicated_equal_expected(self):
        argv_conversion.deduplicate_comfyui_args(self.argv)
        self.assertEqual(self.argv, self.expected_argv)

    def test_port_deduplicated(self):
        self.argv.extend(['--port', '1234', '--port', '5678'])
        self.expected_argv.extend(['--port', '1234'])
        self.assert_deduplicated_equal_expected()

    def test_port_mixed_deduplicated(self):
        self.argv.extend(['--port', '1234', '--port', '5678', '--comfyui-use-split-cross-attention', '--lowvram', '--port', '8765'])
        self.expected_argv.extend(['--port', '1234', '--comfyui-use-split-cross-attention', '--lowvram'])
        self.assert_deduplicated_equal_expected()

    def test_lowvram_deduplicated(self):
        self.argv.extend(['--lowvram', '--lowvram'])
        self.expected_argv.extend(['--lowvram'])
        self.assert_deduplicated_equal_expected()

    def test_lowvram_mixed_deduplicated(self):
        self.argv.extend(['--lowvram', '--port', '1234', '--lowvram', '--comfyui-use-split-cross-attention', '--lowvram'])
        self.expected_argv.extend(['--lowvram', '--port', '1234', '--comfyui-use-split-cross-attention'])
        self.assert_deduplicated_equal_expected()
