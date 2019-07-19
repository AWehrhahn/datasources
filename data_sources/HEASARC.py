#!/usr/bin/env python
# encoding: utf-8

"""
Created by Victor Doroshenko on 2011-01-21.
Copyright (c) 2011 IAAT, Tuebingen, Germany. All rights reserved.
Feel free to contribute to the project.
Adapted to Python 3.5 by Ansgar Wehrhahn
"""

import io
import logging
import re
import socket
import urllib

import pandas as pd

from . import Cache

# to do: sanitize input (i.e.  make switches for complicated args) 'Galactic:
# LII BII'


class heasarc(object):
    """Representation of heasarc query"""

    def __init__(self, table, query, radius=1, resolver="SIMBAD", time="", max_results=100,
                 fields="Standard", order_by="", params="", coordsys='equatorial', equinox="2000", gifsize=0, host='heasarc', convert_fields=True, print_offset=False, timeout=30):
        socket.setdefaulttimeout(timeout)
        self.table = str(table)
        self.query = str(query)
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

        if not isinstance(fields, str):
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
            self.fields = self.fields.capitalize()  # do varon reconstruction
            addvaron = False
        else:
            self.fields = self.fields.lower()
            addvaron = True
        querydic = {"Format": "Text",
                    "Action": "Query",
                    "Coordinates": self.coordsys,
                    "Equinox": self.equinox,
                    "Radius": self.radius,
                    "NR": self.resolver,
                    "fields": self.fields,
                    "ResultMax": self.max_results,
                    "Time": ""}

        field,val = query.split('==')
        querydic[field] = val

        #"Format":"VOTable"}       # VOTable does not currently work, as the connection fails
        querydic['tablehead'] = "name%3dBATCHRETRIEVALCATALOG%5f2%2e0 " + \
            str(self.table)
        if self.order:
            querydic['sortvar'] = self.order
        if self.params:
            paramlist = self.params.split(',')
            for par in paramlist:
                entry = re.findall('(.*?)([><=\*].*)', par)[0]
                querydic['bparam_' +
                         entry[0].strip()] = entry[1].strip().replace('=', '')
        self.url = 'https://' + self.host + \
            '/w3query.pl?' + urllib.parse.urlencode(querydic)
        if addvaron:
            self.url += '&varon=' + \
                '&varon=+'.join(self.fields.replace(',',
                                                    ' ').replace(';', ' ').split())

        f = urllib.request.urlopen(self.url)
        self.text = f.read().decode('utf-8').strip()
        f.close()

# list the contents of a list, with custom seperator


def makeStrList(elements, seperator=', ', removeLastSeperator=True):
    txt = (('%s' + seperator) * len(elements)) % tuple(elements)
    if removeLastSeperator:
        txt = txt[:-len(seperator)]
    return txt


def getData(dataset, catalogue='exoplanodb', fields=('name', 'star_name', 'number_planets'), folder='./DATA/HEARSEC', UseCache=True, maxresults=100):
    """
    dataset examples: (no blanks!) 
        - Position==eps_Eri
        - TRANSIT==1
    """
    logging.info('Loading HEARSEC data')
    if isinstance(dataset, str):
        dataset = (dataset, )

    cache = Cache.Cache(folder, dataset, catalogue, fields, maxresults)
    try:
        data = cache.load() if UseCache else None
    except IOError:
        data = None

    if data is not None:
        return data

    logging.info('Getting data from HEARSEC')
    df = pd.DataFrame(index=range(len(dataset)), columns=fields)

    for source in dataset:
        obsids = heasarc(catalogue, source, fields=fields, max_results=maxresults)
        text = obsids.text
        lines = text.split('\n')
        endline = lines.index('')
        lines = lines[:endline]
        temp = ('{}\n' * len(lines))
        names = [l.strip() for l in lines[0].split('|')]
        lines = str.format(temp,*lines)
        df = pd.read_csv(io.StringIO(lines), delimiter='|', usecols=[i for i in range(len(fields))], names=names, header=0)

    df = df.applymap(lambda s: s.decode('utf-8')
                     if isinstance(s, bytes) else s)
    # print(df.head())

    cache.save(df)
    return df
