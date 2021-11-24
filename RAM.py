from vars import *
import numpy as np
import gurobipy as gp
from gurobipy import GRB

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

class LogicRAM(object):
    def __init__(self, RamID, Mode, Depth, Width, phy_rams, optim=None, mix=False):
        self.id = RamID
        self.mode = Mode
        self.depth = Depth
        self.width = Width
        self.lutram_idx = len(phy_rams.brams)
        self.mix = mix
        ''''
        pre_assign a local best config for different physical ram
        the config is 
            (p, s, w, d, ex_lut, size)
        TODO you can also perform some local pruning to simplify search
        '''
        self.lutram = self.pre_assign(phy_rams.lutram)
        self.brams = []
        for bram in phy_rams.brams:
            self.brams.append(self.pre_assign(bram))
        if self.mix:
            self.ram_mix = self.get_ram_mix(phy_rams)
            if self.ram_mix is None:
                self.mix = False

        self.I_lutram = 0
        self.I_brams = [0 for i in self.brams]

        if optim is not None:
            # setting optimization variable
            self.I_lutram = optim.addVar(vtype=GRB.BINARY) if self.lutram[-1] else 0
            for i in range(len(self.brams)):
                self.I_brams[i] = optim.addVar(vtype=GRB.BINARY) if self.brams[i][-1] else 0
            # add constraints
            
            self.N_exlut = self.I_lutram * self.lutram[-2] + \
                gp.quicksum([self.I_brams[i] * self.brams[i][-2] for i in range(len(self.brams))])
            self.N_lutram = self.I_lutram * self.lutram[-1]
            self.N_brams = [self.I_brams[i] * self.brams[i][-1] for i in range(len(self.brams))]
            if self.mix:
                self.I_mix = optim.addVar(vtype=GRB.BINARY)
                self.N_exlut = self.N_exlut + self.I_mix * self.ram_mix['ex_lut']
                base_id = self.ram_mix['base_id']
                self.N_brams[base_id] = self.N_brams[base_id] + self.I_mix * self.ram_mix['base'][-1]
                for m in ['series', 'parallel']:
                    if self.ram_mix[m] is None: continue
                    m_id = self.ram_mix[m][0]
                    if m_id < len(self.brams):
                        self.N_brams[m_id] = self.N_brams[m_id] + self.I_mix * self.ram_mix[m][-1]
                    else:
                        self.N_lutram = self.N_lutram + self.I_mix * self.ram_mix[m][-1]

                optim.addConstr(self.I_lutram + self.I_mix + gp.quicksum(self.I_brams) == 1)
            else:
                optim.addConstr(self.I_lutram + gp.quicksum(self.I_brams) == 1)

    def pre_assign(self, p_RAM, width=None, depth=None):
        if p_RAM is None or self.mode not in p_RAM['mode']:
            return 0, 0, 0, 0, 0, 0
        width = self.width if width is None else width
        depth = self.depth if depth is None else depth
        # enumerate all cfgs to find best solution.
        # start from largest depth (prefer horizontal fusion)
        attempts = p_RAM['num_cfg'] if self.mode != MODE_TrueDualPort else p_RAM['num_cfg'] - 1
        _p = (width - 1) // p_RAM['widths'][:attempts] + 1
        _s = (depth - 1) // p_RAM['depths'][:attempts] + 1
        _s[_s > 16] = LARGE_NUM
        choice = np.argmin(_p * _s) # the first min value id
        p, s = _p[choice], _s[choice]
        if s == LARGE_NUM:
            return 0, 0, 0, 0, 0, 0
        ex_luts = extra_luts(s, width)
        # True dual port doubles the extra lut cost
        if self.mode == MODE_TrueDualPort: 
            ex_luts *= 2
        return p, s, p_RAM['widths'][choice], p_RAM['depths'][choice], ex_luts, p*s

    def get_final_cfg(self):
        if self.I_lutram and self.I_lutram.x > 0.9:
            return self.lutram_idx, self.lutram
        for i in range(len(self.brams)):
            if self.I_brams[i] and self.I_brams[i].x > 0.9:
                return i, self.brams[i]
        if self.mix and self.I_mix.x > 0.9:
            return -1, self.ram_mix
        else:
            return None, None

    def get_ram_mix_v1(self, p_RAMs):
        """
        the first version
        mix mode requires p_RAM bits are in a decreasing order.
        """
        series = None
        parallel = None
        series_ex_lut = 0
        parallel_ex_lut = 0
        base_ram_id = None
        base_ram = None
        for i in range(len(self.brams)-1, -1 ,-1):
            attempts = p_RAMs[i]['num_cfg'] if self.mode != MODE_TrueDualPort else p_RAMs[i]['num_cfg'] - 1
            _p = self.width // p_RAMs[i]['widths'][:attempts]
            _s = self.depth // p_RAMs[i]['depths'][:attempts]
            tiles = _p * _s
            choice = np.argmax(tiles)
            if tiles[choice] == 0:
                continue
            p, s = _p[choice], _s[choice]
            w, d = p_RAMs[i]['widths'][choice], p_RAMs[i]['depths'][choice]
            d_left = max(self.depth - d * s, 0)
            w_left = max(self.width - w * s, 0)
            if d_left == 0  and w_left == 0:
                continue
            best_series_area = np.inf
            if d_left > 0:
                for j in range(i, -1, -1):
                    _p, _s, _w, _d, _ex_lut, _size = self.pre_assign(p_RAMs[j], self.width, d_left)
                    series_area = _size * p_RAMs[j]['area']
                    if _size > 0 and best_series_area > series_area:
                        best_series_area = series_area
                        series = (j, _p, _s, _w, _d, self.width, d_left, _size)
                        series_ex_lut = _ex_lut
                if p_RAMs.lutram is not None:
                    _p, _s, _w, _d, _ex_lut, _size = self.pre_assign(p_RAMs.lutram, self.width, d_left)
                    series_area = _size * p_RAMs.lutram['area']
                    if _size > 0 and best_series_area > series_area:
                        best_series_area = series_area
                        series = (len(p_RAMs.brams), _p, _s, _w, _d, self.width, d_left, _size)
                        series_ex_lut = _ex_lut
                series_ex_lut += extra_luts(2, self.width)
            best_parallel_area = np.inf
            if w_left > 0:
                for j in range(i, -1, -1):
                    _p, _s, _w, _d, _ex_lut, _size = self.pre_assign(p_RAMs[j], w_left, self.depth-d_left)
                    parallel_area = _size * p_RAMs[j]['area']
                    if _size > 0 and best_parallel_area > parallel_area:
                        best_parallel_area = parallel_area
                        parallel = (j, _p, _s, _w, _d, w_left, self.depth-d_left, _size)
                        parallel_ex_lut = _ex_lut
                if p_RAMs.lutram is not None:
                    _p, _s, _w, _d, _ex_lut, _size = self.pre_assign(p_RAMs.lutram, self.width, self.depth-d_left)
                    parallel_area = _size * p_RAMs.lutram['area']
                    if _size > 0  and best_parallel_area > parallel_area:
                        best_parallel_area = parallel_area
                        parallel = (len(p_RAMs.brams), _p, _s, _w, _d, w_left, self.depth-d_left, _size)
                        parallel_ex_lut = _ex_lut
            return {
                'base_id': i,
                'base': (i, p, s, w, d, self.width-w_left, self.depth-d_left, p*s),
                'ex_lut': series_ex_lut + parallel_ex_lut + extra_luts(s, self.width-w_left),
                'series': series,
                'parallel': parallel
            }
        return None


    def get_ram_mix(self, p_RAMs):
        """
        the first version
        mix mode requires p_RAM bits are in a decreasing order.
        """
        best_area = np.inf
        series = None
        parallel = None
        new_ex_lut = 0
        base_ram_id = None
        base_ram = None
        for i in range(len(self.brams)-1, -1 ,-1):
            p, s, w, d, ex_lut, size = self.brams[i]
            series_ex_lut = 0
            parallel_ex_lut = 0
            d_last_row = 0
            mix_row = False
            mix_col = False
            base_area = size * p_RAMs[i]['area']
            _series = None
            _parallel = None
            _best_area = base_area
            if s > 1:
                d_last_row = self.depth % d
                if d_last_row / d < 0.8:
                    base_area = base_area -1 * p * p_RAMs[i]['area']
                    for j in range(i, -1, -1):
                        _p, _s, _w, _d, _ex_lut, _size = self.pre_assign(p_RAMs[j], self.width, d_last_row)
                        area = base_area + _size * p_RAMs[j]['area']
                        if _size > 0 and area < _best_area:
                            mix_row = True
                            _best_area = area
                            _series = (j, _p, _s, _w, _d, self.width, d_last_row, _p * _s)
                            series_ex_lut = _ex_lut
                    if p_RAMs.lutram is not None:
                        _p, _s, _w, _d, _ex_lut, _size = self.pre_assign(p_RAMs.lutram, self.width, d_last_row)
                        area = base_area + _size * p_RAMs.lutram['area']
                        if _size > 0 and area < _best_area:
                            mix_row = True
                            _best_area = area
                            _series = (len(p_RAMs.brams), _p, _s, _w, _d, self.width, d_last_row, _p * _s)
                            series_ex_lut = _ex_lut
            if p > 1:
                w_last_col = self.width % w
                if w_last_col / w < 0.8:
                    base_area = base_area - (s-int(mix_row)) * p_RAMs[i]['area']
                    d_parallel = self.depth - d_last_row if mix_row else self.depth
                    for j in range(i, -1, -1):
                        _p, _s, _w, _d, _ex_lut, _size = self.pre_assign(p_RAMs[j], w_last_col, d_parallel)
                        area = base_area + _size * p_RAMs[j]['area']
                        if _size > 0 and area < _best_area:
                            mix_col = True
                            _best_area = area
                            _parallel = (j, _p, _s, _w, _d, w_last_col, d_parallel, _p * _s)
                            parallel_ex_lut = _ex_lut
                    if p_RAMs.lutram is not None:
                        _p, _s, _w, _d, _ex_lut, _size = self.pre_assign(p_RAMs.lutram, w_last_col, d_parallel)
                        area = (s-1) * p * p_RAMs[i]['area'] + _size * p_RAMs.lutram['area']
                        if _size > 0 and area < _best_area:
                            mix_col = True
                            _best_area = area
                            _parallel = (len(p_RAMs.brams), _p, _s, _w, _d, w_last_col, d_parallel, _p * _s)
                            parallel_ex_lut = _ex_lut
                        
            if _best_area < best_area:
                best_area = _best_area
                series = _series
                parallel = _parallel
                new_ex_lut = ex_lut + parallel_ex_lut + series_ex_lut
                base_ram_id = i
                base_ram = (base_ram_id, p-int(mix_col), s-int(mix_row), w, d, 
                        self.width - _parallel[-3] if mix_col else self.width,
                        self.depth - _series[-2] if mix_row else self.depth,
                        (p-int(mix_col))* (s-int(mix_row)))
        if series is None and parallel is None:
            return None
        else:
            return {
                'base_id': base_ram_id,
                'base': base_ram,
                'ex_lut': new_ex_lut,
                'series': series,
                'parallel': parallel
            }

# test
if __name__ == '__main__':
    ram_dict = {'RamID': 0, 'Mode': 2, 'Depth': 1025, 'Width': 127}
    from parser import FPGA_cfg, PhyRAM_cfg
    ram_cfg = PhyRAM_cfg('physical_rams.yaml')
    ram = LogicRAM(phy_rams=ram_cfg, **ram_dict)
    print(ram.brams)
    print(ram.get_ram_mix(ram_cfg))