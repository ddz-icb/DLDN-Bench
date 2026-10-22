"""
Tests for create_overlap_plots.py: Venn diagram and UpSet plot for up to 6 tools, only an UpSet plot for more tools.

Run from the repository root with:
    python -m unittest discover -s tests
"""
import os
import subprocess
import sys
import tempfile
import unittest

REPO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
MINI_CSV = os.path.join(REPO_DIR, 'tests', 'data', 'PXD043425_mini_benchmark_predictions.csv')


def run_overlap_script(output_dir, tools=None):
    venn = os.path.join(output_dir, 'venn.png')
    cmd = [sys.executable, 'create_overlap_plots.py', MINI_CSV, '--output', venn]
    if tools:
        cmd += ['--tools', *tools]
    subprocess.run(cmd, cwd=REPO_DIR, check=True, capture_output=True)
    return os.path.isfile(venn), os.path.isfile(os.path.join(output_dir, 'venn_upset.png'))


class TestOverlapPlots(unittest.TestCase):

    def test_up_to_six_tools_creates_venn_and_upset(self):
        for tools in (['casanovo', 'novor', 'instanovo'],
                      ['casanovo', 'novor', 'instanovo', 'contranovo', 'pi_helixnovo', 'pepnovoplus']):
            with tempfile.TemporaryDirectory() as output_dir:
                self.assertEqual(run_overlap_script(output_dir, tools), (True, True), f'{len(tools)} tools')

    def test_more_than_six_tools_creates_only_upset(self):
        # the mini dataset contains predictions of 8 tools (incl. InstaNovo+)
        with tempfile.TemporaryDirectory() as output_dir:
            self.assertEqual(run_overlap_script(output_dir), (False, True))


if __name__ == '__main__':
    unittest.main()
