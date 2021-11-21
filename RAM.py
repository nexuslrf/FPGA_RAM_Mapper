from vars import *
import numpy as np
from gurobipy import GRB

class PhyisicalRAM(object):
    pass

class LUTRAM(PhyisicalRAM):
    mode = [MODE_ROM, MODE_SinglePort, MODE_SimpleDualPort]
    type = 1
    bits = 640
    num_types = 2
    depths = np.array([64, 32])
    widths = np.array([10, 20])
    interval = 1

class M8K(PhyisicalRAM):
    mode = [MODE_ROM, MODE_SinglePort, MODE_SimpleDualPort, MODE_TrueDualPort]
    type = 2
    bits = 8192
    num_types = 6
    depths = np.array([8192, 4096, 2048, 1024, 512, 256])
    widths = np.array([1, 2, 4, 8, 16, 32])
    interval = 10

class M128K(PhyisicalRAM):
    mode = [MODE_ROM, MODE_SinglePort, MODE_SimpleDualPort, MODE_TrueDualPort]
    type = 3
    bits = 8192
    num_types = 8
    depths = np.array([131072, 65536, 32768, 16384, 8192, 4096, 2048, 1024])
    widths = np.array([1, 2, 4, 8, 16, 32, 64, 128])
    interval = 300

class LogicRAM(object):
    def __init__(self, RamID, Mode, Depth, Width, optim=None):
        self.id = RamID
        self.mode = Mode
        self.depth = Depth
        self.width = Width
        ''''
        pre_assign a local best config for different physical ram
        the config is (p, s, w, d, ex_lut, size)
        TODO you can also perform some local pruning to simplify optimization
        TODO maybe consider mixed assignment later.
        TODO current implementation only consider lutram, m8k, m128k
        '''
        self.lutram = self.pre_assign(LUTRAM)
        self.m8k = self.pre_assign(M8K)
        self.m128k = self.pre_assign(M128K)
        # final config
        self.final_cfg = self.m8k
        self.I_lutram, self.I_m8k, self.I_m128k = 0, 0, 0

        if optim is not None:
            # setting optimization variable
            self.I_lutram = optim.addVar(vtype=GRB.BINARY, name=f"{self.id}_lutram") if self.lutram[-1] else 0
            self.I_m8k = optim.addVar(vtype=GRB.BINARY, name=f"{self.id}_m8k") if self.m8k[-1] else 0
            self.I_m128k = optim.addVar(vtype=GRB.BINARY, name=f"{self.id}_m128k") if self.m128k[-1] else 0
            # add constraints
            optim.addConstr(self.I_lutram + self.I_m8k + self.I_m128k == 1)
            self.N_exlut = self.I_lutram * self.lutram[-2] + \
                self.I_m8k * self.m8k[-2] + self.I_m128k * self.m128k[-2] 
            self.N_lutram = self.I_lutram * self.lutram[-1]
            self.N_m8k = self.I_m8k * self.m8k[-1]
            self.N_m128k = self.I_m128k * self.m128k[-1]

    def pre_assign(self, p_RAM):
        if self.mode not in p_RAM.mode:
            return 0, 0, 0, 0, 0, 0
        # enumerate all cfgs to find best solution.
        # start from largest depth (prefer horizontal fusion)
        attempts = p_RAM.num_types if self.mode != MODE_TrueDualPort else p_RAM.num_types - 1
        _p = (self.width - 1) // p_RAM.widths[:attempts] + 1
        _s = (self.depth - 1) // p_RAM.depths[:attempts] + 1
        choice = np.argmin(_p * _s) # the first min value id
        p, s = _p[choice], _s[choice]
        ex_luts = extra_luts(s, self.width)
        # True dual port doubles the extra lut cost
        if self.mode == MODE_TrueDualPort: 
            ex_luts *= 2
        return p, s, p_RAM.widths[choice], p_RAM.depths[choice], ex_luts, p*s

    def get_final_cfg(self):
        if self.I_lutram and self.I_lutram.x == 1:
            return LUTRAM, self.lutram
        if self.I_m8k and self.I_m8k.x == 1:
            return M8K, self.m8k
        if self.I_m128k and self.I_m128k.x == 1:
            return M128K, self.m128k
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