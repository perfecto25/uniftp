import os
import sys
import logging
import jinja2
import smtplib
import socket
import inspect
import traceback
from email.message import EmailMessage

BASEDIR = os.path.dirname(os.path.dirname( __file__ ))
USER = 'uniftp'
GROUP = 'uniftp' 
GPGHOME = BASEDIR + '/.gnupg'
DEBUG = True
EMAIL_ON_ERROR = False
EMAIL_TO = 'admin@company.com'
EMAIL_FROM = 'uniFTP'

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
handler = logging.FileHandler(BASEDIR+'/ftp.log')
formatter = logging.Formatter('[%(levelname)s] %(asctime)s >> %(message)s')
handler.setFormatter(formatter)
log.addHandler(handler)

# Terminal Colors
class txt: 
    reset='\033[0m'
    bold='\033[01m'
    disable='\033[02m'
    underline='\033[04m'
    reverse='\033[07m'
    strikethrough='\033[09m'
    invisible='\033[08m'
    class fg: 
        black='\033[30m'
        red='\033[31m'
        green='\033[32m'
        orange='\033[33m'
        blue='\033[34m'
        purple='\033[35m'
        cyan='\033[36m'
        white='\033[37m'
        lightgrey='\033[37m'
        darkgrey='\033[90m'
        lightred='\033[91m'
        lightgreen='\033[92m'
        yellow='\033[93m'
        lightblue='\033[94m'
        pink='\033[95m'
        lightcyan='\033[96m'
    class bg: 
        black='\033[35m'
        red='\033[41m'
        green='\033[42m'
        orange='\033[43m'
        blue='\033[44m'
        purple='\033[45m'
        cyan='\033[46m'
        lightgrey='\033[47m'
        white='\033[007m'

RED = f'{txt.bg.black}{txt.bold}{txt.fg.red}'
GREEN = f'{txt.fg.green}'
CYAN = f'{txt.fg.cyan}'
YELLOW = f'{txt.fg.yellow}'
WHITE = f'{txt.fg.white}'
PURPLE = f'{txt.bg.black}{txt.bold}{txt.fg.purple}'
ORANGE = f'{txt.bg.black}{txt.bold}{txt.fg.orange}'
RESET = f'{txt.reset}'

def _error_handler(exception, args, config, comment=None):
    if DEBUG:
        print(f'{YELLOW}{inspect.getouterframes( inspect.currentframe() )[1]}{RESET}')
        #mport pdb; pdb.set_trace()
        template = "An exception of type {0} occurred. Arguments:\n{1!r}"
        message = template.format(type(exception).__name__, exception.args)
        print(f'{ORANGE}{type(exception).__name__} , {exception.args}: \n\n {RESET}')
        print(f'{RED}{comment}\n{traceback.format_exc()}{RESET}')
        log.error(exception)
        log.error(traceback.format_exc())
        
        v = {}
        v['exception'] = exception.args
        v['traceback'] = traceback.format_exc()
        v['client'] = args.client
        v['env'] = args.env

        if EMAIL_ON_ERROR:
            html = render_template(BASEDIR+'/uniftp/email.j2', v=v)
            send_email(to_addr=EMAIL_TO, from_addr=EMAIL_FROM, smtp_host='localhost', subject='uniFTP Error', body=html)
            
        sys.exit()
    else:
        sys.exit(f'{RED}[ERROR] {comment}\n\n{exception}{RESET}')



def render_template(template, **kwargs):
    ''' renders a Jinja template into HTML '''
    # check if template exists
    if not os.path.exists(template):
        log.error('No template file present: %s' % template)
        return 'error'

    templateLoader = jinja2.FileSystemLoader(searchpath="/")
    templateEnv = jinja2.Environment(loader=templateLoader)
    templ = templateEnv.get_template(template)
    return templ.render(**kwargs)

def send_email(to_addr, from_addr, smtp_host, cc=None, bcc=None, subject=None, body=None):
    
    if not to_addr or not from_addr:
        log.error('error sending email, To or From values are null')
        return 'error'

    # convert TO into list if string
    if type(to_addr) is not list:
        to_addr = to_addr.split()

    to_list = to_addr + [cc] + [bcc]
    to_list = filter(None, to_list) # remove null emails

    msg = EmailMessage()
    msg['From']    = from_addr
    msg['Subject'] = subject
    msg['To']      = ','.join(to_addr)
    msg.set_content(body, 'html')
    try:
        s = smtplib.SMTP(smtp_host)
    except smtplib.SMTPAuthenticationError as e:
        log.error('Error authenticating to SMTP server: %s, exiting.., %s' % (smtp_host, str(e)))
        return 'error'
    except socket.timeout:
        log.error('SMTP login timeout')
        return 'error'
        
    try:
        s.send_message(msg)
    except smtplib.SMTPException as e:
        log.error('Error sending email')
        log.error(str(e))
    finally:
        s.quit()