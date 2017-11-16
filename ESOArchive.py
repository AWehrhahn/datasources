"""
Request meta data from ESO Archive service
"""
import io

import pandas as pd
import requests
from DataSources import Cache

# http://archive.eso.org/cms/faq/how-do-i-programmatically-access-the-archive.html
# http://archive.eso.org/cms/faq/how-do-i-submit-a-request-to-the-archive-programmatically.html
# http://archive.eso.org/cms/faq/how-do-i-retrieve-download-the-data-programmatically.html

# http://archive.eso.org/wdb/wdb/eso/eso_archive_main/query?wdbo=csv%2fdisplay&max_rows_returned=200&instrument=&tab_object=on&target=HD%20209458&
# resolver=simbad&ra=&dec=&box=00%2010%2000%c2%b0_or_hour=hours&tab_target_coord=on&format=SexaHour&wdb_input_file=&night=&stime=&starttime=12&
# etime=&endtime=12&tab_prog_id=on&prog_id=&gto=&pi_coi=&obs_mode=&title=&spectrum[]=HARPS&tab_dp_cat=on&tab_dp_type=on&dp_type=&dp_type_user=&
# tab_dp_tech=on&dp_tech=&dp_tech_user=&tab_dp_id=on&dp_id=&origfile=&tab_rel_date=on&rel_date=&obs_name=&ob_id=&tab_tpl_start=on&tpl_start=&
# tab_tpl_id=on&tpl_id=&tab_exptime=on&exptime=&tab_filter_path=on&filter_path=&gris_path=&grat_path=&slit_path=&
# tab_instrument=on&add=((ins_id%20like%20%27HARPS%25%27))&tab_tel_airm_start=on&tab_stat_instrument=on&tab_ambient=on&tab_stat_exptime=on&tab_HDR=on&tab_mjd_obs=on&
# aladin_colour=aladin_instrument&tab_stat_plot=on&order=&
# wdbo: output format
# target=HD%20209458
# tab_instrument=on&add=((ins_id%20like%20%27HARPS%25%27))

# star = 'HD 209458'
# instrument = 'HARPS'


def from_ESO_Archive(star, instrument, cache_folder='/DATA/Cache/', UseCache=True):
    """ fetch data from ESO Archive """

    cache = Cache.Cache(cache_folder, star, instrument)
    if UseCache:
        try:
            data = cache.load()
            if data is not None:
                data['OBJECT'] = [star for i in range(len(data['OBJECT']))]
            print('Successfully loaded data for Star ', star)
            return data
        except IOError:
            df = None
    else:
        df = None

    host = "http://archive.eso.org/wdb/wdb/eso/eso_archive_main/query"
    params = {
        'wdbo': 'csv',
        'target': star,
        'resolver': 'simbad',
        'spectrum[]': instrument,
        'add': "((ins_id like '{}%'))".format(instrument)
    }
    n_retries = 10
    for i in range(n_retries):
        try:
            r = requests.get(host, params=params)
            break
        except requests.exceptions.ChunkedEncodingError as e:
            print(e)
            continue

    # Check if results are empty
    if 'No data returned !' in r.text:
        df = None
    else:
        try:
            df = pd.DataFrame(pd.read_csv(
                io.StringIO(r.text), sep=',', comment='#'))
            df['OBJECT'] = [star for i in range(len(df['OBJECT']))]
        except pd.errors.ParserError:
            df = None

    cache.save(df)

    print('Successfully loaded data for Star ', star)
    return df


def batch_from_ESO_Archive(stars, instrument, cache_folder='/DATA/Cache/', UseCache=False):
    """ fetch data for several stars at once"""

    cache = Cache.Cache(cache_folder, stars, instrument)
    data = cache.load() if UseCache else None

    if data is not None:
        return data

    is_first = True
    archive = None
    for star in stars:
        temp_archive = from_ESO_Archive(star, instrument, cache_folder=cache_folder, UseCache=True)
        if temp_archive is not None:
            if is_first:
                archive = temp_archive
                is_first = False
            else:
                try:
                    archive = pd.concat([archive, temp_archive])
                except TypeError as ex:
                    print(ex)
                    continue

    if UseCache:
        cache.save(archive)

    archive = archive[archive['Instrument'] == 'HARPS']
    return archive
