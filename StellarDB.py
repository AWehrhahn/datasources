"""
Handle the collection of yaml files known as stellar db
"""
import os
from ruamel.yaml import YAML
try:
    from ruamel.yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    print('LibYaml not installed, ')
    from ruamel.yaml import Loader, Dumper


from Config.config import load_config
from DataSources import SIMBAD


class StellarDB:
    """ Class for handling stellar_db """

    def __init__(self):
        config = load_config('config.yaml')
        self.folder = config['path_stellar_db']
        self.cache = config['path_cache']
        self.yaml = YAML()
        self.name_index = self.gen_name_index()

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

    def load(self, name):
        """ load data for a given name """
        name = name.replace(' ', '')
        if name not in self.name_index:
            raise AttributeError('Name %s not found' % name)

        return self.__fix__(self.__load_yaml__(self.name_index[name]))

    def save(self, star):
        """ save data for star with given name """
        name = star['name'][0]
        if name not in self.name_index:
            print('WARNING: Name not found, creating new entry')
            filename = name + '.yaml'
            i = 1
            while os.path.exists(os.path.join(self.folder, filename)):
                filename = name + i + '.yaml'
                i += 1
            self.name_index[name] = filename
        else:
            filename = self.name_index[name]

        self.__write_yaml__(filename, star)

    def __fix__(self, star):
        """ fix read object, to conform to standards """
        if isinstance(star['name'], str):
            star['name'] = [star['name'], ]

        return star

    def auto_fill(self, name, fields=('ids', 'otype', 'sptype', 'ra', 'dec', )):
        """ retrieve data from SIMBAD and save it in file """
        star = self.load(name)
        name = star['name'][0]
        df = SIMBAD.getFromSimbad(name, fields, cache_folder=self.cache)
        df = df.iloc[0]

        if 'ids' in fields:
            ids = SIMBAD.Query_ID(name, cache_folder=self.cache)
            for id_star in ids:
                if id_star[0] not in star['name']:
                    star['name'].append(id_star[0])

            i = fields.index('ids')
            fields = fields[:i] + fields[i + 1:]

        field_to_df_translation = {
            'main_id': 'MAIN_ID', 'otype': 'OTYPE', 'sptype': 'SP_TYPE', 'ra': 'RA', 'dec': 'DEC'}

        for f in fields:
            star[f.lower()] = df[field_to_df_translation[f]]

        self.save(star)
