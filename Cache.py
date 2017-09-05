import hashlib
import os
import pandas as pd
import logging
import pickle

class Cache:
    def __init__(self,folder = './',*info):
        self.folder = folder
        self.filename = self.createFilename(folder,info)

    def createFilename(self,folder,*info):
        #Create a file cashe to avoid using SIMBAD to much
        #hash stars and fields and format, to use as unique filename
        string = (str(info)).encode()
        filename = hashlib.sha224(string).hexdigest() + '.dat'
        return os.path.join(folder,filename)

    def load(self):
        if os.path.isfile(self.filename):
            logging.info('Cached File found: %s' %  self.filename)
            with open(self.filename,'rb') as f:
                return pickle.load(f)
            #return pd.read_pickle(self.filename)
        return None

    def save(self,data):
        if not os.path.isdir(self.folder):
            os.makedirs(self.folder)
        with open(self.filename,'wb') as f:
            pickle.dump(data,f,pickle.HIGHEST_PROTOCOL)
            logging.info('Data cached at: %s' % self.filename)
        #data.to_pickle(self.filename)