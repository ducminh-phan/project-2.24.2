import argparse
import json
import logging
import logging.config
import multiprocessing as mp
import os
import time
from functools import wraps

import interruptingcow as ic
import networkx as nx

import key_paths
import steiner_vertices
from utils import parse_graph, graph_weight

METHODS = {'kv': key_paths, 'sv': steiner_vertices}


def setup_logging(
        default_path='./logs/config.json',
        default_level=logging.INFO
):
    """Setup logging configuration"""
    if os.path.exists(default_path):
        with open(default_path) as f:
            config = json.load(f)
        logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=default_level)


# Setup logging
setup_logging()
console_logger = logging.getLogger('console')
file_logger = logging.getLogger('file')


def log_error(f):
    """
    Try to execute the solver. If any exception raised, log the info
    and return an empty result.
    """

    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            file_logger.info('\n{}, {}, {}'.format(f.__name__, args, kwargs))
            file_logger.error(e, exc_info=True)

            console_logger.error('{} raised when solving #{} with method {}'.format(
                e.__class__.__name__, args[0], METHODS[args[1].method].__name__
            ))

            return {}

    return wrapper


class NullContextManager:
    """
    Dummy Context Manager to use as a replacement for interruptingcow.timeout
    in the case no timeout was specified.
    """

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self, *args, **kwargs):
        pass

    def __exit__(self, *args, **kwargs):
        pass


@log_error
def solve(instance_id, args):
    start_all = time.time()
    print("Start solving #{} in Process #{}".format(instance_id, os.getpid()))

    method = METHODS[args.method]

    if args.verbose:
        print('Parsing instance #{}...'.format(instance_id))

    g, terminals = parse_graph(instance_id)

    # Parse the precomputed starting solution
    s = nx.read_gpickle('results/starting_solutions/{}/{}.gpickle'.format(
        args.start, instance_id
    ))

    s_weight = graph_weight(s)

    if args.verbose:
        print('G has {} nodes, {} edges, {} terminals.'.format(
            len(g.nodes), len(g.edges), len(terminals)
        ))
        print('The starting solution has {} nodes with the total weight of {}.'.format(
            len(s.nodes), s_weight
        ))

    epoch = 0
    weights = [s_weight]
    epoch_times = []
    total_time = 0

    # Setup the timeout
    context_manager = NullContextManager if args.timeout == 0 else ic.timeout

    try:
        with context_manager(args.timeout, TimeoutError):
            while True:
                epoch += 1
                start = time.time()

                if args.verbose:
                    print("Epoch {}:".format(epoch), end=' ', flush=True)

                new_s = method.local_search(g, s, terminals,
                                            early_stop=args.early_stop)
                new_s_weight = graph_weight(new_s)
                epoch_time = round(time.time() - start, 3)

                if new_s_weight < s_weight:
                    if args.verbose:
                        print("The solution weight improves from {} to {}.".format(
                            s_weight, new_s_weight
                        ))

                    s_weight = new_s_weight
                    s = new_s.copy()
                else:
                    if args.verbose:
                        print("The solution weight does not improve, "
                              "returning the solution.")
                    break

                weights.append(new_s_weight)
                epoch_times.append(epoch_time)
                total_time += epoch_time
    except TimeoutError:
        print('Stop solving #{} due to timeout.'.format(instance_id))

    if args.verbose:
        print('The final solution has {} nodes.'.format(
            len(s.nodes)
        ))

    if args.save:
        nx.write_gpickle(s, 'results/{}/{}.gpickle'.format(
            get_name(args), instance_id
        ))

    end_all = time.time()
    run_time = end_all - start_all
    print('Solved #{} after {} seconds'.format(instance_id, round(run_time, 3)))

    return {instance_id: {'weights': weights, 'epoch_times': epoch_times, 'run_time': run_time}}


def get_name(args):
    """
    Get the name for the result folder and log from parsed args
    """
    name = METHODS[args.method].__name__

    name += '_{}'.format(args.start)

    if not args.early_stop:
        name += '_noearly'

    if args.timeout:
        name += '_{}'.format(args.timeout)

    return name


def check_args(parser, args):
    if args.id is not None:
        if args.instances == 'all':
            parser.error("Cannot use --all and --id at the same time.")

        args.instances = 'multi'

    if args.verbose and (args.id is None or len(args.id) != 1):
        parser.error("Can turn on verbosity mode if and only if "
                     "a single instance id is provided with --id.")

    if args.id is not None and not all(1 <= iid <= 199 and iid % 2
                                       for iid in args.id):
        parser.error("The instance id provided need to be odd numbers "
                     "between 1 and 199 (inclusive).")

    return args


def parse_args():
    parser = argparse.ArgumentParser(description='Use local search to solve the '
                                                 'Steiner tree problem.')
    parser.add_argument('-s', '--start', choices=('dnh', 'mst'), default='dnh',
                        help="The choice of algorithm to find the starting solution. "
                             "Default: '%(default)s'.")
    parser.add_argument('-m', '--method', choices=('kv', 'sv'), default='kv',
                        help="The neighborhood type to use in the local search. "
                             "The options are corresponding to key vertices and "
                             "steiner vertices. Default: '%(default)s'.")
    parser.add_argument('-n', '--no-early-stop', dest='early_stop', action='store_false',
                        help="Do not use early stopping by default in the local search.")
    parser.add_argument('-a', '--all', dest='instances', action='store_const',
                        const='all', default='small',
                        help="Solve all 100 instances instead of 25 small instances "
                             "by default. Cannot be used together with the option --id.")
    parser.add_argument('-t', '--timeout', type=int, default=3600,
                        help="The time limit to solve for an instance, in seconds. "
                             "Set this to 0 to remove the timeout. Default: %(default)s.")
    parser.add_argument('-i', '--id', nargs='+', type=int,
                        help="Solve the instances with the id provided as a list "
                             "of space-separated integers. Cannot be used together "
                             "with the option --all.")
    parser.add_argument('--save', action='store_true',
                        help="Save the obtained solutions into a folder corresponding "
                             "to the options provided.")
    parser.add_argument('-v', '--verbose', action='store_true',
                        help="Turn on verbosity mode. Can be set if and only if "
                             "a single instance id is provided with --id.")

    args = parser.parse_args()
    args = check_args(parser, args)

    return args


def main():
    start = time.time()

    args = parse_args()

    # Create the folder to store the results if it does not exist
    directory = 'results/{}'.format(get_name(args))
    if args.save and not os.path.exists(directory):
        os.makedirs(directory)

    # Get the current results
    try:
        with open('{}.json'.format(directory)) as f:
            content = f.read()

            if not content:
                # The file is empty, we set an empty dict for the results
                results = {}
            else:
                results = json.loads(content)
    except FileNotFoundError:
        # The results file does not exist, this happens if and only if
        # the options are used for the first time
        results = {}

    def collect_result(result):
        """
        Collect and update the result of an instance into the overall results
        """
        results.update(result)
        with open('{}.json'.format(directory), 'w') as _f:
            json.dump(results, _f)

    # Get the instances to solve
    if args.instances == 'all':
        instances = range(1, 200, 2)
    elif args.instances == 'small':
        with open('small_instances.json') as f:
            instances = json.load(f)
    else:
        instances = args.id

    # Create the pool of processes
    pool = mp.Pool()

    for instance_id in instances:
        pool.apply_async(solve, args=(instance_id, args), callback=collect_result)

    # Starting solving
    pool.close()
    pool.join()

    print('Elapsed time:', time.time() - start)


if __name__ == '__main__':
    main()
