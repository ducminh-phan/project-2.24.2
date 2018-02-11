# Project MPRI 2.24.2

This repository is for the project of the course MPRI 2.24.2: Solving Optimization Problems with Search Heuristics. The goal is to compute a Steiner tree of a graph using local search. The instances are from the [PACE Challenge 2018](https://pacechallenge.wordpress.com/pace-2018/).

The implementation follows the ideas from the paper Fast local search for the Steiner problem in graphs by Eduardo Uchoa and Renato F. Werneck [[pdf](https://renatowerneck.files.wordpress.com/2016/06/uw12-steiner-ls.pdf)].

## Setup

1. You will need Python 3.5
2. Clone this repository
3. Install the packages using the command `pip3 install -r requirements.txt`
4. Run the setup using the command `python3 -m steiner_tree.setup`. This will download the public instances from the contest and precompute the starting solutions.

### Platform
The timeout function uses `signal.SIGALRM`, which is not available on Windows. However, on Windows, we can use the Windows Subsystem for Linux, which is included with Windows 10 version 1607 and later.

## Running

The solver can be run via CLI: `python3 -m steiner_tree [OPTIONS]`

### Options

```
  -h, --help            show this help message and exit
  -s {dnh,mst}, --start {dnh,mst}
                        The choice of algorithm to find the starting solution.
                        Default: 'dnh'.
  -m {kv,sv}, --method {kv,sv}
                        The neighborhood type to use in the local search. The
                        options are corresponding to key vertices and steiner
                        vertices. Default: 'kv'.
  -n, --no-early-stop   Do not use early stopping by default in the local
                        search.
  -a, --all             Solve all 100 instances instead of 25 small instances
                        by default. Cannot be used together with the option
                        --id.
  -t TIMEOUT, --timeout TIMEOUT
                        The time limit to solve for an instance, in seconds.
                        Set this to 0 to remove the timeout. Default: 3600.
  -i ID [ID ...], --id ID [ID ...]
                        Solve the instances with the id provided as a list of
                        space-separated integers. Cannot be used together with
                        the option --all.
  --save                Save the obtained solutions into a folder
                        corresponding to the options provided.
  -v, --verbose         Turn on verbosity mode. Can be set if and only if a
                        single instance id is provided with --id.
```
