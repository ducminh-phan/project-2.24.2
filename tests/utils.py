import os

my_path = os.path.dirname(os.path.abspath(__file__))


def get_path(rel_path):
    """
    Get the absolute path from relative path
    """
    return os.path.abspath(
        os.path.join(my_path, rel_path)
    )


small_instances = (31, 51, 71, 29)
