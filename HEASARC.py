#!/usr/bin/env python
# encoding: utf-8

"""
Created by Victor Doroshenko on 2011-01-21.
Copyright (c) 2011 IAAT, Tuebingen, Germany. All rights reserved.
Feel free to contribute to the project.
Adapted to Python 3.5 by Ansgar Wehrhahn
"""

import urllib
import ssl
import socket
from astropy.io import votable as VOTable
import sys
import re
import hashlib
import Cache
import io
import os
import logging
import pandas as pd
import tempfile
from numpy import vectorize, nan, where, isnan
from numpy import array, float64
# to do: sanitize input (i.e.  make switches for complicated args) 'Galactic:
# LII BII'
class heasarc(object):
    """Representation of heasarc query"""
    def __init__(self, table, position, radius=30, resolver="SIMBAD",time="",max_results=100,
    fields="Standard", order_by="", params="", coordsys='equatorial', equinox="2000", gifsize=0, host='heasarc', convert_fields=True,print_offset=False,timeout=30):
        socket.setdefaulttimeout(timeout)
        self.table = str(table)
        self.position = str(position)
        self.radius = radius
        self.resolver = str(resolver)
        self.time = time
        self.max_results = int(max_results)
        self.gifsize = gifsize
        self.equinox = equinox
        self.order = order_by.lower()
        self.params = params
        self.convert_fields = convert_fields
        self.print_offset = print_offset
        self.fields = fields

        if type(fields) != str:
            self.fields = makeStrList(fields)
            
        if host == 'heasarc':
            # www.isdc.unige.ch/browse/w3query.pl
            self.host = 'heasarc.gsfc.nasa.gov/db-perl/W3Browse'
        elif host == 'isdc':
            self.host = 'www.isdc.unige.ch/browse'
        if coordsys.lower() == 'equatorial':
            self.coordsys = "Equatorial: R.A. Dec"
        else:
            self.coordsys = "Galactic: LII BII"
        if self.fields.lower() == 'standard' or self.fields.lower() == 'all':
            self.fields = self.fields.capitalize() # do varon reconstruction
            addvaron = False
        else:
            self.fields = self.fields.lower()
            addvaron = True
        querydic = {"Format":"Text",\
                  "Action":"Query",\
                  "Coordinates":self.coordsys,\
                  "Equinox":self.equinox,\
                  "Radius":self.radius,\
                  "NR":self.resolver,\
                  "fields": self.fields,\
                  "Position":self.position,\
                  "ResultMax": self.max_results,\
                  "Time":""}
                  #"Format":"VOTable"}       # VOTable does not currently work, as the connection fails
        querydic['tablehead'] = "name%3dBATCHRETRIEVALCATALOG%5f2%2e0 " + str(self.table)
        if self.order:
            querydic['sortvar'] = self.order
        if self.params:
            paramlist = self.params.split(',')
            for par in paramlist:
                entry = re.findall('(.*?)([><=\*].*)',par)[0]
                querydic['bparam_' + entry[0].strip()] = entry[1].strip().replace('=','')
        self.url = 'https://' + self.host + '/w3query.pl?' + urllib.parse.urlencode(querydic)
        if addvaron:
            self.url+='&varon=' + '&varon=+'.join(self.fields.replace(',',' ').replace(';',' ').split())

        f = urllib.request.urlopen(self.url)
        self.text = f.read().decode('utf-8').strip()
        f.close()

#list the contents of a list, with custom seperator
def makeStrList(elements,seperator = ', ',removeLastSeperator = True):
    txt = (('%s' + seperator) * len(elements)) % tuple(elements)
    if removeLastSeperator: txt = txt[:-len(seperator)]
    return txt

def getData(dataset,catalogue='exoplanodb',fields=('name','star_name','number_planets'),folder='./DATA/HEARSEC', UseCache=True):
    logging.info('Loading HEARSEC data')

    cache = Cache.Cache(folder,dataset,catalogue,fields)
    data = cache.load() if UseCache else None

    if data is not None: 
        return data

    logging.info('Getting data from HEARSEC')
    df = pd.DataFrame(index=range(len(dataset)),columns = fields)

    for i,source in zip(range(len(dataset)),dataset):
        obsids = heasarc(catalogue,source,fields=fields)
        text = obsids.text
        lines = text.split('\n')
        content = lines[0] + '\n' + lines[1]
        #if not empty
        if not lines[1] == "":
            df_temp = pd.read_table(io.StringIO(content),delimiter = '|', usecols=[i for i in range(len(fields))])
            print(df_temp.head())
            df.iloc[i] = df_temp.iloc[0]

    df = df.applymap(lambda s: s.decode('utf-8') if type(s) == bytes else s)
    #print(df.head())

    cache.save(df)
    return df