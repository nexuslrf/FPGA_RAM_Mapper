from circuit import *
from parser import FPGA_cfg
from tqdm import tqdm
import argparse
import numpy

geo_mean = lambda lst: np.exp(np.log(lst).mean())

p = argparse.ArgumentParser()
p.add_argument('--l_rams_path', type=str, default='logical_rams.txt')
p.add_argument('--lb_cnt_path', type=str, default='logic_block_count.txt')
p.add_argument('--map_out_path', type=str, default='ram_mapping.txt')
p.add_argument('--verbose', action='store_true', default=False)
args = p.parse_args()

if __name__ == '__main__':
    fpga_cfg = FPGA_cfg(args.l_rams_path, args.lb_cnt_path)
    mapping_file = open(args.map_out_path, 'w')
    areas = []
    for i in tqdm(range(len(fpga_cfg))):
        mapping_file.write(f'/////////////////// Circuit: {i:03d} /////////////////////\n')
        circuit = Circuit(circuit_id=i, verbose=args.verbose, **fpga_cfg[i])
        circuit.gen_cfg(mapping_file)
        areas.append(circuit.ILP_optim.objVal) # areas.append(circuit.get_area()) 
    
    mapping_file.close()
    print(f'geo mean: {geo_mean(areas)}')