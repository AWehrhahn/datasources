import hashlib
import logging
import os
import pickle

import pandas as pd


class Cache:
    def __init__(self,folder='~/.cache',*info):
        self.folder = os.path.expanduser(folder)
        self.filename = self.createFilename(self.folder,info)

    def createFilename(self,folder,*info):
        #Create a file cashe to avoid using SIMBAD to much
        #hash stars and fields and format, to use as unique filename
        string = (str(info)).encode()
        filename = hashlib.sha224(string).hexdigest() + '.dat'
        return os.path.join(folder,filename)

    def load(self):
        if os.path.isfile(self.filename):
            logging.info('Cached file found: %s' %  self.filename)
            with open(self.filename,'rb') as f:
                return pickle.load(f)
            #return pd.read_pickle(self.filename)
        logging.info('No cached file found')
        raise IOError('File not found')

    def save(self,data):
        if not os.path.isdir(self.folder):
            os.makedirs(self.folder)
        with open(self.filename,'wb') as f:
            pickle.dump(data,f,pickle.HIGHEST_PROTOCOL)
            logging.info('Data cached at: %s' % self.filename)
        #data.to_pickle(self.filename)
