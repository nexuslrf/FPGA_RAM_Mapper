# FPGA Ram Mapper

A FPGA CAD tool that maps the logic RAMs required by the circuit to the underlying physical RAMs for Stratix-IV-like architecture, aiming to have the circuit area on FPGA as small as possible.

Detailed formulation and algorithm can be seen in this [report](./ram_mapper.pdf)

## Setup

This mapper is written in Python, all you need is to configure the right python environment.
```bash
virtualenv --system-site-packages ./venv --python=python3.7 # using venv as an example (you can also use other python3 env)
./venv/bin/activate # run proper activate according to your OS
pip install -r requirements.txt
```
Since this mapper uses a commercial optimizer [Gurobi](https://www.gurobi.com/products/gurobi-optimizer/) for solving ILP (integer linear programming), you need to additionally obtain a proper [license](https://www.gurobi.com/academia/academic-program-and-licenses/) (in the form of `grbgetkey xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`) for full functionality. You can finish configuration with a couple of cmd
```bash
wget https://packages.gurobi.com/9.5/gurobi9.5.0_linux64.tar.gz
tar -xzf gurobi9.5.0_linux64.tar.gz
cd gurobi950/linux64/bin
grbgetkey xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx # xxxxx* is the license you get from Gurobi.
```

## Quick-Start Example

Given a list of the total number of logic blocks required for general logic (not RAM-related) in each circuit in the `logic_block_count.txt` file, e.g.,
```bash
Circuit	"# Logic blocks (N=10, k=6, fracturable)"			
0	2941			 
1	2906			
...
```
There is a header line, and then each line gives the circuit number, followed by the number of logic blocks required by that circuit.

A another list of logical RAMs are used in the circuit is given in `logical_rams.txt`, e.g., 
```bash
Num_Circuits 69 
Circuit RamID Mode           Depth Width
0       0     SimpleDualPort 45    12
0       1     ROM            256   16
0       1     SinglePort     2048  32
2       0     TrueDualPort   32    36
...
```
The first two lines give the number of circuits and column headings. Each line after that lists the circuit number, an integer to identify the logical RAM, the type of RAM desired, and its depth (number of words) and width (word size).

The first RAM listed above, for example, is a RAM with one read port and one write port, and 540 bits organized as forty-five 12-bit words. There are four types of RAM:
* `ROM`: uses only one port and is never written to.
* `SinglePort`: uses only one port, as a r/w port.
* `SimpleDualPort`: uses one read port and one write port. 
* `TrueDualPort`: uses two r/w ports to do 1 read and 1 write, 2 writes, or 2 reads each cycle.

Next, we have a list of available physical RAMs we use to implement the logical RAMs, it can be defined in cmd lines or a yaml cfg file. E.g., the `physical_rams.yaml` looks like
```yaml
- RAM: LUTRAM
  type: LUTRAM
  # BRAM by default support these three modes, so you can omit this mode line
  mode: [ROM, SinglePort, SimpleDualPort]
  bits: 640
  widths: [10, 20] # in increasing order
  interval: 1 # it can be a decimal

- RAM: M8K
  type: BRAM
  mode: [ROM, SinglePort, SimpleDualPort, TrueDualPort]
  bits: 8192
  widths: [1, 2, 4, 8, 16, 32]
  interval: 10

- RAM: M128K
  type: BRAM
  # BRAM by default support these four modes, so you can omit this line
  # mode: [ROM, SinglePort, SimpleDualPort, TrueDualPort] 
  bits: 131072
  widths: 128 # that will be automatically converted to [128, 64, ..., 1]
  interval: 300 # one RAM block for every 300 logic blocks
```
Then you can run the script to get the desirable RAM mapping
```bash
python ram_mapper.py --l_rams_path logical_rams.txt \
        --lb_cnt_path logic_block_count.txt \
        --phy_ram_cfg_path physical_rams.yaml \
        --map_out_path ram_mapping.txt \
        # --enable_mix ## (optional)
```
You will get
```bash
100%|██████████████████████████| 69/69 [00:02<00:00, 32.12it/s]
runtime: 2.322944402694702 geo mean: 200232594.62447745 # this gmean is slightly lower than checker.
```
The output file `ram_mapping.txt` is like
```c
/////////////////// Circuit: 000 /////////////////////
0 0 0 LW 12 LD 45 ID 0 S 1 P 2 Type 1 Mode SimpleDualPort W 10 D 64
0 1 0 LW 12 LD 45 ID 1 S 1 P 2 Type 1 Mode SimpleDualPort W 10 D 64
...
/////////////////// Circuit: 001 /////////////////////
1 0 0 LW 18 LD 32 ID 0 S 1 P 1 Type 1 Mode SimpleDualPort W 20 D 32
...
```
The first two numbers are the `Circuit` and `RamID` respectively. The third number is the number of additional LUTs needed, calculated according to the rules described in the assignment. `LW` and `LD` are logical width and depth. They should match the logical RAM’s width and depth defined in logical_rams.txt. `ID` is a number you assigned to this group of physical RAM. This is usually just a unique id. `S` and `P` are the number of RAMs in series and in parallel respectively. You can think of the values `S` and `P` as tiling `S`×`P` RAMs together to form one logical RAM. `Type` is the RAM type number and it matches the order of BRAM types you defined. Using the example given above, LUTRAM is `Type` 1; 8 kbit block RAM is `Type` 2 and 128 kbit block RAM is `Type` 3. `Mode` is the mode that the physical RAM is in. It should be the same as the logical RAM’s mode. `W` and `D` are the width and depth configuration that the physical RAM is in.

*This mapper also supports advanced mixed BRAM mapping. You check the source code to see how it is implemented.

## Provided Solutions
* `ram_mapping_default.txt`: mapping results with default physical RAMs, no mixed assignment
* `ram_mapping_default_mix.txt`: mapping results with default physical RAMs, with mixed assignment
* `ram_mapping_mine.txt`: mapping results with a new list of physical RAMs (`-l 1 1 -b 8196 16 14 1 -b 16384 32 28 1` in checker format), no mixed assignment
* `ram_mapping_mine_mix.txt`: mapping results with a new list of physical RAMs (`-l 1 1 -b 8196 16 14 1 -b 16384 32 28 1` in checker format), with mixed assignment 
