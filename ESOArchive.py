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

# http://archive.eso.org/wdb/wdb/eso/eso_archive_main/query?wdbo=csv%2fdisplay&max_rows_returned=200&instrument=&tab_object=on&target=HD%20209458&resolver=simbad&ra=&dec=&box=00%2010%2000%c2%b0_or_hour=hours&tab_target_coord=on&format=SexaHour&wdb_input_file=&night=&stime=&starttime=12&etime=&endtime=12&tab_prog_id=on&prog_id=&gto=&pi_coi=&obs_mode=&title=&spectrum[]=HARPS&tab_dp_cat=on&tab_dp_type=on&dp_type=&dp_type_user=&tab_dp_tech=on&dp_tech=&dp_tech_user=&tab_dp_id=on&dp_id=&origfile=&tab_rel_date=on&rel_date=&obs_name=&ob_id=&tab_tpl_start=on&tpl_start=&tab_tpl_id=on&tpl_id=&tab_exptime=on&exptime=&tab_filter_path=on&filter_path=&gris_path=&grat_path=&slit_path=&tab_instrument=on&add=((ins_id%20like%20%27HARPS%25%27))&tab_tel_airm_start=on&tab_stat_instrument=on&tab_ambient=on&tab_stat_exptime=on&tab_HDR=on&tab_mjd_obs=on&aladin_colour=aladin_instrument&tab_stat_plot=on&order=&
# wdbo: output format
# target=HD%20209458
# tab_instrument=on&add=((ins_id%20like%20%27HARPS%25%27))

url = "http://archive.eso.org/wdb/wdb/eso/eso_archive_main/query?"
params = {
    'wdbo' : 'csv',
    'target' : 'HD 20209458',
    'tab_instrument' : "((ins_id like 'HARPS%'))"
    }
