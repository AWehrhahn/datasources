import numpy as np
import pandas as pd
import requests
import hashlib
import os

from os.path import isfile
from io import StringIO
import astropy.io.votable as votable

#http://archive.eso.org/cms/faq/how-do-i-programmatically-access-the-archive.html
#http://archive.eso.org/cms/faq/how-do-i-submit-a-request-to-the-archive-programmatically.html
#http://archive.eso.org/cms/faq/how-do-i-retrieve-download-the-data-programmatically.html

user = 'awehrhahn'
pw = 'eso:mOfjJ3*G'