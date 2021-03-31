"""
Handle the collection of yaml files known as stellar db
"""
import inspect
import os
import sys
from string import ascii_lowercase
import copy

import astropy.units as u
import astropy.coordinates as coords
from astropy.time import Time
from astropy.table import QTable

import importlib

import numpy as np
import pandas as pd

# import yaml
from astropy.utils.data import download_file
from astroquery.simbad import Simbad
from astroquery.exoplanet_orbit_database import ExoplanetOrbitDatabaseClass
from astroquery.nasa_exoplanet_archive import NasaExoplanetArchive

from astropy.io.misc import yaml

from flex.flex import FlexFile

try:
    from . import Cache, config as Config
except:
    import Cache
    import config as Config

# TODO use json instead of yaml

class StellarDB:
    """ Class for handling stellar_db """

    def __init__(self):
        config = Config.load_config()
        self.folder = config["path_stellar_db"]
        self.cache = config["path_cache"]
        self.name_index = self.gen_name_index()

    def __load_yaml__(self, fname):
        """ load yaml data from file with given filename """
        with open(fname, "r") as fp:
            return yaml.load(fp)

    def __write_yaml__(self, fname, data):
        """ write data to disk """
        with open(fname, "w") as fp:
            yaml.dump(data, fp, default_flow_style=False)

    def load_flex(self, fname):
        ff = FlexFile.read(fname)
        return self._fix(ff.header)

    def write_flex(self, fname, data):
        ff = Flexfile(header=data)
        ff.write(fname)

    def load_layout(self, name):
        fname = os.path.join(os.path.dirname(__file__), f"layout_{name.lower()}.yaml")
        return self.__load_yaml__(fname)

    def gen_name_index(self):
        """ index all names to files containing them """
        list_of_files = [
            os.path.join(self.folder, x)
            for x in os.listdir(self.folder)
            if x.endswith(".flex")
        ]

        cache = Cache.Cache(self.cache, *list_of_files)
        try:
            data = cache.load()
        except FileNotFoundError:
            data = None

        if data is not None:
            return data

        name_index = {}
        for entry in list_of_files:
            star = self.load_flex(entry)
            name_list = (
                star["id"] if isinstance(star["id"], list) else (star["id"],)
            )
            for name in name_list:
                name = name.replace(" ", "")
                name_index[name] = entry

        cache.save(name_index)
        return name_index

    def load(self, name, auto_get=True):
        """
        load data for a given name
        if auto_get == True, then get info from the web if no file exists
        """
        name = name.replace(" ", "")
        if name not in self.name_index:
            if auto_get:
                print("Name %s not found, retrieving info online" % name)
                self.auto_fill(name)
            else:
                raise AttributeError("Name %s not found" % name)

        filename = self.name_index[name]
        star = self.load_flex(filename)

        return star

    def save(self, star):
        """ save data for star with given name """
        name = star["id"][0].replace(" ", "")
        if name not in self.name_index:
            print(f"WARNING: Name {name} not found, creating new entry")
            filename = name + ".flex"
            i = 1
            while os.path.exists(os.path.join(self.folder, filename)):
                filename = name + i + ".flex"
                i += 1
            filename = os.path.join(self.folder, filename)
            self.name_index[name] = filename
        else:
            filename = self.name_index[name]

        ff = FlexFile(header=star)
        ff.write(filename)

    def _fix(self, star):
        """ fix read object, to conform to standards """
        if isinstance(star["id"], str):
            star["id"] = [
                star["id"],
            ]

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

    def deepupdate(self, target, src):
        """Deep update target dict with src
        For each k,v in src: if k doesn't exist in target, it is deep copied from
        src to target. Otherwise, if v is a list, target[k] is extended with
        src[k]. If v is a set, target[k] is updated with v, If v is a dict,
        recursively deep-update it.

        Examples:
        >>> t = {'name': 'Ferry', 'hobbies': ['programming', 'sci-fi']}
        >>> deepupdate(t, {'hobbies': ['gaming']})
        >>> print t
        {'name': 'Ferry', 'hobbies': ['programming', 'sci-fi', 'gaming']}
        """
        for k, v in src.items():
            if type(v) == list:
                if not k in target:
                    target[k] = copy.deepcopy(v)
                else:
                    target[k].extend(v)
            elif type(v) == dict:
                if not k in target:
                    target[k] = copy.deepcopy(v)
                else:
                    self.deepupdate(target[k], v)
            elif type(v) == set:
                if not k in target:
                    target[k] = v.copy()
                else:
                    target[k].update(v.copy())
            else:
                target[k] = copy.copy(v)

    def auto_fill(self, name):
        """ retrieve data from SIMBAD and ExoplanetDB and save it in file """
        try:
            star = self.load(name, auto_get=False)
        except AttributeError:
            star = {"id": [name]}
        name = star["id"][0]

        # Load fields to read from Database
        simbad_source = StellarDB_Simbad()
        exoplanets_org_source = StellarDB_ExoplanetsOrg()
        exoplanets_nasa_source = StellarDB_ExoplanetsNasa()

        simbad_data = simbad_source.get(name)
        exoplanet_data = exoplanets_org_source.get(name)
        nasa_data = exoplanets_nasa_source.get(name)

        # Combine datasets
        # TODO: decide how to do this
        # Here we simply use an order of priority
        # I.e. least trustworthy first
        self.deepupdate(star, exoplanet_data)
        self.deepupdate(star, simbad_data)
        self.deepupdate(star, nasa_data)

        # Remove duplicate entries
        # Remove extra spaces
        ids = [" ".join(s.split()) for s in star["id"]]
        ids, ind = np.unique(ids, return_index=True)
        star["id"] = ids[np.argsort(ind)]
        star["citation"] = np.unique(star["citation"])

        self.save(star)

class StellarDB_DataSource:
    def load_yaml(self, fname):
        """ load yaml data from file with given filename """
        with open(fname, "r") as fp:
            return yaml.load(fp)

    def load_layout(self, name):
        fname = os.path.join(os.path.dirname(__file__), f"layout_{name.lower()}.yaml")
        return self.load_yaml(fname)

    def set_values(self, data, layout, skip_nan=True):
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

        for key, value in layout.items():
            if key.startswith("__"):
                continue
            if "name" in value:
                unit = value.get("unit", None)
                name = value["name"]
                try:
                    ref = data[value["ref"]]
                except KeyError:
                    ref = None

                try:
                    unc = value["unc"]
                    unc = (data[unc[0]], data[unc[1]])
                except KeyError:
                    unc = None

                try:
                    value = data[name]
                except KeyError:
                    # Skip missing data
                    continue

                # Extract data from structures if necessary
                try:
                    value = data[name].array[0]
                except AttributeError:
                    # Its not a pandas array
                    pass

                if (skip_nan and 
                    (value is None or value != value or np.ma.is_masked(value))):
                    # Skip bad values
                    # value != value == nan
                    continue

                # Apply the correct units
                if unit is None or unit == "str":
                    pass
                elif unit == "hourangle":
                    value = coords.Angle(value, u.hourangle)
                elif unit == "deg" and isinstance(value, str):
                    value = coords.Angle(value, u.deg)
                elif unit == "jd":
                    value = Time(value, format=unit)
                else:
                    value = value << u.Unit(unit)

                # Apply Meta information
                try:
                    if value.info.meta is None:
                        value.info.meta = {}
                    if ref is not None:
                        value.info.meta["reference"] = ref
                    if unc is not None:
                        value.info.meta["uncertainty"] = unc
                except:
                    pass

                # Store data
                result[key] = value

            elif "__class__" in value:
                # If we provide a class use that
                # The input to the constructor are the specified values
                module = value["__module__"]
                cls = value["__class__"]
                module = importlib.import_module(module)
                module = getattr(module, cls)
                layout2 = {k:v for k,v in layout[key].items() if k != "class"}
                value = self.set_values(data, layout2)
                result[key] = module(**value)
            else:
                result[key] = self.set_values(data, layout[key])

        return result


class StellarDB_Simbad(StellarDB_DataSource):
    def __init__(self):
        self.fields = ["ra","dec", "diameter", "rv_value", "fe_h", "rot", 
        "pmra", "pmdec", "plx", "sp", "otype", "flux(U)", "flux(B)", "flux(V)",
         "flux(G)", "flux(R)", "flux(I)", "flux(J)", "flux(H)", "flux(K)"]
        self.timeout = 10
        self.layout = self.load_layout("simbad")
        self.citation = [("Wenger, M., “The SIMBAD astronomical database. The " 
            "CDS reference database for astronomical objects”, Astronomy and "
            "Astrophysics Supplement Series, vol. 143, pp. 9–22, 2000. "
            "doi:10.1051/aas:2000332")]

    def get(self, name):
        # SIMBAD Data
        for f in self.fields:
            try:
                Simbad.add_votable_fields(f)
            except KeyError:
                print("No field named ", f, " found")

        simbad_data = None
        for i in range(self.timeout):
            try:
                simbad_data = Simbad.query_object(name)
                break
            except Exception:
                print(f"Connection failed, attempt {i} of {self.timeout}")
                continue

        # Reset the fileds, in case we run this several times
        Simbad.reset_votable_fields()
        if simbad_data is None:
            raise RuntimeError("Star name not found or connection timed out")

        simbad_data = simbad_data.to_pandas()
        simbad_data = simbad_data.applymap(
            lambda s: s.decode("utf-8") if isinstance(s, bytes) else s
        )
        simbad_data["MAIN_ID"] = simbad_data["MAIN_ID"].apply(
            lambda s: s.replace(" ", "")
        )
        simbad_data = dict(simbad_data)
        simbad_data = self.set_values(simbad_data, self.layout)
        simbad_data["id"] = self.get_ids(name)
        simbad_data["citation"] = self.citation
        return simbad_data

    def get_ids(self, name):
        # Give it a few tries, just in case
        ids = None
        for i in range(self.timeout):
            try:
                ids = Simbad.query_objectids(name)
                break
            except Exception:
                print(f"Connection failed, attempt {i}")
                continue
        if ids is None:
            raise RuntimeError("Star name not found or connection timed out")

        # To keep the order of elements
        star = {"name": [name]}
        ids = list(ids["ID"])
        ids, ind = np.unique(star["name"] + ids, return_index=True)
        ids = list(ids[np.argsort(ind)])

        return ids

class StellarDB_ExoplanetsOrg(StellarDB_DataSource, ExoplanetOrbitDatabaseClass):
    def __init__(self):
        super().__init__()
        self.layout = self.load_layout("exoplanets_org")
        self.citation = [("Han, E., “Exoplanet Orbit Database. II. Updates to "
            "Exoplanets.org”, Publications of the Astronomical Society of the "
            "Pacific, vol. 126, no. 943, p. 827, 2014. doi:10.1086/678447")]
        self.EXOPLANETS_CSV_URL = 'http://exoplanets.org/csv-files/exoplanets.csv'

    def get_table(self, cache=True, show_progress=True, table_path=None):
        """ We overwrite the get table method, since the original uses a horrbly slow
        implementation. We replace that with pandas. We also skip some minor steps that
        we dont need. """
        if self._table is None:
            if table_path is None:
                table_path = download_file(self.EXOPLANETS_CSV_URL, cache=cache,
                                           show_progress=show_progress)
            # Pandas go brrrr
            exoplanets_table = pd.read_csv(table_path, low_memory=False)

            # Use numpy char arrays for efficiency
            lowercase_names = exoplanets_table["NAME"].values.astype(str)
            lowercase_names = np.char.lower(lowercase_names)
            lowercase_names = np.char.replace(lowercase_names, " ", "")
            exoplanets_table['NAME_LOWERCASE'] = lowercase_names

            # convert the dataframe to a quantity table
            exoplanets_table = QTable.from_pandas(exoplanets_table)
            # Need to define the index
            exoplanets_table.add_index('NAME_LOWERCASE')

            # Create sky coordinate mixin column
            # Skip the sky coordinates, as we will do that later manually
            # exoplanets_table['sky_coord'] = coords.SkyCoord(ra=exoplanets_table['RA'] * u.hourangle,
            #                                          dec=exoplanets_table['DEC'] * u.deg)
            # Assign units to columns where possible
            for col in exoplanets_table.columns:
                if col in self.param_units:
                    # Check that unit is implemented in this version of astropy
                    try:
                        exoplanets_table[col].unit = u.Unit(self.param_units[col])
                    except ValueError:
                        print(f"WARNING: Unit {self.param_units[col]} not recognised")

            self._table = QTable(exoplanets_table)
        return self._table

    def get(self, name):
        planets = {}
        for comp in ascii_lowercase[1:]:
            try:
                exoplanet_data = self.query_planet(f"{name} {comp}")
                exoplanet_data = self.set_values(exoplanet_data, self.layout)
                exoplanet_data["planets"] = {comp: exoplanet_data["planets"]}
                if comp == "b":
                    planets = exoplanet_data
                else:
                    planets["planets"][comp] = exoplanet_data["planets"][comp]
            except KeyError:
                # Planet not found (and we don't expect any more)
                break

        planets["citation"] = self.citation
        return planets
           

class StellarDB_ExoplanetsNasa(StellarDB_DataSource):
    def __init__(self):
        self.timeout = 10
        self.layout = self.load_layout("exoplanets_nasa")
        self.citation = ["This research has made use of the NASA Exoplanet "
            "Archive, which is operated by the California Institute of "
            "Technology, under contract with the National Aeronautics and "
            "Space Administration under the Exoplanet Exploration Program."]

    def tap(self, name, regularize=True):
        from astroquery.utils.tap.core import TapPlus

        if regularize:
            name = NasaExoplanetArchive._regularize_object_name(name)

        archive = TapPlus(url="https://exoplanetarchive.ipac.caltech.edu/TAP")
        query = archive.launch_job(f"select top 10 * from pscomppars where hostname='{name}'")
        table = query.results

        return table

    def get(self, name):
        data = None
        for i in range(self.timeout):
            try:
                # data = NasaExoplanetArchive.query_object(name)
                data = self.tap(name)
                break
            except Exception:
                print(f"Connection failed, attempt {i} of {self.timeout}")
                continue
        
        if data is None:
            raise RuntimeError("Star name not found or connection timed out")

        if len(data) == 0:
            # No data found in the datatbase
            return {}

        star_data = self.set_values(data[0], self.layout)
        star_data["planets"] = {data[0]["pl_letter"] : star_data["planets"]}

        for i in range(1, len(data)):
            planet_letter = data[i]["pl_letter"]
            planet_data = self.set_values(data[i], self.layout)
            star_data["planets"][planet_letter] = planet_data["planets"]

        star_data["citation"] = self.citation

        return star_data

if __name__ == "__main__":
    target = "Trappist-1"
    sdb = StellarDB()
    sdb.auto_fill(target)
    star = sdb.load(target, auto_get=False)  # Check if everything worked
    print("Done")
