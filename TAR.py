import tarfile
import os.path
import logging
                   
#Handle .tar files

#Extract a .tar file
def extractTar(filename,keepStructure=True,extractTo = './'):
    #Use filename as folder
    files_res = []
    file, file_extension = os.path.splitext(filename)
    sub = file.split('\\')           #Use python function
    path = extractTo + sub[-1] + '/'
    logging.info('Untar %s to %s' % (sub[-1],extractTo))
    with tarfile.TarFile(filename) as file:
        for f in file:
            f.name = f.name.replace(r':', '_') #remove 'bad' characters
            if not keepStructure:
                f.name = str.split(f.name,'/')[-1] #only use actual filename, discard structure
            if not os.path.isfile(os.path.join(path + f.name)): #Only extract if the file does not exist already
                file.extract(f,path=path)
            files_res.append(os.path.join(path,f.name))
    return path,files_res

#returns the contents as file like objects
#Some contents might be unavailable as the files are closed afterwards
def readTar(filename):
    with tarfile.TarFile(filename) as file:
        return [file.extractfile(f) for f in file]
