#import yaml
import ruamel_yaml as yaml
import os.path

folder = './DATA/YAML/'
defaultStarFileName = os.path.join(folder,'default.yaml')

def loadStar(filename,useDefaultFolder = True):
    if useDefaultFolder:
        filename = os.path.join(folder,filename)

    if not os.path.exists(filename): 
        print('File %s not found' % filename)
        return

    #Load default and specific star values
    default = yaml.load(open(defaultStarFileName))
    specific = yaml.load(open(filename))

    #override default values with specific values if possible
    for x in specific:
        default[x] = specific[x]

    return specific
