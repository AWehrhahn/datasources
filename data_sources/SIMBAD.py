"""
Load Data from SIMBAD DataBase
"""
import logging

import astropy.io.votable as votable
from astropy.table import Table
from astroquery.simbad import Simbad

from . import Cache


def getNotes(starID):
    """
    WIP
    http://simbad.u-strasbg.fr/simbad/sim-script?script=format object "%IDLIST(1) | %COO(A D)"\nhd1\nhd2
    """
    #url = r"http://simbad.u-strasbg.fr/simbad/sim-script?script=format"
    logging.warning('getNotes() does not currently do anything')


def VOTableFromSimbad(stars, fields):
    """ Load VOTable from SIMBAD """
    custom = Simbad()
    fields = [f.lower() for f in fields]
    if len(fields) > 0:
        if 'main_id' in fields:
            fields.remove('main_id')
        custom.remove_votable_fields('coordinates')
        custom.add_votable_fields(*fields)
    # Some fields might be binary, need to be converted
    # This is done in DataFrameFromSimbad
    return custom.query_object(makeStrList(stars, '\n', False))


def DataFrameFromSimbad(stars, fields):
    """ Load DataFrama from SIMBAD """
    vt = VOTableFromSimbad(stars, fields)
    df = vt.to_pandas()
    df = df.applymap(lambda s: s.decode('utf-8') if type(s) == bytes else s)
    return df


def makeStrList(elements, seperator=', ', removeLastSeperator=True):
    """ list the contents of a list, with custom seperator """
    txt = (('%s' + seperator) * len(elements)) % tuple(elements)
    if removeLastSeperator:
        txt = txt[:-len(seperator)]
    return txt


def Query_ID(name, cache_folder='./DATA/SIMBAD/', UseCache=True):
    """ query ids only """
    cache = Cache.Cache(cache_folder, name, 'id_query')
    try:
        data = cache.load() if UseCache else None
    except IOError:
        data = None

    if data is not None:
        return data
    data = Simbad.query_objectids(name)
    if UseCache:
        cache.save(data)

    return data


def getFromSimbad(stars, fields, table_format='pandas', cache_folder='./DATA/SIMBAD/', UseCache=True):
    """
    Manages the data retrieval and file cashe
    """
    logging.info('Loading SIMBAD data')
    # this needs working internet if the files arent there
    if isinstance(stars, str):  # make sure stars is a list
        stars = (stars,)

    cache = Cache.Cache(cache_folder, stars, fields, format)
    try:
        data = cache.load() if UseCache else None
    except IOError:
        data = None

    if data is not None:
        return data
    else:
        # if not get data online
        logging.info('Retrieving SIMBAD data online')
        df = DataFrameFromSimbad(stars, fields)
        if UseCache:
            cache.save(df)

    # return desired Format
    table_format = table_format.lower()
    if table_format == 'pandas' or table_format == 'dataframe':
        return df
    elif table_format == 'votable':
        return votable.from_table(Table.from_pandas(df))
    elif table_format == 'aptable':  # Astropy.Table
        return Table.from_pandas(df)
    else:
        raise ValueError('%s is not a valid format' % table_format)
