import importlib.util
from pathlib import Path
import tempfile
import unittest
spec=importlib.util.spec_from_file_location('combine',Path(__file__).resolve().parents[1]/'scripts/combine_reports.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)

class CombineTests(unittest.TestCase):
    def test_preserves_previous_report_on_missing_input(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);out=root/'all.txt';out.write_text('previous')
            with self.assertRaises(FileNotFoundError):c.combine([root/'missing.txt'],out)
            self.assertEqual(out.read_text(),'previous')
    def test_preserves_previous_report_on_empty_input(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);out=root/'all.txt';out.write_text('previous');empty=root/'empty.txt';empty.write_text('')
            with self.assertRaises(ValueError):c.combine([empty],out)
            self.assertEqual(out.read_text(),'previous')
    def test_combines_without_changing_source_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=root/'one.txt';source.write_text('original query timestamp and alias')
            out=root/'all.txt';c.combine([source],out)
            self.assertIn(source.read_text(),out.read_text())
            self.assertEqual(source.read_text(),'original query timestamp and alias')
if __name__=='__main__':unittest.main()
