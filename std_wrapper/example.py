from args import defaults, main_wrapper

def main(_gc):
    global gc
    gc = _gc

    results = {
        'hi': [[1,2,3], [5,6,7]],
        'exclude_vid': gc['exclude_video']
    }
    return results

if __name__ == '__main__':
    main_wrapper(main)
