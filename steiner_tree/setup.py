import io
import os
import sys
import zipfile

import networkx as nx
import requests


def get_instances():
    """
    Download and extract the public instances
    """
    url = "http://www.lamsade.dauphine.fr/~sikora/pace18/heuristic.zip"
    f = io.BytesIO()

    print("Downloading the public instances")

    response = requests.get(url, stream=True)
    total_length = response.headers.get('content-length')

    if total_length is None:  # no content length header
        f.write(response.content)
    else:
        dl = 0
        total_length = int(total_length)
        for data in response.iter_content(chunk_size=4096):
            f.write(data)

            dl += len(data)
            percentage = 100 * dl / total_length
            done = int(percentage / 2)

            sys.stdout.write("\r[{}{}] {}%".format(
                '=' * done, ' ' * (50 - done), round(percentage, 2))
            )
            sys.stdout.flush()

    print('\nExtracting...')

    with zipfile.ZipFile(f, 'r') as zip_ref:
        zip_ref.extractall()

    print('Complete extracting\n')


def compute_starting_solutions():
    """
    Precompute the starting solutions
    """
    from .utils import parse_graph, find_starting_solution

    for algo in ('dnh', 'mst'):
        print('Computing the starting solutions using {}'.format(algo.upper()))

        directory = 'results/starting_solutions/{}'.format(algo)
        if not os.path.exists(directory):
            os.makedirs(directory)

        for i in range(1, 200, 2):
            g, terminals = parse_graph(i)
            s = find_starting_solution(g, terminals, algo=algo)

            nx.write_gpickle(s, '{}/{}.gpickle'.format(directory, i))

            percentage = (i + 1) // 2
            done = int(percentage / 2)
            sys.stdout.write("\r[{}{}] {}/100".format(
                '=' * done, ' ' * (50 - done), percentage)
            )
            sys.stdout.flush()

        print()


def setup():
    get_instances()
    compute_starting_solutions()


if __name__ == '__main__':
    setup()
    print('Setup complete.')
