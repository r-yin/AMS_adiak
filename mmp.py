import numpy
import argparse
from subprocess import Popen, PIPE
from ctypes import cdll, POINTER, c_bool, c_double


p = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
p.add_argument("-d", "--device", help="Device config string", default="cpu")
p.add_argument("-c", "--stop-cycle", type=int, help="Stop cycle", default=10)
p.add_argument("-m", "--num-mats", type=int,help="Number of materials", default=5)
p.add_argument("-e", "--num-elems", type=int,help="Number of elements", default=10000)
p.add_argument("-q", "--num-qpts", type=int, help="Number of quadrature points per element", default=64)
p.add_argument("-r", "--empty-element-ratio", type=float, help="Fraction of elements that are empty " "for each material. If -1 use a random value for each. ", default=-1)
p.add_argument("-p", "--pack-sparse", "--np", "--do-not-pack-sparse", type=bool, help="pack sparse material data before evals (cpu only)", default=True)

args = p.parse_args()

print(args)
indicators = numpy.zeros(args.num_elems*args.num_mats, dtype=bool)
min_ratio=.2
for k in range(args.num_mats):
    nz=0
    if args.empty_element_ratio == -1:
        ratio = numpy.random.random() * (1-min_ratio) + min_ratio
    else:
        ratio = args.empty_element_ratio
    num_nonzeros_elems = ratio * args.num_elems
    for i in range(args.num_elems):
        if nz < num_nonzeros_elems:
            if (num_nonzeros_elems - nz) == (args.num_elems - i) or numpy.random.random() <= ratio:
                indicators[k*args.num_elems+i] = True
                nz += 1
# now fill the input arrays
density = numpy.zeros(args.num_mats*args.num_elems*args.num_qpts, dtype=float)
energy = numpy.zeros(args.num_mats*args.num_elems*args.num_qpts, dtype=float)

for k in range(args.num_mats):
    for i in range(args.num_elems):
        if not indicators[i+k*args.num_elems]:
            continue
        for j in range(args.num_qpts):
            density[j + i*args.num_qpts + k*args.num_elems*args.num_qpts] = .1 + numpy.random.random()
            energy[j + i*args.num_qpts + k*args.num_elems*args.num_qpts]  = .1 + numpy.random.random()

is_cpu = args.device.lower() == "cpu"
libname = './mmp-toss_3_x86_64_ib.so'
lib = cdll.LoadLibrary(libname)

p = Popen(("nm", f"{libname}"), stdout=PIPE, stderr=PIPE)
o, e = p.communicate()

# Figures out the mangled name
# I know it's a hack
for l in o.decode().split("\n"):
    if "eval_data" in l:
        eval_data_function_name = l.split()[2]

eval_data_function = getattr(lib, eval_data_function_name)

# Now let's call it
eval_data_function(args.stop_cycle, is_cpu, args.pack_sparse,
                   args.num_qpts, args.num_elems, args.num_mats,
                   density.ctypes.data_as(POINTER(c_double)),
                   energy.ctypes.data_as(POINTER(c_double)),
                   indicators.ctypes.data_as(POINTER(c_bool)))
