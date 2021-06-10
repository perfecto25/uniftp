# UNIFTP - Universal FTP framework

![Alt text](logo.png)

FTP framework in Python3

works for variety of FTP requirements

UniFTP can

1. connect to a target and upload a file or directory
1. can pull a file or directory from a target
1. can encrypt a file in 7zip or GPG format and upload to target
1. check what files are present on target's side
1. comes with wide variety of configuration options in a YAML config file

## Installation

git clone this repo

    cd /opt
    git clone repo

create Virtual Env and install requirements

    cd uniftp
    python3 -m venv venv
    source venv/bin/activate
    python3 -m pip install --upgrade pip
    python3 -m pip install -r requirements.txt

update ftp.py shebang to point to the python3 directory where this repo is sitting on

    vi ftp.py

    change shebang to:

    #!/opt/uniftp/venv/bin/python3

---

## Configuration

UniFTP works by reading a YAML config file for each target you want to connect to.

To generate a sample client config in order to connect to a client

    ./ftp.py -c someClient --generate

This will create a new configuration file in clients/someClient/config.yaml

Update options in this file,

```
# specify connection environment (prod, uat, dev, etc)
prod:

  # push to client or pull from client [push, pull]
  action: push

  # hostname or IP of target
  host: ftp.client.com

  # comment out to use default port 22
  port: 2022

  # username for all auth types
  username: joe

  # password or ssh-key authentication, can only use one [password, key]
  auth_type: password

  # if using password, specify password
  password: mySecretPassword

  # if using ssh-key, specify name of private key
  # UniFTP will search path specified for private key, if not found, will search inside clients/CLIENT/ folder for key
  privkey: client.priv

  # if you want to encrypt your file, can use 7zip or GPG [7zip, gpg]
  enc_type: 7zip

  # to encrypt 7zip, use password or comment out
  enc_password: 7zipSecretPassword

  # if you'd like to upload file to specific path on target server
  remote_path: /uploads

  # if you want to download a file to specific path on your host server
  local_path: /home/user/downloads

  # if you'd like to add a prefix to your encrypted file name
  file_prefix: my_file_

  # once encrypted files are sent to target, delete them from /clients/CLIENT/encrypted folder [true, false]
  delete_encrypted_files: 'true'
```

---

### Authentication to Client

to authenticate using username password, configure _auth_type_ key to 'password' and provide username and password

    username: user
    auth_type: password
    password: myPassword

to use SSH keys, set _auth_type_ to 'key' and provide path to the Private key for 'privkey'

    username: user
    auth_type: key
    privkey: id_rsa (uniftp will look for keys in clients/client/sshkeys)

    ## or if keys are located on some other path:

    privkey: /home/user/.ssh/id_rsa

SSH keypair can either be external, ie `/home/user/.ssh/id_rsa `

or be placed in `clients/client/sshkeys/`

---

### GPG encryption

place client GPG asc keys into `clients/CLIENT/gpgkeys` folder

the keys will be imported by uniftp

---

### Alert on Error

UniFTP can email you if theres an error during an FTP process.

open up uniftp/globals.py and enable email

    EMAIL_ON_ERROR = True
    EMAIL_TO = 'admin@company.com'
