import pandas as pd
import os.path as op
import logging

def fromFile(file,info=False,verbose=False):
    name,_ = op.splitext(op.basename(file))
    date,target,sp = name.split('_')
    names = ['DeltaV','Profile','Error']
    
    logging.info('Reading LSD data from: %r',file)
    df = pd.read_table(file,delim_whitespace=True,header=0,names = names,usecols=(0,1,2,)).iloc[:-1]
    
    if (sp in ['iv','iq','iu']):
        df['Profile'] = 1 - df['Profile']

    if verbose:
        print('Target: %s' % target)
        print('Obs Date: %s' % date)
        print('Stokes Parameter: %s' % sp)

    if info:
        return df,{'Target':target,'Date':date,'Parameter':sp}

    return df

def info(file):
    name,_ = op.splitext(op.basename(file))
    date,target,sp = name.split('_')
    return target,date,sp

