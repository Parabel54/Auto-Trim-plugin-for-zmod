"""Run the actual installer with only its two filesystem roots redirected."""
from pathlib import Path
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
class InstallerTests(unittest.TestCase):
    def fixture(self,base):
        pkg=base/'package';pkg.mkdir()
        for name in ('deep_calibration.py','deep_calibration_sensors.py','deep_calibration_mesh.py','deep_calibration_approach.py','deep_calibration_auto_mesh.cfg','deep_calibration_start.cfg'):
            (pkg/name).parent.mkdir(parents=True,exist_ok=True)
            (pkg/name).write_text((ROOT/name).read_text())
        extras=[base/'klipper13',base/'native_klipper']
        script=(ROOT/'install_deep_calibration.sh').read_text().replace('/usr/data/zmod/klipper/klippy/extras',str(extras[0])).replace('/usr/prog/klipper/klippy/extras',str(extras[1]))
        install=pkg/'install.sh';install.write_text(script)
        return pkg,extras,lambda:subprocess.run(['sh',str(install)],capture_output=True,text=True)
    def test_both_native_roots_link_all_modules_and_rerun_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            pkg,extras,run=self.fixture(Path(tmp))
            for p in extras:p.mkdir()
            for i in range(2):
                result=run();self.assertEqual(result.returncode,0,result.stderr)
                for p in extras:
                    for name in ('deep_calibration.py','deep_calibration_sensors.py','deep_calibration_mesh.py','deep_calibration_approach.py'):
                        self.assertTrue((p/name).is_symlink());self.assertEqual((p/name).resolve(),pkg/name)
    def test_regular_file_conflict_preflights_both_roots_before_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            pkg,extras,run=self.fixture(Path(tmp))
            for p in extras:p.mkdir()
            conflict=extras[1]/'deep_calibration_mesh.py';conflict.write_text('preserve')
            result=run();self.assertNotEqual(result.returncode,0)
            self.assertEqual(list(extras[0].iterdir()),[]);self.assertEqual(conflict.read_text(),'preserve')
    def test_missing_module_and_unsupported_paths_fail_without_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            pkg,extras,run=self.fixture(Path(tmp));self.assertNotEqual(run().returncode,0)
            for p in extras:p.mkdir()
            (pkg/'deep_calibration_sensors.py').unlink()
            self.assertNotEqual(run().returncode,0)
            for p in extras:self.assertEqual(list(p.iterdir()),[])
if __name__=='__main__':unittest.main()
