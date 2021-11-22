from pickle import NONE
from typing import List
from vars import *
import yaml
import numpy as np

class FPGA_cfg(object):
    def __init__(self, ram_cfg_path, lb_cnt_path):
        ram_reader = open(ram_cfg_path)
        lb_cnt_reader = open(lb_cnt_path)
        # parsing the cfg files
        self.num_circuit = eval(ram_reader.readline().strip().split()[1])
        # skipping header
        ram_reader.readline() 
        lb_cfg = [ p.strip() for p in lb_cnt_reader.readline().strip()\
            .replace(')', '(').split('(')[1].split(',')]
        lb_cfg = {
            p.split('=')[0] if '=' in p else 'type': 
            eval(p.split('=')[1]) if '=' in p else p
            for p in lb_cfg}
        self.lb_size = lb_cfg['N'] if 'N' in lb_cfg else 10
        self.lb_k = lb_cfg['k'] if 'k' in lb_cfg else 6
        self.lb_type = lb_cfg['type'] if 'type' in lb_cfg else 'fracturable'
        # read each circuits
        self.circuits = [{'rams': []} for i in range(self.num_circuit)]
        for line in lb_cnt_reader.readlines():
            c_id, n_lb = [eval(v) for v in line.strip().split()]
            self.circuits[c_id]['num_lb'] = n_lb
        for line in ram_reader.readlines():
            c_id, r_id, mode, depth, width = \
                [eval(v) if v.isdigit() else v for v in line.strip().split()]
            self.circuits[c_id]['rams'].append(
                {
                    'RamID': r_id,
                    'Mode': MODE_Map[mode],
                    'Depth': depth,
                    'Width': width
                }
            )

    def __len__(self):
        return len(self.circuits)

    def __getitem__(self, index):
        return self.circuits[index]

class PhyRAM_cfg(object):
    def __init__(self, ram_cfg_path='', rams=[]):
        # there is only one type of lutram but multi types of bram
        self.lutram = None 
        self.brams = []
        p_ram_id = 1
        if ram_cfg_path != '':
            f = open(ram_cfg_path).read()
            cfg = yaml.load(f, Loader=yaml.FullLoader)
            for c in cfg:
                p_ram = complete_RAM_cfg(id=p_ram_id, **c)
                if p_ram['type'] == 'LUTRAM':
                    self.lutram = p_ram
                else:
                    self.brams.append(p_ram)
                p_ram_id += 1
        for r in rams:
            p_ram = complete_RAM_cfg(*[eval(v) for v in r[:-1]],
                        interval=eval(r[-1]),        
                        type='LUTRAM' if len(r) == 1 else 'BRAM',
                        id=p_ram_id)
            if p_ram['type'] == 'LUTRAM':
                self.lutram = p_ram # cmd line can overload cfg file
            else:
                self.brams.append(p_ram)
            p_ram_id += 1
        
        self.lb_area = AREA_LB_NO_RAM if self.lutram is None else \
            (AREA_LB_NO_RAM * self.lutram['interval'] + AREA_LB_RAM) / (self.lutram['interval']+1)

    def __len__(self):
        n = len(self.brams)
        return n + 1 if self.lutram is not None else n
    
    def __getitem__(self, index):
        if index < len(self.brams):
            return self.brams[index]
        else:
            return self.lutram

def complete_RAM_cfg(bits=640, widths=[10, 20], interval=1, type='LUTRAM', 
                mode=None, RAM='', id=0):
    cfg = {}
    cfg['type'] = type
    cfg['bits'] = bits
    cfg['name'] = RAM
    cfg['id'] = id
    cfg['interval'] = interval
    if mode is None:
        cfg['mode'] = ['ROM', 'SinglePort', 'SimpleDualPort']
        if cfg['type'] == 'BRAM': cfg['mode'].append('TrueDualPort')
    else:
        cfg['mode'] = mode
    cfg['mode'] = [MODE_Map[m] for m in cfg['mode']]

    if not isinstance(widths, list):
        widths = [1<<i for i in range(int(np.log2(widths))+1)]
    cfg['widths'] = np.array(widths)
    cfg['depths'] = np.array([cfg['bits']//w for w in cfg['widths']])
    cfg['num_cfg'] = len(cfg['widths'])
    cfg['area'] = bram_area(cfg['bits'], cfg['widths'][-1]) if cfg['type'] == 'BRAM' \
        else AREA_LB_RAM
    cfg['area'] = round(cfg['area'])
    return cfg

if __name__ == '__main__':
    fpga_cfg = FPGA_cfg('logical_rams.txt', 'logic_block_count.txt')
    print(fpga_cfg[-1])
    ram_cfg = PhyRAM_cfg('physical_rams.yaml')
    print(ram_cfg.lutram)
    print(ram_cfg.brams)
