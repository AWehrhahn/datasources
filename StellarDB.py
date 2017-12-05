"""
Handle the collection of yaml files known as stellar db
"""
import os
import inspect
import numpy as np
import pandas as pd
from ruamel.yaml import YAML, comments
try:
    from ruamel.yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    print('LibYaml not installed, ')
    from ruamel.yaml import Loader, Dumper


from Config.config import load_config
#import SIMBAD
from astroquery.simbad import Simbad
try:
    import HEASARC
except ModuleNotFoundError:
    from DataSources import HEASARC


class StellarDB:
    """ Class for handling stellar_db """

    def __init__(self):
        config = load_config('config.yaml')
        self.folder = config['path_stellar_db']
        self.cache = config['path_cache']
        self.yaml = YAML()
        self.name_index = self.gen_name_index()

        config_filename = inspect.stack()[0][1]
        config_filename = os.path.join(os.path.dirname(config_filename), 'StellarDB_config.yaml')
        self.config = self.__load_yaml__(config_filename)

    def __load_yaml__(self, fname):
        """ load yaml data from file with given filename """
        with open(fname, 'r') as fp:
            return self.yaml.load(fp)

    def __write_yaml__(self, fname, data):
        """ write data to disk """
        with open(fname, 'w') as fp:
            self.yaml.dump(data, fp)

    def gen_name_index(self):
        """ index all names to files containing them """
        list_of_files = [os.path.join(self.folder, x) for x in os.listdir(
            self.folder) if x.endswith('.yaml')]

        name_index = {}
        for entry in list_of_files:
            star = self.__load_yaml__(entry)
            name_list = star['name'] if isinstance(
                star['name'], list) else (star['name'], )
            for name in name_list:
                name = name.replace(' ', '')
                name_index[name] = entry
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
            print('WARNING: Name not found, creating new entry')
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
        simbad_data = Simbad.query_object(name).to_pandas()
        simbad_data = simbad_data.applymap(lambda s: s.decode('utf-8') if isinstance(s, bytes) else s)
        simbad_data['MAIN_ID'] = simbad_data['MAIN_ID'].apply(lambda s: s.replace(' ', ''))
        simbad_data['key'] = 1

        ids = Simbad.query_objectids(name)
        for n in ids:
            if n[0] not in star['name']:
                star['name'].append(n[0])

        # Exoplanet Data
        exoplanet_data = HEASARC.getData("Position==%s" % name, fields=exoplanet_fields)
        exoplanet_data['star_name'] = exoplanet_data['star_name'].apply(lambda s: s.replace(' ', ''))
        exoplanet_data['planet_name'] = exoplanet_data.iloc[:, 0]
        exoplanet_data['key'] = 1

        #This relies on the Main_ID in SIMBAD and exoplanet.org to be the same
        merge = pd.merge(simbad_data, exoplanet_data, on='key')

        # Set values according to layout        
        layout = self.load('ids')

        def to_baseclass(value):
            """ fix type of value to a python base class """
            if isinstance(value, (np.ndarray, np.generic)):
                if value.dtype in [np.float32, np.float64]:
                    return float(value)
                if value.dtype in [np.int32, np.int64]:
                    return int(value)
            if isinstance(value, str):
                value = value.strip()
                try:
                    value = float(value)
                    return value
                except ValueError:
                    pass
                if value == 'null':
                    return float('NaN')
            return str(value)

        def set_values(layout, merge, star={}):
            """ set values in merge, as described in layout """
            for entry in layout.items():
                if entry[0] in ['name']:
                    continue
                #for planets
                if entry[0]  == 'planets':
                    star['planets'] = {}
                    for _, planet in merge.iterrows():
                        name = planet['planet_name'][-1]
                        star['planets'][name] = set_values(entry[1]['name'], merge, star={})
                    continue

                # If only one label is given use that one
                if isinstance(entry[1], str):
                    value = to_baseclass(merge[entry[1]][0])
                    star[entry[0]] = value
                
                # If there is a list then use the first that is not Null
                if isinstance(entry[1], list):
                    star[entry[0]] = None
                    for ent in entry[1]:
                        value = to_baseclass(merge[ent][0])
                        if value is not None and not np.isnan(value):
                            star[entry[0]] = value
                            break

                # If it is a Commeted Map, i.e. a dictionary, go into each object and repeat
                if isinstance(entry[1], comments.CommentedMap):
                    star[entry[0]] = set_values(entry[1], merge, star={})
            return star

        star = set_values(layout, merge, star=star)
        self.save(star)

if __name__ == '__main__':
    target = 'WASP-47'
    sdb = StellarDB()
    sdb.auto_fill(target)
    star = sdb.load(target, auto_get=False) #Check if everything worked
    print('Done')
