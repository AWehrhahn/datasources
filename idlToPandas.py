#!/usr/bin/env python

"""
Created on 2014-06-01T20:15:40
__author__ = "Matt Giguere (github: @mattgiguere)"
__maintainer__ = "Matt Giguere"
__email__ = "matthew.giguere@yale.edu"
__status__ = " Production"
__version__ = '0.1.0'

Edits by Ansgar Wehrhahn
I only did minor changes to adapt to python 3.x
And cut a lot of stuff I dont need
"""

import pandas as pd
import logging
from scipy.io.idl import readsav
import Cache


#Load a IDL .sav and put into a pandas dataframe

def idlToPandas(fileName, keyValue=None,folder = './DATA/IDL/', UseCache = True):
    """PURPOSE: To restore an IDL strcture contained
    within an IDL save file and add it to a pandas
    data frame."""

    cache = Cache.Cache(folder,fileName,keyValue)
    data = cache.load() if UseCache else None
    
    if data is not None: 
        return data

    logging.info('Loading IDL file: %s' % fileName)
    idlSavedVars = readsav(fileName)

    #check if the keyValue passed in is actually an index
    #rather than the keyValue name:
    if keyValue is None:
        keys = list(idlSavedVars.keys())
        keyValue = keys[0]

    struct = idlSavedVars[keyValue]
    tags = []
    for tag in struct.dtype.descr:
        tags.append(tag[0][0])

    #now take care of potential big-endian/little-endian issues
    dt = struct.dtype
    dt = dt.descr
    for i in range(len(dt)):
        if(dt[i][1][0] == '>' or dt[i][1][0] == '<'):
            dt[i] = (dt[i][0], dt[i][1][1:])
    struct = struct.astype(dt)

    pdf = pd.DataFrame.from_records(struct, columns=tags)

    cache.save(pdf)

    return pdf

