MODE_ROM = 0
MODE_SinglePort = 1
MODE_SimpleDualPort = 2
MODE_TrueDualPort = 3

MODE_Map = {
    'ROM': MODE_ROM,
    'SinglePort': MODE_SinglePort,
    'SimpleDualPort': MODE_SimpleDualPort,
    'TrueDualPort': MODE_TrueDualPort,
}
MODE_List = ['ROM', 'SinglePort', 'SimpleDualPort', 'TrueDualPort']

bram_area = lambda bits, max_width: 9000 + 5 * bits + 90 * bits**0.5 + 600 * 2 * max_width

AREA_LB = 37500 # (35000 + 40000)/2
AREA_M8K = 96506 # bram_area(8192, 32)
AREA_M128K = 850544 # bram_area(1024*128, 128)

LB_SIZE = 10
LB_K = 6

LARGE_NUM = 100000000 #2147483647