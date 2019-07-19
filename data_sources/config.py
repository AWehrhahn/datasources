"""
Author: Ansgar Wehrhahn
Load configuration file from current working directory
"""

import os
import sys
import yaml
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    print('LibYaml not installed, ')
    from yaml import Loader, Dumper

if sys.version_info[0] == 2:
    print('WARNING: This program was developed for Python 3, but Python 2 is beeing used. Errors may occur and Calculations might be wrong.')


def load_yaml(fname):
    """ load json data from file with given filename """
    with open(fname, 'r') as fp:
        return yaml.load(fp, Loader=Loader)
    raise IOError


def load_config(filename=None):
    """ Load configuration from file """
    if filename is None:
        filename = os.path.dirname(__file__)
        filename = os.path.join(filename, "config.yaml")
    c = load_yaml(filename)

    for k, v in c.items():
        c[k] = os.path.expanduser(v)
    return c
