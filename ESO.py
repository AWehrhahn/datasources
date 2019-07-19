from os.path import isfile, join, expanduser
from astroquery.eso import Eso
import logging
import secretstorage


import urllib

import pyvo as vo
from astropy.coordinates import SkyCoord
from astropy.units import Quantity

cacheDir = expanduser(r'~\.astropy\cache\astroquery\Eso')

# Change this if necessary
user = 'awehrhahn'


def login(user):
    eso = Eso()
    eso.login(user, store_password=True)
    return eso


def fromArchive(dataset, folder='./DATA/ESO'):
    if type(dataset) == str:
        dataset = (dataset,)

    # let astroquery do everything
    eso = login(user)
    return eso.retrieve_data(dataset)

def fromSciencePortal(target, instrument, diameter = 0.5):
    ssap_endpoint = "http://archive.eso.org/ssap"
    ssap_service = vo.dal.SSAService(ssap_endpoint)
    print("Querying the ESO SSAP service at %s" %(ssap_endpoint))

    pos = SkyCoord.from_name(target)
    size = Quantity(diameter, unit="deg")
    print("SESAME coordinates for %s: %s" % (target, pos.to_string()))

    ssap_resultset = ssap_service.search(pos=pos.fk5, diameter=size, COLLECTION=instrument)

    return ssap_resultset

def downloadFromSciencePortal(row):
    url_name = row["access_url"].decode()
    out_file = row["CREATORDID"].decode()[23:]
    print(f"Fetching file: {url_name}.fits as {out_file}")
    urllib.request.urlretrieve(url_name, out_file)
    return out_file
