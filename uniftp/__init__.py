import os
import sys
import yaml
from pprint import pprint
from dictor import dictor

#from paramiko import Transport, SFTPClient, RSAKey
import pysftp
from pathlib import Path
from time import sleep
from subprocess import Popen, PIPE, CalledProcessError
from .encryption import encrypt_7z, encrypt_GPG

from .globals import log, _error_handler, EMAIL_TO, EMAIL_ON_ERROR, EMAIL_FROM, \
BASEDIR, USER, GROUP, GREEN, RED, YELLOW, ORANGE, RESET, DEBUG

def generate(client):
    """
    generates a client folder structure with sample config data
    """
    print(f'generating {client} folders')
    
    client_path = f'{BASEDIR}/clients/{client}'
    
    try:
        os.makedirs(client_path)
    except FileExistsError:
        sys.exit(f'{RED}[ERROR] client folder already exists at {client_path}{RESET}')
    except OSError as excep:
        _error_handler(excep)

    sample = {}
    sample['prod'] = {}
    sample['prod']['action'] = "push"
    sample['prod']['host'] = "ftp.client.com"
    sample['prod']['port'] = 2022
    sample['prod']['username'] = "user"
    sample['prod']['auth_type'] = "password"
    sample['prod']['password'] = "mySecretPassword"
    sample['prod']['privkey'] = "client.priv"
    sample['prod']['enc_type'] = "7zip"
    sample['prod']['enc_password'] = "7zipSecretPassword"
    sample['prod']['remote_path'] = "/uploads"
    sample['prod']['local_path'] = "/home/user/downloads"
    sample['prod']['file_prefix'] = "my_file_"
    sample['prod']['delete_encrypted_files'] = "true"

    try:
        with open(f'{client_path}/config.yml', 'w') as outfile:
            yaml.dump(sample, outfile, default_flow_style=False, sort_keys=False)
    except Exception as excep:
        sys.exit(f'{RED}[ERROR]: {excep}{RESET}')

    # create sshkeys folder
    if not os.path.exists(f'{client_path}/sshkeys'):
        os.makedirs(f'{client_path}/sshkeys')

    os.system(f'chown -R {USER}:{GROUP} {client_path}')
    os.system(f'chmod 600 {client_path}/config.yml')
    os.system(f'chmod 700 {client_path}/sshkeys')
    os.chmod(client_path, 0o750)

    print(f'{GREEN}new folder and sample Config YAML file generated in {client_path} for client\'s Production FTP environment{RESET}')
    sys.exit()


def _remote_path(remote_path, sftp):
    # check if need to chdir on target
    if remote_path:
        try:
            sftp.chdir(remote_path)
        except (IOError, Exception) as excep:
            sys.exit(f'[ERROR] unable to chdir to remote_path {excep}')
        return sftp.pwd


def _push_file(sftp, args, file, config):
    """ push file to client """

    file_path = None

    if not os.path.exists(file):
        sys.exit(f'{RED}[ERROR] File {file} not present{RESET}')

    if dictor(config, 'enc_type'):
        enc_type = dictor(config, 'enc_type')
        enc_password = dictor(config, 'enc_password')

        ## 7zip
        if enc_type and enc_type == '7zip':
            file_prefix = dictor(config, 'file_prefix')
            file = encrypt_7z(file, args, config)
            file_path = f'{BASEDIR}/clients/{args.client}/encrypted/{file}'

        ## GPG
        if enc_type and enc_type == 'gpg':
            file_prefix = dictor(config, 'file_prefix')
            gpg_key = dictor(config, 'gpg_key', checknone=True)
            file = encrypt_GPG(file, args, config)
            file_path = f'{BASEDIR}/clients/{args.client}/encrypted/{file}'   

    if not file_path:
        file_path = file


    remote_path = dictor(config, 'remote_path', default='/')

    print(f'Pushing file {file} to {args.client}')
    raw_file_name = Path(file_path).name

    # check if file is a directory
    if os.path.isdir(file_path):
        try:
            sftp.mkdir(raw_file_name)
        except (OSError, Exception) as excep:
            _error_handler(excep, args, config, f'Error mkdir: {raw_file_name}')

        try:
            sftp.put_r(file_path, raw_file_name, preserve_mtime=True)
        except (PermissionError, Exception) as excep:
            _error_handler(excep, args, config, f'Error put_r: {raw_file_name}')
    else:
        try:
            sftp.put(localpath=file_path, remotepath='/'+remote_path+'/'+raw_file_name, confirm=False)
        except Exception as excep:
            _error_handler(excep, args, config, 'Error pushing file to client')
        
    log.info(f'files on target host: {list_files(args, config)}\n')
    print(f'files on target host: {list_files(args, config)}\n')

    if dictor(config, 'enc_type'):
        if dictor(config, 'delete_encrypted_files') == 'true':
            os.remove(f'{BASEDIR}/clients/{args.client}/encrypted/{file}')
    
    print(f'{GREEN}push complete{RESET}\n')


def _pull_file(sftp, args, config):
    
    local_path = dictor(config, 'local_path')
    remote_path = dictor(config, 'remote_path', default='/')

    if not local_path:
        log.error(f'no local_path configuration for {args.client}, {args.env}')
        sys.exit(f'{RED}[ERROR] no local_path configuration for {args.client} ({args.env}){RESET}')
    
    try:
        sftp.get_r(remote_path, local_path, preserve_mtime=True)
    except (PermissionError, Exception) as excep:
        _error_handler(excep, args, config, f'Error get_r: {raw_file_name}')

    sftp.close()


def _check_known_host(host, port, auth_type, username, password, key):
    """ checks if target host is in known_hosts file, if not, adds it """
    print('checking known host')
    p = Popen(f'ssh-keygen -F {host} -f {BASEDIR}/known_hosts', shell=True, stdout=PIPE)
    if not p.communicate()[0]:
        Popen(f'ssh-keyscan {host} >> {BASEDIR}/known_hosts', shell=True, stdout=PIPE)
        sleep(6)


def list_files(args, config):
    """ show all files on remote server """

    sftp = _get_sftp(args, config)

    if dictor(config, 'remote_path'):
        try:
            file_list = sftp.listdir(dictor(config, 'remote_path'))
        except Exception as excep:
            _error_handler(excep, args, config, 'Password auth error')

    else:
        try:
            file_list = sftp.listdir()
        except Exception as excep:
            _error_handler(excep, args, config, 'Password auth error')

    sftp.close()
    return pprint(file_list)


def _get_sftp(args, config):
    """ establish FTP connection to client """
    
    username = dictor(config, 'username', checknone=True)
    host = dictor(config, 'host', checknone=True)
    port = dictor(config, 'port', 22)
    key = dictor(config, 'privkey')
    auth_type = dictor(config, 'auth_type', checknone=True)
    password = dictor(config, 'password')

    # create known_hosts file if missing
    if not os.path.exists(f'{BASEDIR}/known_hosts'):
        with open(f'{BASEDIR}/known_hosts', 'a'):
            pass

    # generate known_hosts entry for target
    _check_known_host(host, port, auth_type, username, password, key)
    
    # pysftp security options
    cnopts = pysftp.CnOpts()
    cnopts = pysftp.CnOpts(knownhosts=f'{BASEDIR}/known_hosts')

    ### PASSWORD AUTH
    if auth_type == 'password':
        password = dictor(config, 'password', checknone=True)
       
        try:
            sftp = pysftp.Connection(host, username=username, password=password, port=port, cnopts=cnopts)
        except (ConnectionError, ConnectionAbortedError, ConnectionRefusedError, ConnectionResetError, Exception) as excep:
            _error_handler(excep, args, config, 'Password auth error')
            

    ### KEY AUTH
    if auth_type == 'key':
        if not os.path.exists(key):
            if os.path.exists(BASEDIR + '/clients/' + args.client + '/sshkeys/' + key):
                key = BASEDIR + '/clients/' + args.client + '/sshkeys/' + key
            else:
                sys.exit(f'{RED}[ERROR] ssh private key {key} does not exist{RESET}')
        try:
            sftp = pysftp.Connection(host, username=username, private_key=key, port=port, cnopts=cnopts)
        except (ConnectionError, ConnectionAbortedError, ConnectionRefusedError, ConnectionResetError, Exception) as excep:
            _error_handler(excep, args, config)
    
    return sftp


def _start_ftp(args, config):
    """ start FTP process to client """

    sftp = _get_sftp(args, config)
    
    action = dictor(config, 'action', checknone=True)

    if action == 'push':
        if not args.file:
            sys.exit('{RED}[ERROR] {RESET}')
        
        # multiple files or dirs
        if ',' in args.file:
            files = args.file.split(',')
            for f in files:
                log.info(f'pushing to client: {args.client}, file: {args.file}, env: {args.env}')
                _push_file(sftp, args, f, config)
        # single file or dir
        else:
            log.info(f'pushing to client: {args.client}, file: {args.file}, env: {args.env}')
            _push_file(sftp, args, args.file, config)

    if action == 'pull':
        log.info(f'pulling from client: {args.client}, env: {args.env}')
        _pull_file(sftp, args, config)
    
    sftp.close()