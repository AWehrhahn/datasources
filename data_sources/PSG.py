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

#TODO use wget instead of pycurl
# or urllib?
import pycurl
import pandas as pd
import numpy as np

from . import Cache
from . import config

def round_to(n, precision, limits=None, round_direction=None):
    """ Round to the closest value within the given precison or the next limit

    Parameters:
    ----------
    n : {float}
        value to round
    precision : {float}
        precision of the rounding, e.g. 0.5
    limits : {tuple(min, max), None}, optional
        Limits the results to min, max, or no limits if None (the default is None)

    Returns
    -------
    rounded : float
        rounded value
    """
    correction = 0.5 if n >= 0 else -0.5
    if round_direction is None:
        value = int(n / precision + correction) * precision
    elif round_direction == "up":
        value = int(np.ceil(n / precision)) * precision
    elif round_direction == "down":
        value = int(np.floor(n / precision)) * precision
    else:
        raise ValueError("round_direction should be one of up, down, None")

    if limits is None:
        return value

    if value >= limits[0] and value <= limits[1]:
        return value

    if value < limits[0]:
        return limits[0]

    if value > limits[1]:
        return limits[1]

class PSGConfig:
    def __init__(self, filename):
        self.filename = filename
        self.data = PSGConfig._load(filename)

    def __getitem__(self, key):
        key = key.upper()
        return self.data[key]

    def __setitem__(self, key, value):
        key = key.upper()
        self.data[key] = value

    def __str__(self):
        lines = [f"<{key}>{value}\n" for key, value in self.data.items()]
        text = "".join(lines)
        return text

    @staticmethod
    def _load(filename):
        data = {}
        with open(filename) as f:
            for line in f:
                i = line.find(">")
                key = line[1:i]
                value = line[i+1:-1]
                data[key] = value
        return data

    @staticmethod
    def _save(filename, data):
        with open(filename, "w") as f:
            for key, value in data.items():
                line = f"<{key}>{value}\n"
                f.write(line)
    
    @staticmethod
    def load(filename):
        return PSGConfig(filename)

    def save(self, filename=None):
        if filename is None:
            filename = self.filename
        PSGConfig._save(filename, self.data)
        
    def asByteString(self):
        text = str(self)
        byte = text.encode()
        return byte

class PSG:
    """ interface for the Planetary Spectrum Generator Webservice of NASA Goddard """
    def __init__(self, config_file=None):
        if config_file is None:
            this_dir = dirname(__file__)
            config_file = join(this_dir, 'psg_config.txt')

        self.psg_config = PSGConfig(config_file)
        self.url = 'https://psg.gsfc.nasa.gov/api.php'
        self.config = config.load_config()
        self.cache_folder = self.config['path_cache']

    def _curl(self, **kwargs):
        post_data = self.psg_config.asByteString()
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
        return data

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
        cache = Cache.Cache(self.cache_folder, str(self.psg_config), kwargs)
        try:
            data = cache.load() if UseCache else None
        except FileNotFoundError:
            data = None

        if data is None:
            print('Sending request to Planetary Spectrum Generator')
            data = None
            for _ in range(10):
                try:
                    data = self._curl(**kwargs)
                    break
                except:
                    # Try again
                    pass
            if data is None:
                raise RuntimeError("Could not load data from server")
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
        # apply changes to dictionary
        for key, value in kwargs.items():
            self.psg_config[key] = value
        self.psg_config.save()

    # make the wavelength steps constants independant of the number of parts
    # so that the cache is reusable even if another wavelength range is picked
    # number of wavelength points should be constant per request
    # one hundred parts per 0.01 micron, i.e. 100 angstrom
    # have a global reference wavelength, on which all requests are based?
    def get_data_in_range(self, wl_low, wl_high, unit='An', **kwargs):
        """ Use several curl request to get data for a larger wavelength spectrum """
        #TODO automatically decide how many parts are required
        self.change_config({'GENERATOR-RANGEUNIT': unit})

        # Assuming its in Angstrom
        # And resolution is about 100 000
        wl_base = 5000
        wl_step = 100

        # round wl_low and wl_high to the next point in 100 steps from wave_base
        wl_low = wl_base + round_to(wl_low - wl_base, wl_step, round_direction="down")
        wl_high = wl_base + round_to(wl_high - wl_base, wl_step, round_direction="up")
        
        # Determine the steps to do
        n_steps = (wl_high - wl_low) / wl_step
        n_steps = int(np.ceil(n_steps)) + 1

        wl_parts = [wl_low + i * wl_step for i in range(n_steps)]

        data = [None for i in range(n_steps)]
        for i, part in enumerate(wl_parts):
            # Change Wavelength range
            self.change_config({'GENERATOR-RANGE1': part, 'GENERATOR-RANGE2': part + wl_step})
            # Get Data
            data[i] = self.get_pandas(**kwargs)

        # Combine Data
        return pd.concat(data, sort=True)

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
