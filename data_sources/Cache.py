import hashlib
import logging
import os
import pickle
from functools import wraps

class Cache:
    def __init__(self,folder='~/.cache',*info):
        self.folder = os.path.expanduser(folder)
        self.filename = self.createFilename(self.folder, info)

    def createFilename(self,folder,*info):
        #Create a file cashe to avoid using SIMBAD to much
        #hash stars and fields and format, to use as unique filename
        string = (str(info)).encode()
        filename = hashlib.sha224(string).hexdigest() + '.dat'
        return os.path.join(folder,filename)

    def load(self):
        try:
            with open(self.filename,'rb') as f:
                return pickle.load(f)
            logging.info('Cached file found: %s' %  self.filename)
        except FileNotFoundError, ValueError:
            # The load will fail with a ValueError if the pickle version changed
            logging.info('No cached file found')
            raise FileNotFoundError('File not found')

    def save(self,data):
        if not os.path.isdir(self.folder):
            os.makedirs(self.folder)
        with open(self.filename,'wb') as f:
            pickle.dump(data,f,pickle.HIGHEST_PROTOCOL)
            logging.info('Data cached at: %s' % self.filename)
        #data.to_pickle(self.filename)

class UseCache:
    def __init__(self, folder='~/.cache'):
        self.folder = folder

    def __call__(self, func):

        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = Cache(self.folder, *args, *kwargs.values())
            try:
                data = cache.load()
            except FileNotFoundError:
                data = func(*args, **kwargs)
                cache.save(data)
            finally:
                return data

        return wrapper
