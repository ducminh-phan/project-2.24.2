import json
import logging
import multiprocessing as mp
import os
import sys
import time
from functools import wraps
from multiprocessing.pool import ThreadPool

import networkx as nx

import steiner_vertices
from utils import parse_graph, find_starting_solution, graph_weight

logging.basicConfig(filename='logs/error.log', level=logging.INFO)
logger = logging.getLogger('main')

METHODS = [steiner_vertices]


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
            logger.info((f.__name__, args, kwargs))
            logger.error(e, exc_info=True)
            print('{} raised when solving #{} with method {}'.format(
                e.__class__.__name__, args[1], METHODS[args[0]].__name__
            ))

            return {}

    return wrapper


def timeout(t=None):
    """
    Add a timeout of t seconds to a function. It calls the worker function
    in a background thread, and then wait for a result for t seconds.
    If the timeout expires, it raises an exception, which will abruptly
    terminate the thread worker is executing in.
    """

    def _timeout(worker):
        @wraps(worker)
        def wrapper(*args, **kwargs):
            with ThreadPool(processes=1) as pool:
                res = pool.apply_async(worker, args, kwargs)
                try:
                    # Wait t seconds for the worker to complete
                    out = res.get(timeout=t)
                    return out
                except mp.TimeoutError:
                    print("Abort solving #{} due to timeout".format(args[1]))
                    sys.exit()

        return wrapper

    return _timeout


@timeout()
@log_error
def solve(method_id, instance_id, max_runtime=None):
    start_all = time.time()
    print("Solving #{} in Process #{}".format(instance_id, os.getpid()))

    method = METHODS[method_id]

    g, terminals = parse_graph(instance_id)
    s = find_starting_solution(g, terminals)
    s_weight = graph_weight(s)

    epoch = 0
    weights = [s_weight]
    epoch_times = []
    total_time = 0

    stop = False

    while not stop:
        epoch += 1
        start = time.time()

        new_s = method.local_search(g, s, terminals)
        new_s_weight = graph_weight(new_s)
        epoch_time = round(time.time() - start, 3)

        if new_s_weight < s_weight:
            s_weight = new_s_weight
            s = new_s.copy()
        else:
            break

        weights.append(new_s_weight)
        epoch_times.append(epoch_time)
        total_time += epoch_time

        if max_runtime is not None and total_time > max_runtime:
            stop = True

    nx.write_gpickle(s, 'results/{}/{}.gpickle'.format(
        method.__name__, instance_id
    ))

    end_all = time.time()
    run_time = end_all - start_all
    print('Solved #{} after {} seconds'.format(instance_id, round(run_time, 3)))

    return {instance_id: {'weights': weights, 'epoch_times': epoch_times, 'run_time': run_time}}


def main():
    results = {}

    with open('small_instances.json') as f:
        small_instances = json.load(f)

    def collect_result(result):
        results.update(result)
        with open('results/{}.json'.format(method_name), 'w') as f:
            json.dump(results, f)

    start = time.time()

    for method_id in range(len(METHODS)):
        pool = mp.Pool()
        method_name = METHODS[method_id].__name__

        for instance_id in small_instances:
            pool.apply_async(solve, args=(method_id, instance_id),
                             callback=collect_result)

        pool.close()
        pool.join()

    print('Elapsed time:', time.time() - start)


if __name__ == '__main__':
    main()
