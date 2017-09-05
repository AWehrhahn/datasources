from os.path import isfile, join, expanduser
from astroquery.eso import Eso
import logging
import secretstorage

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
