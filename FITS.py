import os.path                     
import astropy.io.fits as fits
import TAR
import logging

# Open and load FITS files

def getFITS(filenames,folder='',extractTo='./',headerOnly = False):
    if type(filenames) == str:
        filenames = (filenames,)

    res = []
    for filename in filenames:
        if os.path.isfile(folder + filename):
            logging.info('Loading FITS data from %r',filename)
            _ , f_ext = os.path.splitext(filename)
            #if its a .tar file, unpack it and load all contained FITS files
            if f_ext == '.tar':
                dir,_ = TAR.extractTar(folder + filename,keepStructure = False,extractTo = extractTo)
                res2 = []
                for _ , _ , fileList in os.walk(dir):
                    for f in fileList:
                        _, f_ext = os.path.splitext(f)
                        if not f_ext == '.fits': continue #check if its a FITS file
                    
                        hdu = fits.open(os.path.join(dir,f))[0]
                        res2.append((hdu.header,hdu.data))  #retrieve the data now
                res.append(res2)
            
            #if its a .fits file, just load it and return it
            elif f_ext == '.fits':
                hdu = fits.open(filename,memmap=True)[0]
                if headerOnly:
                    res.append(hdu.header)
                else:
                    res.append((hdu.header,hdu.data))
            else: raise ValueError('Unknown File Format')
        else:
            # File not found
            res.append('File not Found')

    if len(res) == 1: return res[0]
    return res