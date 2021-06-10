import os
import sys
import gnupg
from dictor import dictor
from py7zr import SevenZipFile
from .globals import _error_handler, BASEDIR, GPGHOME

def precheck(file, client, file_prefix):
    """ check if encrypted folder exists, append prefix to file if necessary """

    if not os.path.exists(f'{BASEDIR}/clients/{client}/encrypted'):
        os.makedirs(f'{BASEDIR}/clients/{client}/encrypted')

    file = os.path.basename(file)

    if file_prefix:
        file = file_prefix + '_' + file 
    return file


def encrypt_7z(file, args, config):
    
    print(f'encrypting {file} with 7zip')

    file_prefix = dictor(config, 'file_prefix')
    file_name = precheck(file, args.client, file_prefix) + '.7z'
    
    
    if os.path.exists(f'{BASEDIR}/clients/{args.client}/encrypted/{file_name}'):
        print(f'{file_name} already exists in encrypted folder')
        return file_name

    if dictor(config, 'enc_password'):
        with SevenZipFile(f'{BASEDIR}/clients/{args.client}/encrypted/{file_name}', 'w', password=dictor(config, 'enc_password')) as archive:
            try:
                archive.writeall(file)
            except Exception as excep:
                _error_handler(excep, f'7zip archive error: {file}')

    else:
        with SevenZipFile(f'{BASEDIR}/clients/{args.client}/encrypted/{file_name}', 'w') as archive:
            
            try:
                archive.writeall(file)
            except Exception as excep:
                _error_handler(excep, args.client, config, f'7zip archive error: {file}')

    print('encryption complete..')
    return file_name


def encrypt_GPG(file, args, config):
    
    client_home = f'{BASEDIR}/clients/{args.client}'
    
    if not os.path.exists(GPGHOME):
        os.makedirs(GPGHOME)

    gpg_key = dictor(config, 'gpg_key')
    file_prefix = dictor(config, 'file_prefix')

    gpg = gnupg.GPG(gnupghome=GPGHOME)
    
    keys = open(f'{client_home}/gpgkeys/{gpg_key}').read()
    key_import = gpg.import_keys(keys)

    print(f'encrypting {file} with GPG')
    file_name = precheck(file, args.client, file_prefix) + '.gpg'

    if os.path.exists(f'{BASEDIR}/clients/{args.client}/encrypted/{file_name}'):
        print(f'{file_name} already exists in encrypted folder')
        return file_name

    with open(file, 'rb') as f:
        status = gpg.encrypt_file(file=f, recipients=key_import.fingerprints, output=client_home+'/encrypted/'+file_name, always_trust=True)
        if not status.ok:
            _error_handler(f'Error encypting file with GPG {file}', args.client, config)
    return file_name
    
