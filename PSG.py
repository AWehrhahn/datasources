"""
Interface for the
Planetary Spectrum Generator
by NASA Goddard
https://psg.gsfc.nasa.gov/index.php

author: Ansgar Wehrhahn
"""

import inspect
from os.path import join, dirname
from io import BytesIO, StringIO
from urllib.parse import urlencode

import pycurl
import pandas as pd

from Config import config
try:
    import Cache
except ModuleNotFoundError:
    from DataSources import Cache

class PSG:
    """ interface for the Planetary Spectrum Generator Webservice of NASA Goddard """
    def __init__(self, config_file=None):
        if config_file is not None:
            self.config_filename = config_file
        else:
            this_dir = inspect.stack()[0][1]  # Directory of this file
            this_dir = dirname(this_dir)
            self.config_filename = join(this_dir, 'psg_config.xml')

        self.url = 'https://psg.gsfc.nasa.gov/api.php'
        self.config = config.load_config()
        self.cache_folder = self.config['path_cache']

    def curl(self, UseCache=True):
        """
        retrieve data as defined in the config file
        returns a string
        """
        # help: https://psg.gsfc.nasa.gov/helpapi.php
        # curl --data-urlencode file@config.txt https://psg.gsfc.nasa.gov/api.php
        cache = Cache.Cache(self.cache_folder, open(self.config_filename).read())
        try:
            data = cache.load() if UseCache else None
        except IOError:
            data = None

        if data is None:
            print('Sending request to Planetary Spectrum Generator')
            # prepare data
            post_data = open(self.config_filename, 'rb').read()
            postfields = urlencode({'file': post_data})

            # prepare curl
            buffer = BytesIO()
            c = pycurl.Curl()
            c.setopt(c.URL, self.url)
            c.setopt(c.BUFFERSIZE, 102400)
            c.setopt(c.NOPROGRESS, 1)
            c.setopt(c.POSTFIELDS, postfields)
            c.setopt(c.WRITEDATA, buffer)
            
            # start curl
            c.perform()
            c.close()

            # decode data
            data = buffer.getvalue().decode('iso-8859-1')
            # save data as cache
            if UseCache:
                cache.save(data)
            print('... Done')
        else:
            print('Using cached PSG data')

        return data

    def __parse__(self, line):
        """ parse a simplified xml line """
        if not isinstance(line, list):
            line = [line, ]

        for l in line:
            label, value = l.split('>', 1)
            label = label[1:] #cut away the leading <
            value = value[:-1] #cut away the last \n newline
            yield label, value

    def __deparse__(self, key_value):
        """ convert key value pair into simple xml """
        if not isinstance(key_value, dict):
            key_value = {key_value[0]: key_value[1], }

        for key, value in key_value.items():
            yield '<{key}>{value}\n'.format(key=key, value=value)

    def change_config(self, kwargs):
        """ Change values in psg config file """
        # Read existing config file
        with open(self.config_filename, 'r') as f:
            content = f.readlines()

        # parse lines into dictionary
        content = dict(self.__parse__(content))
        #content = {self.__parse__(line)[0]: self.__parse__(line)[1] for line in content}
        
        # apply changes to dictionary
        for key, value in kwargs.items():
            if key in content.keys():
                content[key] = value

        # deparse back into list of strings
        content = self.__deparse__(content)

        # write changes to file
        with open(self.config_filename, 'w') as f:
            f.writelines(content)

    def get_pandas(self, UseCache=True):
        """ retrieve the data as a pandas dataframe """
        data = self.curl(UseCache=UseCache)
        # Parse header to get names
        header = [line for line in data.split('\n') if line.startswith('#')]
        names = header[-1][1:].split()

        io_data = StringIO(data)
        df = pd.read_table(io_data, delim_whitespace=True, header=None, names=names, comment='#')
        return df

if __name__ == '__main__':
    psg = PSG()
    psg.change_config({'GENERATOR-RANGE1': 0.5, 'GENERATOR-RANGE2': 0.55})
    body = psg.curl()
    df = psg.get_pandas()
    print(df.head())
    pass