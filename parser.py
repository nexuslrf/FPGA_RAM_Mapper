from vars import *

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

if __name__ == '__main__':
    cfg = FPGA_cfg('logical_rams.txt', 'logic_block_count.txt')
    print(cfg[-1])
