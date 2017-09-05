from typing import List

import idlToPandas
import SIMBAD
import FITS
import ESO
import HEASARC
import Cache
import LSD
import TBL
import StarYAML

DataFrame = List[List]

#Data Sources should be project independent. All project specific references, should be in the appropiate project 
#Output should be Pandas DataFrame if possible

#This should just provide an interface for the other classes in DataSources
#avoid using the subclasses directly

def fromIDL(filename:str,key:str=None,folder:str = './DATA/IDL/',UseCache:bool = True) -> DataFrame:
    return idlToPandas.idlToPandas(filename,key,folder,UseCache)

def fromSIMBAD(stars:List[str],fields:List[str], format:str='Pandas', folder:str='./DATA/SIMBAD/', UseCache:bool=True) -> DataFrame:
    return SIMBAD.getFromSimbad(stars,fields,format,folder, UseCache)

def fromFITS(filenames:List[str],folder:str='',extractTo:str='./',headerOnly:bool=False) -> List:
    return FITS.getFITS(filenames,folder, extractTo,headerOnly)

def fromESO(dataset:List[str],folder:str='./DATA/ESO/') -> List[str]:
    return ESO.fromArchive(dataset,folder)

def fromHEASARC(dataset:List[str],folder:str='./DATA/HEARSEC/', UseCache:bool = True) -> List[str]:
    return HEASARC.getData(dataset,folder = folder, UseCache = UseCache)