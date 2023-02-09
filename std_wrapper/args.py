import sys; sys.path.append('/work/awilf/Standard-Grid'); import standard_grid
import sys; sys.path.append('/work/awilf/utils/'); from alex_utils import *

defaults = [
    ("--out_dir", str, "results/hash1"), # REQUIRED - results will go here
    ("--optimizer", str, 'adamw'), # pick your arguments here: format is (name, type, default)
    ("--exclude_video", int, 0),
]

# ---- utility functions, do not modify below this line ---- #
gc = {}
def get_arguments():
    parser = standard_grid.ArgParser()
    for arg in defaults:
        parser.register_parameter(*arg)

    args = parser.compile_argparse()

    global gc
    for arg, val in args.__dict__.items():
        gc[arg] = val
    return gc

def write_results(results):
    mkdirp(gc['out_dir'])
    save_json(join(gc['out_dir'], 'results.json'), results)
    write_txt(join(gc['out_dir'], 'success.txt'), '')

def main_wrapper(main_fn):
    '''main_fn takes in gc, turns it into a global variable, returns results'''
    rt = Runtime()
    global gc
    get_arguments()
    results = main_fn(gc)
    write_results(results)
    rt.get()
