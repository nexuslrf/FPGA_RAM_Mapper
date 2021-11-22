from circuit import *
from parser import FPGA_cfg, PhyRAM_cfg
from tqdm import tqdm
import argparse
import numpy as np

geo_mean = lambda lst: np.exp(np.log(lst).mean())

p = argparse.ArgumentParser()
p.add_argument('--l_rams_path', type=str, default='logical_rams.txt')
p.add_argument('--lb_cnt_path', type=str, default='logic_block_count.txt')
p.add_argument('--map_out_path', type=str, default='ram_mapping.txt')
p.add_argument('--verbose', action='store_true', default=False)
p.add_argument('--phy_ram', action='append', nargs='+', help='''
        add a new ram: 
            to cfg LUTRAM: --phy_ram [interval]
            to cfg BRAM: --phy_ram [bits] [max_width] [interval]
        ''')
p.add_argument('--phy_ram_cfg_path', type=str, default='')
args = p.parse_args()
if args.phy_ram is None:
    args.phy_ram = []

if __name__ == '__main__':
    fpga_cfg = FPGA_cfg(args.l_rams_path, args.lb_cnt_path)
    phy_rams = PhyRAM_cfg(args.phy_ram_cfg_path, args.phy_ram)
    assert len(phy_rams) > 0
    mapping_file = open(args.map_out_path, 'w')
    areas = []
    for i in tqdm(range(len(fpga_cfg))):
        mapping_file.write(f'/////////////////// Circuit: {i:03d} /////////////////////\n')
        circuit = Circuit(circuit_id=i, phy_rams=phy_rams, verbose=args.verbose, **fpga_cfg[i])
        circuit.gen_cfg(mapping_file)
        areas.append(circuit.ILP_optim.objVal) # areas.append(circuit.get_area()) 
    
    mapping_file.close()
    print(f'geo mean: {geo_mean(areas)}')