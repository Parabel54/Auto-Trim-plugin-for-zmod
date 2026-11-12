from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from make_plan import plan

class PlanTests(unittest.TestCase):
    def test_plan_changes_one_declared_factor_and_coupons_have_requested_dimensions(self):
        with tempfile.TemporaryDirectory() as tmp:
            rows=plan(tmp)
            self.assertEqual(len([r for r in rows if r['changed']=='repeat']),4)
            base=rows[0]
            for row in rows:
                if row['changed'] in ('height','width','speed','fan'):
                    self.assertEqual([key for key in ('height','width','speed','fan') if row[key]!=base[key]],[row['changed']])
            for size in (205,215):
                text=(Path(tmp)/('square_%dx%dx2.stl'%(size,size))).read_text()
                vertices=[list(map(float,line.split()[1:])) for line in text.splitlines() if line.strip().startswith('vertex ')]
                self.assertEqual(len(vertices),36)
                self.assertEqual([max(v[i] for v in vertices)-min(v[i] for v in vertices) for i in range(3)],[size,size,2])
                volume=0.
                for i in range(0,len(vertices),3):
                    a,b,c=vertices[i:i+3]
                    volume+=(a[0]*(b[1]*c[2]-b[2]*c[1])+a[1]*(b[2]*c[0]-b[0]*c[2])+a[2]*(b[0]*c[1]-b[1]*c[0]))/6.
                self.assertAlmostEqual(volume,size*size*2.)

if __name__=='__main__': unittest.main()
