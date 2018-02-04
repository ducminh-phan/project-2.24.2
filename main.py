import json
import logging
import multiprocessing as mp
import time

import networkx as nx

import steiner_vertices
from utils import parse_graph, find_starting_solution, graph_weight, try_log

logging.basicConfig(filename='logs/error.log', level=logging.ERROR)
logger = logging.getLogger('main')

METHODS = [steiner_vertices]


@try_log(logger)
def solve(method_id, instance_id, max_runtime=None):
    import os

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

        if max_runtime is not None and total_time > max_runtime * 60:
            stop = True

    nx.write_gpickle(s, 'results/{}/{}.gpickle'.format(
        method.__name__, instance_id
    ))

    end_all = time.time()
    run_time = end_all - start_all
    print('Done #{} after {} seconds'.format(instance_id, round(run_time, 3)))

    return {instance_id: {'weights': weights, 'epoch_times': epoch_times, 'run_time': run_time}}


def main():
    results = {}

    def collect_result(result):
        results.update(result)

    start = time.time()
    pool = mp.Pool()

    for method_id in range(len(METHODS)):
        for instance_id in range(1, 200, 2):
            pool.apply_async(solve,
                             args=(method_id, instance_id), kwds={'max_runtime': 60},
                             callback=collect_result)

        pool.close()
        pool.join()

        method_name = METHODS[method_id].__name__
        with open('results/{}.json'.format(method_name), 'w') as f:
            json.dump(results, f)

    print(time.time() - start)


if __name__ == '__main__':
    main()
