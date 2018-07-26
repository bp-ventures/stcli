#!/usr/bin/env python
# -*- coding:utf-8 -*-
'''
@author: ‘ant‘
@site: tempo.eu.com
@file: stcli.py
@time: 2018-06-10

# The MIT License
#
# Copyright (c) 2018 anthony barker.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND
PEP E401, E501 and E701 ignored
'''
from __future__ import unicode_literals, print_function
import requests, json, sys, os
import toml
from prompt_toolkit import prompt
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from stellar_base.builder import Builder, HORIZON_TEST, HORIZON_LIVE
from stellar_base.keypair import Keypair
from stellar_base.address import Address, AccountNotExistError
from prompt_toolkit import print_formatted_text, HTML
#optional
import pyqrcode
PT = os.path.dirname(os.path.realpath(__file__))
PTZ = PT + '/stcli.zip'
PTC = PT + '/stcli.conf'
CONF = {}
compl = WordCompleter(['?', 'create', 'help', 'send', 'receive', 'trust',
                      'asset', 'deposit', 'withdrawal', 'settings', 'balance', 'version'], ignore_case=True)
session = PromptSession(history=FileHistory('.myhistory'))
VERSION = '0.1.5'

def load_conf():
    global CONF
    print('using: ' + PT)
    if not os.path.isfile(PTC):
        if os.path.isfile(PTZ):
            unzip()
    if not os.path.isfile(PTC):
        create_conf()
    os.chmod(PTC, 0o700)
    with open(PTC, 'r') as fp:
        CONF = toml.loads(fp.read())


def unzip():
    os.system('unzip -j -o '+ PTZ)


def zipfile(passw):
    os.chmod(PTC, 0o700)
    if os.path.isfile(PTZ):
        cmd = "zip -u --password %s -m %s %s" % (passw, PTZ, PTC)
    else:
        cmd = "zip --password %s -m %s %s" % (passw, PTZ, PTC)
    print('zip --password ******* -m %s %s' % (PTZ, PTC))
    os.system(cmd)
    os.chmod(PTZ, 0o700)


def set_private_key():
    print('set private key')
    if CONF['private_key'] != "":
        f = prompt('You have a private key... over ride for this session? (y/n)')
        if f.lower() != 'y': return
    CONF['private_key'] = prompt('Enter private key(masked): ', is_password=True)
    c = Keypair.from_seed(CONF['private_key'])
    CONF['public_key'] = c.address().decode('ascii')
    CONF['network'] = 'PUBLIC'
    with open(PTC, 'w') as fp:
        fp.write(toml.dumps(CONF))
    os.chmod(PTC, 0o700)
    print("set conf... to display conf type conf")
    return


def create_conf():
    with open(PTC, 'w') as fp:
        fp.write('public_key = ""\nprivate_key = ""\nnetwork = "TESTNET"\nlanguage ' +
                 '= "ENGLISH"\nstellar_address = ""\nairdrop="t"\npartner_key=""\n'+
                 'multisig=""')
    load_conf()
    os.chmod(PTC, 0o700)
    return


def fund():
    if CONF['public_key'] == '': create_wallet()
    if CONF['network'] == 'PUBLIC':
        print("Can only fund on Stellar testnet")
        return
    print('... asking friendbot for some test lumens. after remember to trust an asset')
    r = requests.get('https://friendbot.stellar.org/?addr=' + CONF['public_key'])
    print(r.text)


def set_account(settype, var1):
    print('set account')
    sa = Builder(CONF['private_key'], network=CONF['network'])
    if settype == 'inflation':
        sa.append_set_options_op(inflation=var1)
    else:
        sa.append_set_options_op(home_domain=var1)
    sa.sign()
    sa.submit()


def set_var(text):
    cmd = text.split()
    var = cmd[1].split('=')
    if var[0] in ['inflation','home_domain']:
        set_account(var[0], var[1])
        return
    if var[0] in ['multisig']:
        set_multisig(var[1])
    if len(var) < 2:
        print('format is set var=val')
        return
    print(text)
    CONF[var[0]] = var[1]
    with open(PTC, 'w') as fp:
        fp.write(toml.dumps(CONF))
    list_balances()


def create_wallet():
    print('creating keys...')
    kp = Keypair.random()
    if CONF['network'] == 'PUBLIC':
        print_formatted_text(HTML('<ansiyellow>WARNING YOU NEED TO FUND AND BACKUP YOUR PRIVATE KEY!</ansiyellow>'))
    else:
        print('.. on testnet... hit f after this to fund')
    print('Public key this is where people send funds to. You need to fund with some lumens to get started\n')
    print_formatted_text(HTML('<ansired>' + kp.address().decode('ascii') + '</ansired>'))
    print('\nPrivate key please ensure you store securely\n')
    print_formatted_text(HTML('<ansiyellow>' + kp.seed().decode('ascii') + '</ansiyellow>'))
    from stellar_base.utils import StellarMnemonic
    sm = StellarMnemonic(CONF['language'].lower())
    secret_phrase = sm.generate()
    print('\n if you loose your key you can recreate it with this special passphrase:\n')
    print(secret_phrase)
    print('')
    print('> if you want to store this hit y')
    text = session.prompt(u'> y')
    if text.lower() == 'n':
        return
    # todoo update config
    if CONF['public_key'] != '':
        print('only one public key is currently supported')
        return
    CONF['public_key'] = kp.address().decode('ascii')
    CONF['private_key'] = kp.seed().decode('ascii')
    with open(PTC, 'w') as fp:
        fp.write(toml.dumps(CONF))
    if CONF['network'] != 'TESTNET':
        print('configuration saved - please remember to fund by sending a couple of lumens')


def list_balances(check_asset=''):
    #print('Using public key: ' + CONF['public_key'])
    c = Address(CONF['public_key'], network=CONF['network'])
    try:
        c.get()
    except AccountNotExistError:
        print_formatted_text(HTML('<ansiyellow>unfunded account... </ansiyellow> ' +
                             'you need to hit <ansiblue>f to fund for testnet or type key for public</ansiblue> '))
        return
    r = requests.get("https://api.coinmarketcap.com/v1/ticker/stellar/?convert=EUR")
    rate = r.json()[0]
    #  print('.. rate ' + str(rate))
    for x in c.balances:
        if x['asset_type'] == 'native':
            if check_asset != '': continue
            usd_val = float(rate['price_usd']) * float(x['balance'])
            eur_val = float(rate['price_eur']) * float(x['balance'])
            print_formatted_text(HTML('XLM: <ansiblue>' + x['balance'] + '</ansiblue> value: USD:' + "{:.2f}".format(usd_val)
                  + ' EUR:' + "{:.2f}".format(eur_val)))
        else:
            if check_asset != '':
                if check_asset.upper() == x['asset_code'].upper():
                    return True
            else:
                print_formatted_text(HTML(x['asset_code'] + ' <ansiblue>' + x['balance'] + '</ansiblue>'))
    if check_asset != '': return False


def list_assets():
    print('list assets')
    url = 'https://raw.githubusercontent.com/stellarterm/stellarterm/master/directory/directory.json'
    r = requests.get(url)
    b = json.loads(r.text)
    #    print(asset)
    for x in b['anchors']:
        print(b['anchors'][x]['name']+":")
        ass = ''
        for y in b['anchors'][x]['assets'].keys():
            ass += y + ' '
        print_formatted_text(HTML('<ansired>' + ass + '</ansired>'))
    print('trust domain asset .. e.g. trust tempo.eu.com EURT')


def trust_asset(text):
    if CONF['private_key'] == '':
        print('no private key setup  - use set to set key or c to create wallet')
        return
    val = text.split(' ')
    if len(val) != 3:
        print('invalid syntax please use trust anchor asset')
        return
    url = 'https://raw.githubusercontent.com/stellarterm/stellarterm/master/directory/directory.json'
    r = requests.get(url)
    b = json.loads(r.text)
    asset_name = val[-1].upper()
    asset_anchor = val[1]
    try:
        asset_key = b['anchors'][asset_anchor]['assets'][asset_name].split('-')[1]
    except:
        print('unabled to find anchor or asset so quiting trust')
        return
    trst = Builder(CONF['private_key'], network=CONF['network'])
    if val[0] == 'trust':
        print('trusting.. ' + asset_name + ' ' + asset_key)
        trst.append_trust_op(asset_key, asset_name)
    else:
        print('untrust ' + asset_name + ' ' + asset_key + ' please ensure your balance is 0 before this operation')
        trst.append_trust_op(asset_key, asset_name, limit=0)
    trst.sign()
    trst.submit()


def print_help():
    print("""
    NAME
           stcli - a repl command line crypto wallet for stellar that is simple and all in one file

    SYNOPSIS

            DESCRIPTION
                                                     COMMAND OPTIONS
                r [receive] - displays the public key and or federated address
                s [send] amount asset address memo [text|id] e.g. s 1 XLM antb123*papayame.com
                b [balances] - shows the balances of all assets
                t [trust] - shows the trust lines and allows trust of new assets
                u [untrust] - allows remove of trust lines were the balance is 0
                l [list] assets - shows all the assets known to stellarterm
                c [create] - creates a new private and public keypair
                k [key] - sets private key
                f [fund] - fund a testnet address
                h [history] - history of transactions
                v [version] - displays version
                pp [paymentpath] - allows you to play with path payments (in beta)
                q [quit] - quit app
                deposit - brings up deposit menu  e.g. d tempo.eu.com eurt
                withdrawal - brings up withdrawal menu w tempo.eu.com eurt
                conf - prints configuration
                set key=var .. e.g. set network=PUBLIC (do not use for private key - use k)
                set inflation=tempo.eu.como not use for private key - use k)
                set multisig=GPUBKEY sets a public key for multisig)

     AUTHOR:
            Put together by Anthony Barker for testing purposes
    """)


def receive():
    text = pyqrcode.create(CONF['public_key'])
    print(text.terminal())
    print_formatted_text(HTML('\n to receive send funds to <ansiyellow>' +
                         CONF['public_key'] + '</ansiyellow> wth no memo and network is ' + CONF['network'] +
                         ' for crypto (BTC ETH) you need to trust and deposit or buy via pp'))
    if CONF['stellar_address'] != "":
        print_formatted_text(HTML('or they can send to your federated key'
                             + CONF['stellar_address'] + '</ansired>\n\n'))


def horiz_lp():
    if CONF['network'] == 'PUBLIC': return HORIZON_LIVE
    return HORIZON_TEST


def history():
    c = Address(CONF['public_key'], network=CONF['network'])
    c.get()
    h = c.payments(limit=30, order='desc')
    for x in h[u'_embedded']['records']:
        if x['type'] == 'create_account':
            print(x['created_at'] + ' ' + x['type'] + ' start ' + x['starting_balance'] + '\n'
                  + horiz_lp() + '/operations/' + x['id'])
        else:
            print(x['created_at'] + ' ' + x['type'] + ' ' + x['to'] + ' ' + x['from'] + ' ' + x['amount'] +
                  '\n' + horiz_lp() + '/operations/' + x['id'])


def fed(domain, address):
    FED = toml.loads(requests.get('https://' + domain + '/.well-known/stellar.toml').text)
    data = {'q': address, 'type': 'name'}
    print('getting federation with ' + FED['FEDERATION_SERVER'] + " " + address)
    r = requests.get(url=FED['FEDERATION_SERVER'], params=data)
    print(r.text)
    return r.json()


def get_balance_issuer(amount, asset):
    if asset == 'XLM': return 0, ""
    c = Address(CONF['public_key'], network=CONF['network'])
    c.get()
    for b in c.balances:
        if asset == b['asset_code']:
            if float(b['balance']) < float(amount):
                print('error insufficient funds')
                return 1, b['asset_issuer']
            else:
                return 0, b['asset_issuer']


def send_sanity(addr, memo_type, asset):
    if asset == 'BTC': return True
    r = requests.get('https://raw.githubusercontent.com/stellarterm/stellarterm/master/directory/directory.json')
    b = r.json()
    if addr not in b['destinations']:
        return True
    match = b['destinations'][addr]
    print(match)
    memot = 'MEMO_' + memo_type.upper()
    if 'requiredMemoType' in match:
        if memot != match['requiredMemoType']:
            print('invalid memo type ' + match['name'] + ' requires ' + match['requiredMemoType'])
            return False
    if 'acceptedAssetsWhitelist' in match:
        if asset[:3] != match['acceptedAssetsWhitelist'][:3]:
            print('it looks like you are sending an asset the destination does not accept ')
            return False
    return True


def send_asset(text):
    # send 10 EURT antb123*papayame.com or send 1 XLM PUBKEY memo text
    if CONF['private_key'] == '':
        print('no private key setup  - pls type set to set key or c to create wallet')
        return
    val = text.split()
    memo_type = 'text'
    if len(val) < 3:
        print('invalid syntax please use send amount asset receiver e.g.  s 10 EURT antb123*papayame.com')
        return
    amount, asset, address = val[1], val[2].upper(), val[3]
    if '*' in address:
        res = fed(address.split('*')[1], address)
        sendto = res['account_id']
        memo = res['memo']
        memo_type = res['memo_type']
    else:
        sendto = address
        memo = ''
    # override memo, type if given
    if len(val) == 6:
        memo = val[4]
        memo_type = val[5]
    if len(val) == 5:
        memo = val[4]
        memo_type = 'text'
    print_formatted_text(HTML("""Are you sure you want to send
                                <ansiyellow>%s</ansiyellow>
                                <ansired>%s %s</ansired>
                                with memo of <ansiblue>%s</ansiblue> (y/n)
                                """ % (sendto, asset, amount, memo)))
    text = session.prompt(u'> ', default='y')
    if text != 'y': return
    ret, asset_issuer = get_balance_issuer(amount, asset)
    if ret: return
    retsan = send_sanity(sendto, memo_type, asset)
    if not retsan: return
    send = Builder(CONF['private_key'], network=CONF['network'])
    if asset != 'XLM':
        send.append_payment_op(sendto, amount, asset, asset_issuer)
    else:
         send.append_payment_op(sendto, amount)
    if memo != '' and memo_type == 'text':
        send.add_text_memo(memo)
    if memo != '' and memo_type == 'id':
        send.add_id_memo(memo)
    if CONF['multisig'] != '':
        print('You have 2of2 multisig - send this data to the other key to sign when you get it back type signsend data')
        print(send.gen_xdr())
        return
    send.sign()
    send.submit()


def signsend(text):
    cont = session.prompt(u'You want to sign or send? (sign/send) > ')
    data = text.split()[1]
    if cont.lower() == 'sign':
        print(' signing ' + data)
        sign = Builder(CONF['private_key'], network=CONF['network'])
        sign.import_from_xdr(data)
        #key = session.prompt(u'Enter who you sign for? %s > ' % CONF['multisig'])
	sign.sign()
	print("send this to the other wallet and ask them to signsend it\n")
	print(sign.gen_xdr())
        return
    print(' signing and sending ' + data)
    c = Builder(CONF['private_key'], network=CONF['network'])
    c.import_from_xdr(data)
    c.sign()
    data = c.submit()
    print(data)
    return


def start_app():
    print_formatted_text(HTML('### WELCOME TO <ansired>stcli</ansired> - '
                         + 'type <ansiblue>?</ansiblue> or help for commands ####\n\n'))
    load_conf()
    try:
        if 'private_key' not in CONF:
            create_conf()
    except:
        print('no wallet? type k [key] to set the private key or c [create] to create wallet')
    try:
        print_formatted_text(HTML('Public key: <ansiyellow>' + CONF['public_key']
                             + '</ansiyellow> network: ' + CONF['network']))
    except:
        create_conf()
        print('using public key:' + CONF['public_key'] + 'network: ' + CONF['network'])
    list_balances()


def path_payment(text):
        print('..checking path payment options not yet implemented')


def deposit(text):
    print_formatted_text(HTML('<ansiblue>\n### DEPOSIT ###</ansiblue>\n'))
    print("Deposit servers allow you to cash in assets into your wallet. We support naobtc.com, apay.io and tempo.eu.com")
    print("you need to trust the asset before depositing.. eg. trust api.io BCH")
    r = text.split()
    if len(r) > 2:
        server = text.split()[1]
        asset =  text.split()[2].upper()
        print("deposit to " + server + " asset " + asset)
    else:
        print("server asset e.g. apay.io bch or naobtc.com btc")
        res = session.prompt(u'server asset > ')
        try:
            server, asset = res.split()[0], res.split()[1]
        except:
            print('format error')
            return
    if server not in ['tempo.eu.com','apay.io','naobtc.com']:
        print('error ' + server + ' unsupported')
        return
    print_formatted_text(HTML('<ansiyellow>' + asset + '</ansiyellow> will be send to: <ansiyellow>' + CONF['public_key']
                             + '</ansiyellow> network: ' + CONF['network']))
    if not list_balances(check_asset=asset):
        print('ERROR need to trust asset: type trust %s %s' % (server, asset))
        return
    FED = toml.loads(requests.get('https://' + server + '/.well-known/stellar.toml').text)
    deposit_server= FED['DEPOSIT_SERVER']
    param = {}
    param['asset_code'] = asset.upper()
    param['account'] = CONF['public_key']
    if server == 'apay.io':
        deposit_server += '/deposit'
        #url = '%s?asset_code=%s&account=%s' % (deposit_server, asset.upper(), CONF['public_key'])
    elif server == 'tempo.eu.com':
        param['email'] = session.prompt(u' email address > ')
        param['method'] = 'sepa' #session.prompt(u'method default: sepa (sepa, swift, cash, unistream) > ', default='sepa')
        print('deposit needs to happen using sepa')
        #url = '%s?asset_code=%s&account=%s&email=%s' % (deposit_server, asset.upper(), CONF['public_key'], email)
    else:
        pass
    #    url = '%s?asset_code=%s&account=%s' % (deposit_server, asset.upper(), CONF['public_key'])
    #print('getting deposit info from ' + url)
    print(param)
    cont = session.prompt(u'Are you sure? (y/n) > ')
    if cont.lower() != 'y': return
    r = requests.get(deposit_server, params=param)
    print(r.url)
    res = r.json()
    if server in['apay.io', 'naobtc.com']:
        text = pyqrcode.create(res['how'])
        print(text.terminal())
    print(res)
    min_amount = str(res.setdefault('min_amount', ''))
    max_amount = str(res.setdefault('max_amount', ''))
    print_formatted_text(HTML('\nSEND ' + asset + ' to <ansiyellow> ' + res['how'] + ' </ansiyellow> you have '
                         + str(int(res['eta']/60)) + ' min to make the payment. Amount min ' + asset + ' ' +
                         min_amount + ' and max ' + max_amount  + ' ' + res['extra_info']))
    return


def set_multisig(trusted_key):
    print_formatted_text(HTML('<ansiblue>\n### SET MULTISIG ###</ansiblue>\n'))
    print('set multisig will currently make your key a 2 of 2 multisig address')
    print_formatted_text(HTML('trusted key is:<ansired>'+ trusted_key +'</ansired>'))
    print('it will set med threshold and high to 2 and master weight to 1 so you can use 2 keys for all sending or issuing tokens\n\n')
    b = Builder(CONF['private_key'], network=CONF['network'])
    b.append_set_options_op(master_weight=1,
			med_threshold=2,
			high_threshold=2,
			signer_address=trusted_key,
			signer_type='ed25519PublicKey',
			signer_weight=1,
			source=None)
    b.sign()
    val = b.submit()
    print(val)
    return



def withdrawal(text):
    print_formatted_text(HTML('<ansiblue>\n### WITHDRAWAL ###</ansiblue>\n'))
    print('withdrawal allows you to remove assets from your wallet such as EUR, BCH, BTC')
    r = text.split()
    if len(r) > 2:
        server = text.split()[1]
        asset =  text.split()[2]
    else:
        print("server asset e.g. tempo.eucom eurt, apay.io bch or naobtc.com btc")
        res = session.prompt(u'server asset> ')
        try:
            server, asset = res.split()[0], res.split()[1]
        except:
            print('format error')
            return
    if server not in ['tempo.eu.com','apay.io','naobtc.com','flutterwave.com']:
        print('error ' + server + ' unsupported')
        return
    print_formatted_text(HTML('<ansiyellow>' + asset + '</ansiyellow> withdrawal from <ansiyellow>'
                         + server + '</ansiyellow> network: ' + CONF['network']))
    FED = toml.loads(requests.get('https://' + server + '/.well-known/stellar.toml').text)
    #print(FED)
    param = {}
    param['type'] = 'forward'
    if server == 'tempo.eu.com':
        print_formatted_text(HTML('withdrawal is <ansiyellow>sepa</ansiyellow>'))
        param['email'] = session.prompt(u'email address > ')
        param['iban'] = session.prompt(u'iban > ')
        param['swift'] = session.prompt(u'swift/bic > ')
        param['receiver_name'] = session.prompt(u'receiver name > ')
        param['forward_type'] = 'bank_account'
        #url = '%s?type=forward&forward_type=bank_account&iban=%s&swift=%s&email=%s' % (FED['FEDERATION_SERVER'],iban,swift,email)
        #url = '%s?type=forward&iban=%s&swift=%s&email=%s' % (FED['FEDERATION_SERVER'],iban,swift,email)
    else:
        param['account'] = session.prompt(u'crypto destination account > ')
        #url = FED['FEDERATION_SERVER'] +'?type=forward&account=%s' % account
    #print('getting federation with ' + url)
    print(param)
    cont = session.prompt(u'Are you sure? (y/n) > ', default='n')
    if cont.lower() != 'y': return
    r = requests.get(FED['FEDERATION_SERVER'], params=param)
    print(r.url)
    res = r.json()
    print(res)
    #print_formatted_text(HTML('\nSEND ' + asset + ' to <ansiyellow> ' + res['how'] + ' </ansiyellow>you have ' + str(int(res['eta']/60))
    #                     + ' min and ' + res['extra_info']))
    return

def sys_exit():
    saveconf = session.prompt(u'save zip encrypted configuration (y/n)> ')
    if saveconf.lower() == 'y':
        passw = prompt('password for conf file: ', is_password=True)
        zipfile(passw)
    sys.exit()


if __name__ == "__main__":
    start_app()
    while True:
        text = session.prompt(u'> ', completer=compl, complete_while_typing=True,
                              vi_mode=True, auto_suggest=AutoSuggestFromHistory())
        if text == 'help' or text == '?': print_help()
        elif text == '': continue
        elif text == 'create' or text == 'c': create_wallet()
        elif text == 'balance' or text == 'b': list_balances()
        elif text == 'history' or text == 'h': history()
        elif text[:8] == 'signsend': signsend(text)
        elif text == 'quit'or text == 'q': sys_exit()
        elif text == 'key'or text == 'k': set_private_key()
        elif text == 'receive'or text == 'r': receive()
        elif text == 'fund'or text == 'f': fund()
        elif text == 'list'or text == 'l': list_assets()
        elif text == 'conf': print(toml.dumps(CONF))
        elif text.split(" ")[0] == 'set':
            set_var(text)
        elif text == 'version' or text == 'v': print('VERSION: ' + VERSION)
        elif text[0] == 'd': deposit(text)
        elif text[0] == 'w': withdrawal(text)
        elif text[0] == 't': trust_asset(text)
        elif text[0] == 'u': trust_asset(text)
        elif text[0] == 's': send_asset(text)
        elif text[0] == '!': os.system(text[1:])
        else:
            print('You entered:', text)
