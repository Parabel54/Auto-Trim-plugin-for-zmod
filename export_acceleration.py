#!/usr/bin/env python3
"""Stream saved native-mapped acceleration frames to CSV after the print."""
import argparse
import csv
import glob
from deep_calibration_sensors import read_acceleration

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('parts',nargs='+',help='Ordered .dca parts, or a quoted glob pattern')
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    paths=sorted(set(path for pattern in args.parts for path in glob.glob(pattern)))
    if not paths:parser.error('no acceleration parts found')
    count=0
    with open(args.output,'w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=['t','x','y','z','host_received','errors','overflows'])
        writer.writeheader()
        for row in read_acceleration(paths):writer.writerow(row);count+=1
    print('Exported %d native mapped/scaled frames. This is not original ADC integer data.'%count)
if __name__=='__main__':main()
