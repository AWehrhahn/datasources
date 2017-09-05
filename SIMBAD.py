import hashlib
import logging
import os
from os.path import isfile

import astropy.io.votable as votable

from astropy.table import Table
from astroquery.simbad import Simbad

from DataSources import Cache

# Load Data from SIMBAD DataBase


def getNotes(starID):
    # WIP
    # http://simbad.u-strasbg.fr/simbad/sim-script?script=format object "%IDLIST(1) | %COO(A D)"\nhd1\nhd2
    url = r"http://simbad.u-strasbg.fr/simbad/sim-script?script=format"
    logging.warning('getNotes() does not currently do anything')


def VOTableFromSimbad(stars, fields):
    custom = Simbad()
    if len(fields) > 0:
        if 'main_id' in fields:
            fields.remove('main_id')
        custom.remove_votable_fields('coordinates')
        custom.add_votable_fields(*fields)
    # Some fields might be binary, need to be converted
    # This is done in DataFrameFromSimbad
    return custom.query_object(makeStrList(stars, '\n', False))

# Convenience function


def DataFrameFromSimbad(stars, fields):
    vt = VOTableFromSimbad(stars, fields)
    df = vt.to_pandas()
    df = df.applymap(lambda s: s.decode('utf-8') if type(s) == bytes else s)
    return df

# list the contents of a list, with custom seperator


def makeStrList(elements, seperator=', ', removeLastSeperator=True):
    txt = (('%s' + seperator) * len(elements)) % tuple(elements)
    if removeLastSeperator:
        txt = txt[:-len(seperator)]
    return txt

# Manages the data retrieval and file cashe


# ASCII equals Pandas Dataframe
def getFromSimbad(stars, fields, format, folder='./DATA/SIMBAD/', UseCache=True):
    logging.info('Loading SIMBAD data')
    # this needs working internet if the files arent there
    if type(stars) == str:  # make sure stars is a list
        stars = (stars,)

    cache = Cache.Cache(folder, stars, fields, format)
    data = cache.load() if UseCache else None

    if data is not None:
        return data
    else:
        # if not get data online
        logging.info('Retrieving SIMBAD data online')
        df = DataFrameFromSimbad(stars, fields)
        cache.save(df)

    # return desired Format
    if format == 'Pandas' or format == 'DataFrame':
        return df
    elif format == 'VOTable':
        return votable.from_table(Table.from_pandas(df))
    elif format == 'APTable':  # Astropy.Table
        return Table.from_pandas(df)
    else:
        raise ValueError('%s is not a valid format' % format)
