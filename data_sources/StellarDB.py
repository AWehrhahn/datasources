"""
Handle the collection of yaml files known as stellar db
"""
import inspect
import os
import sys

import astropy.units as u
import astropy.coordinates as coords

import numpy as np
import pandas as pd
# import yaml

from astroquery.simbad import Simbad
from astroquery.exoplanet_orbit_database import ExoplanetOrbitDatabase
from astropy.io.misc import yaml

from . import Cache, config as Config

# TODO use json instead of yaml

class StellarDB:
    """ Class for handling stellar_db """

    def __init__(self):
        config = Config.load_config()
        self.folder = config['path_stellar_db']
        self.cache = config['path_cache']
        self.name_index = self.gen_name_index()

        config_filename = os.path.join(os.path.dirname(__file__), 'StellarDB_config.yaml')
        self.config = self.__load_yaml__(config_filename)

    def __load_yaml__(self, fname):
        """ load yaml data from file with given filename """
        with open(fname, 'r') as fp:
            return yaml.load(fp)

    def __write_yaml__(self, fname, data):
        """ write data to disk """
        with open(fname, 'w') as fp:
            yaml.dump(data, fp, default_flow_style=False)

    def load_layout(self, name):
        fname = os.path.join(os.path.dirname(__file__), f"layout_{name.lower()}.yaml")
        return self.__load_yaml__(fname)

    def gen_name_index(self):
        """ index all names to files containing them """
        list_of_files = [os.path.join(self.folder, x) for x in os.listdir(
            self.folder) if x.endswith('.yaml')]

        cache = Cache.Cache(self.cache, *list_of_files)
        try:
            data = cache.load()
        except FileNotFoundError:
            data = None

        if data is not None:
            return data

        name_index = {}
        for entry in list_of_files:
            star = self.__load_yaml__(entry)
            name_list = star['name'] if isinstance(
                star['name'], list) else (star['name'], )
            for name in name_list:
                name = name.replace(' ', '')
                name_index[name] = entry

        cache.save(name_index)
        return name_index

    def load(self, name, auto_get=True):
        """
        load data for a given name
        if auto_get == True, then get info from the web if no file exists
        """
        name = name.replace(' ', '')
        if name not in self.name_index:
            if auto_get:
                print('Name %s not found, retrieving info online' % name)
                self.auto_fill(name)
            else:
                raise AttributeError('Name %s not found' % name)

        return self.__fix__(self.__load_yaml__(self.name_index[name]))

    def save(self, star):
        """ save data for star with given name """
        name = star['name'][0].replace(' ', '')
        if name not in self.name_index:
            print(f'WARNING: Name {name} not found, creating new entry')
            filename = name + '.yaml'
            i = 1
            while os.path.exists(os.path.join(self.folder, filename)):
                filename = name + i + '.yaml'
                i += 1
            filename = os.path.join(self.folder, filename)
            self.name_index[name] = filename
        else:
            filename = self.name_index[name]

        self.__write_yaml__(filename, star)

    def __fix__(self, star):
        """ fix read object, to conform to standards """
        if isinstance(star['name'], str):
            star['name'] = [star['name'], ]

        return star


    def to_base_type(self, value):
        if isinstance(value, np.str_):
            return str(value)
        elif isinstance(value, np.floating):
            return float(value)
        elif isinstance(value, np.integer):
            return int(value)
        elif isinstance(value, list):
            return [self.to_base_type(s) for s in value]
        else:
            return value

    def set_values(self, data, layout, **kwargs):
        """
        Fill the fields in layout, with data from data and keywords
        
        Parameters
        ----------
        data : dict
            input data
        layout : dict
            target layout of the data
        """

        result = {}
        for key in layout:
            data_key = layout[key]
            unit = None
            if isinstance(data_key, list):
                data_key, unit = data_key
            elif isinstance(data_key, dict):
                result[key] = self.set_values(data, data_key, **kwargs)
                continue
        
            try:
                value = data[data_key].array[0]
            except AttributeError:
                # Its not a pandas array
                value = data[data_key]
            except KeyError:
                # Data not in data, get it from keyword args
                value = kwargs[data_key]

            if np.ma.is_masked(value) or value is np.nan:
                continue

            value = self.to_base_type(value)

            if unit is not None:
                if isinstance(value, str):
                    value = coords.Angle(value, unit)
                else:    
                    value *= u.Unit(unit)
            result[key] = value

        return result


    def auto_fill(self, name):
        """ retrieve data from SIMBAD and ExoplanetDB and save it in file """
        try:
            star = self.load(name, auto_get=False)
        except AttributeError:
            star = {'name': [name]}
        name = star['name'][0]

        # Load fields to read from Database
        simbad_fields = self.config['SIMBAD_fields']
        exoplanet_fields = self.config['exoplanet_fields']

        # SIMBAD Data
        for f in simbad_fields:
            try:
                Simbad.add_votable_fields(f)
            except KeyError:
                print('No field named ', f, ' found')

        for _ in range(10):
            try:
                simbad_data = Simbad.query_object(name)
                break
            except Exception:
                continue

        if simbad_data is None:
            raise AttributeError('Star name not found')
        simbad_data = simbad_data.to_pandas()
        simbad_data = simbad_data.applymap(lambda s: s.decode('utf-8') if isinstance(s, bytes) else s)
        simbad_data['MAIN_ID'] = simbad_data['MAIN_ID'].apply(lambda s: s.replace(' ', ''))

        # Give it a few tries, just in case
        for _ in range(10):
            try:
                ids = Simbad.query_objectids(name)
                break
            except Exception:
                continue
        # To keep the order of elements
        ids = list(ids["ID"])
        ids, ind = np.unique(star["name"] + ids, return_index=True)
        ids = list(ids[np.argsort(ind)])

        simbad_data = dict(simbad_data)
        layout = self.load_layout("simbad")
        data = self.set_values(simbad_data, layout, ids=ids)

        # Exoplanet Data
        planets = {}
        layout = self.load_layout("exoplanets")
        for comp in ["b", "c", "d", "e", "f", "g"]:
            try:
                exoplanet_data = ExoplanetOrbitDatabase.query_planet(f"{name} {comp}")
                exoplanet_data = self.set_values(exoplanet_data, layout)
                exoplanet_data["planets"] = {comp: exoplanet_data["planets"]}
                planets[comp] = exoplanet_data
            except KeyError:
                # Planet not found (and we don't expect any more)
                break

        # Combine datasets
        star.update(data)
        for p in planets.values():
            star.update(p)

        self.save(star)

if __name__ == '__main__':
    target = 'Trappist-1'
    sdb = StellarDB()
    sdb.auto_fill(target)
    star = sdb.load(target, auto_get=False) #Check if everything worked
    print('Done')
