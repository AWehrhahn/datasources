import pandas as pd

def readTBL(filename):
    #Read Header
    with open(filename,'r') as file:
        header = {}
        counter = 0
        for i,line in enumerate(file):
            if line[0] == '\\':
                if '=' in line:
                    name,value = line.split('=')
                    header[name[1:].strip()] = value.replace('"','').strip()
                continue
            if line[0] == '|':
                temp = [l.strip() for l in line.split('|')[1:-1]]
                if counter == 0:
                    header['name'] = temp
                elif counter == 1:
                    header['dtype'] = temp
                elif counter == 2:
                    header['unit'] = temp
                counter += 1
                continue
            if line[0] not in ['\\','|'] :
                skip = i
                break

    #Read Data
    return pd.read_table(filename,comment='\\',header=None, names = header['name'],delim_whitespace=True,skiprows=skip),header