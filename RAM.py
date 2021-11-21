from vars import *
import numpy as np
import gurobipy as gp
from gurobipy import GRB

# class PhyisicalRAM(object):
#     pass

# class LUTRAM(PhyisicalRAM):
#     mode = [MODE_ROM, MODE_SinglePort, MODE_SimpleDualPort]
#     type = 1
#     bits = 640
#     num_types = 2
#     depths = np.array([64, 32])
#     widths = np.array([10, 20])
#     interval = 1

# class M8K(PhyisicalRAM):
#     mode = [MODE_ROM, MODE_SinglePort, MODE_SimpleDualPort, MODE_TrueDualPort]
#     type = 2
#     bits = 8192
#     num_types = 6
#     depths = np.array([8192, 4096, 2048, 1024, 512, 256])
#     widths = np.array([1, 2, 4, 8, 16, 32])
#     interval = 10

# class M128K(PhyisicalRAM):
#     mode = [MODE_ROM, MODE_SinglePort, MODE_SimpleDualPort, MODE_TrueDualPort]
#     type = 3
#     bits = 131072
#     num_types = 8
#     depths = np.array([131072, 65536, 32768, 16384, 8192, 4096, 2048, 1024])
#     widths = np.array([1, 2, 4, 8, 16, 32, 64, 128])
#     interval = 300
            

class LogicRAM(object):
    def __init__(self, RamID, Mode, Depth, Width, phy_rams, optim=None):
        self.id = RamID
        self.mode = Mode
        self.depth = Depth
        self.width = Width
        self.lutram_idx = len(phy_rams.brams)
        ''''
        pre_assign a local best config for different physical ram
        the config is (p, s, w, d, ex_lut, size)
        TODO you can also perform some local pruning to simplify optimization
        TODO maybe consider mixed assignment later.
        '''
        self.lutram = self.pre_assign(phy_rams.lutram)
        self.brams = []
        for bram in phy_rams.brams:
            self.brams.append(self.pre_assign(bram))

        self.I_lutram = 0
        self.I_brams = [0 for i in self.brams]

        if optim is not None:
            # setting optimization variable
            self.I_lutram = optim.addVar(vtype=GRB.BINARY) if self.lutram[-1] else 0
            for i in range(len(self.brams)):
                self.I_brams[i] = optim.addVar(vtype=GRB.BINARY) if self.brams[i][-1] else 0
            # add constraints
            optim.addConstr(self.I_lutram + gp.quicksum(self.I_brams) == 1)
            self.N_exlut = self.I_lutram * self.lutram[-2] + \
                gp.quicksum([self.I_brams[i] * self.brams[i][-2] for i in range(len(self.brams))])
            self.N_lutram = self.I_lutram * self.lutram[-1]
            self.N_brams = [self.I_brams[i] * self.brams[i][-1] for i in range(len(self.brams))]

    def pre_assign(self, p_RAM):
        if p_RAM is None or self.mode not in p_RAM['mode']:
            return 0, 0, 0, 0, 0, 0
        # enumerate all cfgs to find best solution.
        # start from largest depth (prefer horizontal fusion)
        attempts = p_RAM['num_cfg'] if self.mode != MODE_TrueDualPort else p_RAM['num_cfg'] - 1
        _p = (self.width - 1) // p_RAM['widths'][:attempts] + 1
        _s = (self.depth - 1) // p_RAM['depths'][:attempts] + 1
        _s[_s > 16] = LARGE_NUM
        choice = np.argmin(_p * _s) # the first min value id
        p, s = _p[choice], _s[choice]
        if s == LARGE_NUM:
            return 0, 0, 0, 0, 0, 0
        ex_luts = extra_luts(s, self.width)
        # True dual port doubles the extra lut cost
        if self.mode == MODE_TrueDualPort: 
            ex_luts *= 2
        return p, s, p_RAM['widths'][choice], p_RAM['depths'][choice], ex_luts, p*s

    def get_final_cfg(self):
        if self.I_lutram and self.I_lutram.x == 1:
            return self.lutram_idx, self.lutram
        for i in range(len(self.brams)):
            if self.I_brams[i] and self.I_brams[i].x == 1:
                return i, self.brams[i]
        else:
            return None, None

def extra_luts(r, w):
    if r == 1:
        return 0
    num_decode = r if r!=2 else 1
    num_mux = w * mux_size(r)
    return num_decode + num_mux

# number of 4:1 mux needed to build one r:1 mux
def mux_size(r):
    level = 4
    size = 1
    while r > level:
        size += (r - 1) // level + 1
        level *= 4
    return size

# test
if __name__ == '__main__':
    ram_dict = {'RamID': 0, 'Mode': 2, 'Depth': 64, 'Width': 36}
    ram = LogicRAM(**ram_dict)
    print(ram.lutram)
    print(ram.m8k)
    print(ram.m128k)