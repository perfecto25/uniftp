#!/opt/uniftp/venv/bin/python3
import sys
import os
import yaml
import argparse
import textwrap
from dictor import dictor
from uniftp import _start_ftp, generate, list_files
from uniftp.globals import BASEDIR, RED, WHITE, RESET, log

parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
    description=textwrap.dedent('''
    UniFTP framework
    ./ftp.py -c clientA -f file.txt -e prod
    ./ftp.py -c clientA -f dir1,file1,file2 -e prod  
    ./ftp.py -g -c clientA   (generate Client config folder skeleton) 
    ./ftp.py -c clientA -e prod -l  (show all files on target side)

    Config YAML options:
    ---
    environment_name:
      action = [push, pull] pushing to or pulling from client (required)
      host = client's FTP hostname or IP    (required)
      port = customer FTP port              (optional)
      username = user to connect with       (required)
      auth_type = authentication type [key, password] (required)
      password = insert password if using password authentication  (optional)
      privkey = path to SSH private key, by default in client's folder (RSA only) (optional)
      enc_type = encrypt file with encryption type [gpg, 7zip] (optional)
      enc_password = encryption password for 7zip (optional)
      remote_path = path where to put file on client's FTP server (optional)
      local_path = path to where you want to save pulled files (optional)
      file_prefix = append prefix to encrypted filename (optional)
      delete_encrypted_files = delete encrypted files after sending them to client [true, false] (default: true)

    '''))

parser.add_argument('--client', '-c', action='store', type=str, required=True, help='name of client')
parser.add_argument('--file', '-f', action='store', type=str, help='file or directory to FTP to client, can specify multiple items with comma separator')
parser.add_argument('--env', '-e', action='store', type=str, help='environment for FTP transfer; prod, uat, etc')
parser.add_argument('--generate', '-g', action='store_true', help='generate client folder structure')
parser.add_argument('--list', '-l', action='store_true', help='show all files on client\'s FTP side')
args = parser.parse_args()

if __name__ == "__main__":

    if args.generate:
        if not args.client:
            sys.exit(f'{RED}provide a Client name to generate folder structure{RESET}')
        generate(args.client)

    if not args.env:
        sys.exit(f'{RED}provide an Environment for FTP transfer{RESET}')

    # get config dict from YAML
    with open(f'{BASEDIR}/clients/{args.client}/config.yml', "r") as file:
        try:
            conf = yaml.load(file, Loader=yaml.FullLoader)
            config = dictor(conf, f'{args.env}', checknone=True)
        except yaml.YAMLError as excep:
            log.error(f'({RED} {str(excep)} {RESET}')
            sys.exit(f'({RED} {str(excep)} {RESET}')    

    if args.list:
        print('listing files')
        files = list_files(args, config)
        print(f'{WHITE}{files}{RESET}')
        sys.exit()
    
    if not args.file and dictor(config, 'action') == 'push':
        sys.exit(f'{RED}provide an File for FTP transfer:{RESET} -f file')

    if not os.path.exists(f'{BASEDIR}/clients/{args.client}/config.yml'):
        sys.exit(f'{RED}Client FTP configuration does not exist, run "--generate" to create a sample config{RESET}')

    _start_ftp(args, config)