#!/usr/bin/env python3
"""Write an experiment CSV and 205/215 mm STL coupons. Never generates printer G-code."""
import argparse
import csv
from pathlib import Path

def coupon(path,size,thickness=2.):
    # Eight vertices, twelve outward-oriented triangles, centred by the slicer.
    v=[(0,0,0),(size,0,0),(size,size,0),(0,size,0),
       (0,0,thickness),(size,0,thickness),(size,size,thickness),(0,size,thickness)]
    faces=[(0,2,1),(0,3,2),(4,5,6),(4,6,7),(0,1,5),(0,5,4),
           (1,2,6),(1,6,5),(2,3,7),(2,7,6),(3,0,4),(3,4,7)]
    lines=['solid deep_calibration_coupon']
    for face in faces:
        a,b,c=[v[i] for i in face]
        ab=[b[i]-a[i] for i in range(3)];ac=[c[i]-a[i] for i in range(3)]
        n=[ab[1]*ac[2]-ab[2]*ac[1],ab[2]*ac[0]-ab[0]*ac[2],ab[0]*ac[1]-ab[1]*ac[0]]
        length=sum(x*x for x in n)**.5;n=[x/length for x in n]
        lines+=['  facet normal '+' '.join(str(x) for x in n),'    outer loop']
        lines+=['      vertex '+' '.join(str(x) for x in p) for p in (a,b,c)]
        lines+=['    endloop','  endfacet']
    lines+=['endsolid deep_calibration_coupon']
    Path(path).write_text('\n'.join(lines)+'\n')

def plan(output,material='PLA'):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    rows=[]
    base=dict(material=material,height=.2,width=.45,speed=40,fan=0,layers_to_observe='1',coupon_height=2,
              offset_order='GOOD,TOO_HIGH,GOOD,TOO_HIGH,GOOD',
              note='Keep GOOD offset fixed; use two printable TOO_HIGH offsets; hold >=20-30 s; keep temperatures/flow/PA/mesh/soak fixed')
    for repeat in range(1,5):
        rows.append(dict(base,run='baseline_repeat_%d'%repeat,changed='repeat',
                         offset_order=('GOOD,TOO_HIGH,GOOD,TOO_HIGH,GOOD' if repeat%2 else 'TOO_HIGH,GOOD,TOO_HIGH,GOOD,TOO_HIGH,GOOD')))
    for key,values in [('speed',(20,60)),('height',(.12,.16,.24)),('width',(.4,.5)),('fan',(30,60,100))]:
        for value in values: rows.append(dict(base,run='%s_%s'%(key,value),changed=key,**{key:value}))
    rows.append(dict(base,run='layer_background',changed='layer',layers_to_observe='1,2,3',
                     note='Layer 2/3 characterize background, not nozzle-to-bed gap; set metadata on layer changes'))
    with open(output/'experiment_plan.csv','w',newline='') as stream:
        fields=['run','changed']+list(base)
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(rows)
    coupon(output/'square_205x205x2.stl',205.)
    coupon(output/'square_215x215x2.stl',215.)
    return rows

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',default='experiments');p.add_argument('--material',default='PLA')
    args=p.parse_args();plan(args.output,args.material)
