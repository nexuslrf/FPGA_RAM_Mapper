from vars import *
import numpy as np

class PhyisicalRAM(object):
    pass

class LUTRAM(PhyisicalRAM):
    mode = [MODE_ROM, MODE_SinglePort, MODE_SimpleDualPort]
    bits = 640
    num_types = 2
    depths = np.array([64, 32])
    widths = np.array([10, 20])
    interval = 1

class M8K(PhyisicalRAM):
    mode = [MODE_ROM, MODE_SinglePort, MODE_SimpleDualPort, MODE_TrueDualPort]
    bits = 8192
    num_types = 6
    depths = np.array([8192, 4096, 2048, 1024, 512, 256])
    widths = np.array([1, 2, 4, 8, 16, 32])
    interval = 10

class M128K(PhyisicalRAM):
    mode = [MODE_ROM, MODE_SinglePort, MODE_SimpleDualPort, MODE_TrueDualPort]
    bits = 8192
    num_types = 8
    depths = np.array([131072, 65536, 32768, 16384, 8192, 4096, 2048, 1024])
    widths = np.array([1, 2, 4, 8, 16, 32, 64, 128])
    interval = 300

class LogicRAM(object):
    def __init__(self, RamID, Mode, Depth, Width):
        self.id = RamID
        self.mode = Mode
        self.depth = Depth
        self.width = Width
        # TODO current implementation only consider lutram, m8k, m128k
        self.N_lutram = 0
        self.N_m8k = 0
        self.N_m128k = 0
        self.N_exluts = 0
        self.map = None

    def pre_assign(self, p_RAM):
        if self.mode not in p_RAM.mode:
            return 0, 0, 0
        # enumerate all cfgs to find best solution.
        # start from largest depth (prefer horizontal fusion)
        p, s = 10000, 10000

        attempts = p_RAM.num_types if self.mode != MODE_TrueDualPort else p_RAM.num_types - 1
        for i in range(attempts):
            _p = (self.width - 1) // p_RAM.widths[i] + 1
            _s = (self.depth - 1) // p_RAM.depths[i] + 1
            if _p * _s < p * s:
                p, s = _p, _s
        
        ex_luts = extra_luts(s, self.width)
        return p, s, ex_luts


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