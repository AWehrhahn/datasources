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
import numpy as np

try:
    import config
    import Cache
except ImportError:
    from DataSources import Cache
    from DataSources import config

class PSG:
    """ interface for the Planetary Spectrum Generator Webservice of NASA Goddard """
    def __init__(self, config_file=None):
        if config_file is not None:
            self.config_filename = config_file
        else:
            this_dir = inspect.stack()[0][1]  # Directory of this file
            this_dir = dirname(this_dir)
            self.config_filename = join(this_dir, 'psg_config.txt')

        self.url = 'https://psg.gsfc.nasa.gov/api.php'
        self.config = config.load_config()
        self.cache_folder = self.config['path_cache']

    def curl(self, UseCache=True, **kwargs):
        """
        retrieve data as defined in the config file
        returns a string
        """
        # type = 
        # rad - radiance 
        # noi - noise 
        # trn - planetary transmittance
        # atm - planetary flux
        # str - stellar transmittance 
        # tel - tellurics 
        # srf - surface reflectance 
        # cfg - configuration file 
        # all - everything

        # help: https://psg.gsfc.nasa.gov/helpapi.php
        # curl --data-urlencode file@config.txt https://psg.gsfc.nasa.gov/api.php

        # curl -d type=trn -d whdr=n --data-urlencode file@config.txt https://psg.gsfc.nasa.gov/api.php
        cache = Cache.Cache(self.cache_folder, open(self.config_filename).read(), kwargs)
        try:
            data = cache.load() if UseCache else None
        except IOError:
            data = None

        if data is None:
            print('Sending request to Planetary Spectrum Generator')
            # prepare data
            post_data = open(self.config_filename, 'rb').read()
            #postfields = {'file': post_data}
            kwargs['file'] = post_data
            postfields = urlencode(kwargs)

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

    def get_data_in_range(self, wl_low, wl_high, n_parts, unit='um', **kwargs):
        """ Use several curl request to get data for a larger wavelength spectrum """
        #TODO automatically decide how many parts are required
        self.change_config({'GENERATOR-RANGEUNIT': unit})

        wl_parts = np.linspace(wl_low, wl_high, n_parts, endpoint=False)
        wl_delta = (wl_high - wl_low)/n_parts

        data = [None for i in range(n_parts)]
        for i, part in enumerate(wl_parts):
            # Change Wavelength range
            self.change_config({'GENERATOR-RANGE1': part, 'GENERATOR-RANGE2': part+wl_delta})
            # Get Data
            data[i] = self.get_pandas(**kwargs)

        # Combine Data
        return pd.concat(data)

    def get_pandas(self, UseCache=True, **kwargs):
        """ retrieve the data as a pandas dataframe """
        data = self.curl(UseCache=UseCache, **kwargs)
        # Parse header to get names
        header = [line for line in data.split('\n') if line.startswith('#')]
        names = header[-1][1:].split()

        io_data = StringIO(data)
        df = pd.read_table(io_data, delim_whitespace=True, header=None, names=names, comment='#')
        return df

if __name__ == '__main__':
    psg = PSG()
    #psg.change_config({'GENERATOR-RANGE1': 0.5, 'GENERATOR-RANGE2': 0.55})
    df = psg.get_data_in_range(0.6, 1.0, 50)
    print(df.head())
    df.to_csv('test.csv', index=False)
    pass
