#!/usr/bin/python3
from __future__ import unicode_literals, print_function
import base64
import time
import webbrowser
import requests
import json
import sys
import os
import toml
import platform
from prompt_toolkit import prompt
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from stellar_sdk.server import Server
from stellar_sdk import Asset, TransactionEnvelope, exceptions as stellar_exceptions
from stellar_sdk.keypair import Keypair
from stellar_sdk.sep.mnemonic import StellarMnemonic
from stellar_sdk.transaction_builder import TransactionBuilder
from stellar_sdk.network import Network

# from stellar_sdk.xdr import SignerKey
from prompt_toolkit import print_formatted_text, HTML

# optional
import pyqrcode

PT = os.path.dirname(os.path.realpath(__file__))
PTZ = PT + "/stcli.zip"
PTC = PT + "/stcli.conf"
CONF = {}
compl = WordCompleter(
    [
        "?",
        "create",
        "help",
        "send",
        "receive",
        "trust",
        "asset",
        "deposit",
        "withdrawal",
        "settings",
        "balance",
        "version",
    ],
    ignore_case=True,
)
session = PromptSession(history=FileHistory(".myhistory"))
VERSION = "0.1.5"


def get_stellar_toml(asset, asset_issuer=None):
    if asset_issuer is None:
        _asset_issuer = get_asset_issuer(asset)
    else:
        _asset_issuer = asset_issuer
    if _asset_issuer is not None:
        url = horizon_url()
        _url = url + "accounts/" + _asset_issuer
        response = requests.get(_url).json()
        try:
            # home_domain = response["home_domain"]
            home_domain = "netxd-sb-anchor.bpventures.us"
            if home_domain is not None:
                _toml = toml.loads(
                    requests.get(
                        "https://" + home_domain + "/.well-known/stellar.toml"
                    ).text
                )
                return _toml
            return None
        except Exception as e:
            print(e)
            return None


def load_conf():
    global CONF
    print("using: " + PT)
    if not os.path.isfile(PTC):
        if os.path.isfile(PTZ):
            unzip()
    if not os.path.isfile(PTC):
        create_conf()
    os.chmod(PTC, 0o700)
    with open(PTC, "r") as fp:
        CONF = toml.loads(fp.read())


def unzip():
    os.system("unzip -j -o " + PTZ)


def zipfile(passw):
    os.chmod(PTC, 0o700)
    if os.path.isfile(PTZ):
        cmd = "zip -u --password %s -m %s %s" % (passw, PTZ, PTC)
    else:
        cmd = "zip --password %s -m %s %s" % (passw, PTZ, PTC)
    print("zip --password ******* -m %s %s" % (PTZ, PTC))
    os.system(cmd)
    os.chmod(PTZ, 0o700)


def set_private_key():
    print("set private key")
    if CONF["private_key"] != "":
        f = prompt("You have a private key... over ride for this session? (y/n)")
        if f.lower() != "y":
            return
    CONF["private_key"] = prompt("Enter private key(masked): ", is_password=True)
    CONF["public_key"] = keypair().public_key
    CONF["network"] = "PUBLIC"
    with open(PTC, "w") as fp:
        fp.write(toml.dumps(CONF))
    os.chmod(PTC, 0o700)
    print("set conf... to display conf type conf")
    return


def create_conf():
    with open(PTC, "w") as fp:
        fp.write(
            'public_key = ""\nprivate_key = ""\nnetwork = "TESTNET"\nlanguage '
            '= "ENGLISH"\nstellar_address = ""\nairdrop="t"\npartner_key=""\n'
            'multisig=""'
        )
    load_conf()
    os.chmod(PTC, 0o700)
    return


def keypair():
    return Keypair.from_secret(CONF["private_key"])


def fund():
    if CONF["public_key"] == "":
        create_wallet()
    if CONF["network"] == "PUBLIC":
        print("Can only fund on Stellar testnet")
        return
    print("... asking friendbot for some test lumens. after remember to trust an asset")
    try:
        r = requests.get("https://friendbot.stellar.org/?addr=" + CONF["public_key"])
        print(r.text)
    except Exception as e:
        if e.status == 400:
            print("already funded")
        else:
            print(e)


def fetch_base_fee():
    try:
        return server().fetch_base_fee()
    except (
        stellar_exceptions.ConnectionError,
        stellar_exceptions.NotFoundError,
        stellar_exceptions.BadRequestError,
        stellar_exceptions.BadResponseError,
        stellar_exceptions.UnknownRequestError,
    ):
        return 300


def transaction_builder():
    account = server().load_account(CONF["public_key"])
    return TransactionBuilder(
        source_account=account,
        network_passphrase=network_passphrase(),
        base_fee=fetch_base_fee(),
    ).set_timeout(30)


def set_account(settype, var1):
    return


def set_var(text):
    return


def create_wallet():
    print("creating keys...")
    kp = Keypair.random()
    if CONF["network"] == "PUBLIC":
        print_formatted_text(
            HTML(
                "<ansiyellow>WARNING YOU NEED TO FUND AND BACKUP YOUR PRIVATE KEY!</ansiyellow>"
            )
        )
    else:
        print(".. on testnet... hit f after this to fund")
    print(
        "Public key this is where people send funds to. You need to fund with some lumens to get started\n"
    )
    print_formatted_text(HTML("<ansired>" + kp.public_key + "</ansired>"))
    print("\nPrivate key please ensure you store securely\n")
    print_formatted_text(HTML("<ansiyellow>" + kp.secret + "</ansiyellow>"))
    sm = StellarMnemonic(CONF["language"].lower())
    secret_phrase = sm.generate()
    print(
        "\n if you loose your key you can recreate it with this special passphrase:\n"
    )
    print(secret_phrase)
    print("")
    print("> if you want to store this hit y")
    text = session.prompt("> y")
    if text.lower() == "n":
        return
    # todoo update config
    if CONF["public_key"] != "":
        print("only one public key is currently supported")
        return
    CONF["public_key"] = kp.public_key
    CONF["private_key"] = kp.secret
    with open(PTC, "w") as fp:
        fp.write(toml.dumps(CONF))
    if CONF["network"] != "TESTNET":
        print(
            "configuration saved - please remember to fund by sending a couple of lumens"
        )


def list_balances(check_asset=""):
    try:
        account = server().accounts().account_id(CONF["public_key"]).call()
    except stellar_exceptions.NotFoundError:
        print_formatted_text(
            HTML(
                "<ansiyellow>unfunded account... </ansiyellow> "
                "you need to hit <ansiblue>f to fund for testnet or type key for public</ansiblue> "
            )
        )
        return

    res = requests.get(
        "https://api.kraken.com/0/public/Ticker?pair=BTCEUR,XLMEUR,ETHEUR"
    )
    data = res.json()["result"]
    price_eur = data["XXLMZEUR"]["c"][0]
    #  print('.. rate ' + str(rate))
    for record in account["balances"]:
        if (
            record["asset_type"] == "native"
            or record["asset_type"] == "liquidity_pool_shares"
        ):
            if check_asset != "":
                continue
            eur_val = float(price_eur) * float(record["balance"])
            print_formatted_text(
                HTML(
                    "XLM: <ansiblue>"
                    + record["balance"]
                    + "</ansiblue> EUR:"
                    + "{:.2f}".format(eur_val)
                )
            )
        else:
            if check_asset != "":
                if check_asset.upper() == record["asset_code"].upper():
                    return True
            else:
                print_formatted_text(
                    HTML(
                        record["asset_code"]
                        + " <ansiblue>"
                        + record["balance"]
                        + "</ansiblue> EUR:"
                        + "{:.2f}".format(float(price_eur) * float(record["balance"]))
                    )
                )
    if check_asset != "":
        return False


def network_passphrase():
    if CONF["network"] == "PUBLIC":
        return Network.PUBLIC_NETWORK_PASSPHRASE
    else:
        return Network.TESTNET_NETWORK_PASSPHRASE


def print_help():
    print(
        """
    NAME
           stcli - a repl command line crypto wallet for stellar that is simple and all in one file
    SYNOPSIS
            DESCRIPTION
                                            COMMAND OPTIONS
                r [receive] - displays the public key and or federated address
                s [send] amount asset address memo [text|id] e.g. s 1 XLM <address>
                b [balances] - shows the balances of all assets
                c [create] - creates a new private and public keypair
                k [key] - sets private key
                f [fund] - fund a testnet address
                h [history] - history of transactions
                v [version] - displays version
                tt [trust] - trust an asset e.g. t XDUS <asset issuer>
                ut [untrust] - untrust an asset e.g. t XDUS <asset issuer>
                pps [payment path send] - allows you to send path payments e.g. pps <amount> <asset code> <address>  (in beta) 
                ppr [payment path recieve] - allows you to recieve with path payments e.g ppr <amount> <asset code> <address> (in beta)
                deposit - brings up deposit menu  e.g. d tempo.eu.com eurt (sep 24)
                withdrawal - brings up withdrawal menu w tempo.eu.com eurt (sep 24)
                direct transfer - allows you to send direct transfers to a bank account e.g. dt kbtrading.org eurt 10  (sep 31 - in beta)
                conf - prints configuration
                cls [clear] - clears the screen
                q [quit] - quit app
                set key=var .. e.g. set network=PUBLIC (do not use for private key - use k)
                set inflation=tempo.eu.como not use for private key - use k)
                set multisig=GPUBKEY sets a public key for multisig)
     AUTHOR:
            Put together by Anthony Barker for testing purposes
    """
    )


def receive():
    text = pyqrcode.create(CONF["public_key"])
    print(text.terminal())
    print_formatted_text(
        HTML(
            "\n to receive send funds to <ansiyellow>"
            + CONF["public_key"]
            + "</ansiyellow> wth no memo and network is "
            + CONF["network"]
            + " for crypto (BTC ETH) you need to trust and deposit or buy via pp"
        )
    )
    if CONF["stellar_address"] != "":
        print_formatted_text(
            HTML(
                "or they can send to your federated key"
                + CONF["stellar_address"]
                + "</ansired>\n\n"
            )
        )


def horizon_url():
    if CONF["network"] == "PUBLIC":
        return "https://horizon.stellar.org/"
    return "https://horizon-testnet.stellar.org/"


def fed(domain, address):
    FED = toml.loads(
        requests.get("https://" + domain + "/.well-known/stellar.toml").text
    )
    data = {"q": address, "type": "name"}
    print("getting federation with " + FED["FEDERATION_SERVER"] + " " + address)
    response = requests.get(url=FED["FEDERATION_SERVER"], params=data)
    print(response.text)
    return response.json()


def history():
    try:
        payments = (
            server()
            .payments()
            .for_account(CONF["public_key"])
            .limit(30)
            .call()["_embedded"]["records"]
        )
        if len(payments) == 0:
            print("no history")
            return
        else:
            for payment in payments:
                if payment["type"] == "create_account":
                    print(
                        payment["created_at"]
                        + " "
                        + payment["type"]
                        + " start "
                        + payment["starting_balance"]
                        + "\n"
                        + horizon_url()
                        + "operations/"
                        + payment["id"]
                    )
                else:
                    print(
                        payment["created_at"]
                        + " "
                        + payment["type"]
                        + " "
                        + payment["to"]
                        + " "
                        + payment["from"]
                        + " "
                        + payment["amount"]
                        + "\n"
                        + horizon_url()
                        + "operations/"
                        + payment["id"]
                    )
    except Exception as e:
        print(e)


def get_balance_issuer(amount, asset):
    if asset == "XLM":
        return 0, ""
    try:
        account = server().accounts().account_id(CONF["public_key"]).call()
        for record in account["balances"]:
            if (
                asset == record["asset_code"]
                or record["asset_type"] == "liquidity_pool_shares"
            ):
                if float(record["balance"]) < float(amount):
                    print("error insufficient funds")
                    return 1, record["asset_issuer"]
                else:
                    return 0, record["asset_issuer"]
    except Exception as e:
        print("account not found")


def get_asset_issuer(asset):
    try:
        account = server().accounts().account_id(CONF["public_key"]).call()
        count = 1
        for record in account["balances"]:
            if (
                record["asset_type"] == "liquidity_pool_shares"
                or record["asset_type"] == "native"
            ):
                continue
            else:
                if asset == record["asset_code"]:
                    print(str(count) + ": " + record["asset_issuer"])
                    count += 1
        if count > 1:
            print("select one of the above issuers e.g. 1")
            res = session.prompt("select assset issuer > ")
            try:
                if int(res) in range(count):
                    return account["balances"][int(res) - 1]["asset_issuer"]
            except Exception as e:
                print(e)
        else:
            print("no asset issuer found")
            res = session.prompt("want to provide asset issuer? y/n > ")
            if res == "y":
                return session.prompt("provide asset issuer > ")
        return None
    except Exception as e:
        print(e)
    return None


def send_asset(text):
    # send 10 EURT antb123*papayame.com or send 1 XLM PUBKEY memo text
    if CONF["private_key"] == "":
        print("no private key setup  - pls type set to set key or c to create wallet")
        return
    val = text.split()
    memo_type = "text"
    if len(val) < 3:
        print(
            "invalid syntax please use send amount asset receiver e.g.  s 10 EURT antb123*papayame.com"
        )
        return
    amount, asset, address = val[1], val[2].upper(), val[3]
    print(amount)
    if "*" in address:
        res = fed(address.split("*")[1], address)
        sendto = res["account_id"]
        try:
            memo = res["memo"]
            memo_type = res["memo_type"]
        except Exception:
            memo = ""
            memo_type = ""
    else:
        sendto = address
        memo = ""
    # override memo, type if given
    if len(val) == 6:
        memo = val[4]
        memo_type = val[5]
    if len(val) == 5:
        memo = val[4]
        memo_type = "text"
    print_formatted_text(
        HTML(
            """Are you sure you want to send
                                <ansiyellow>%s</ansiyellow>
                                <ansired>%s %s</ansired>
                                with memo of <ansiblue>%s</ansiblue> (y/n)
                                """
            % (sendto, asset, amount, memo)
        )
    )
    text = session.prompt("> ", default="y")
    if text != "y":
        return
    try:
        ret, asset_issuer = get_balance_issuer(amount, asset)
    except Exception as e:
        return e
    if ret:
        return
    # retsan = send_sanity(sendto, memo_type, asset)
    # if not retsan: return
    _asset = Asset(asset, asset_issuer)
    builder = transaction_builder()
    if asset != "XLM":
        builder.append_payment_op(sendto, _asset, amount)
    else:
        builder.append_payment_op(sendto, amount)
    if memo != "" and memo_type == "text":
        builder.add_text_memo(memo)
    if memo != "" and memo_type == "id":
        builder.add_id_memo(memo)
    try:
        envelope = builder.build()
        if CONF["multisig"] != "":
            print(
                "You have 2of2 multisig - send this data to the other key to sign when you get it back type signsend data"
            )
            print(envelope.to_xdr())
            return
        envelope.sign(keypair())
        print(server().submit_transaction(envelope))
    except Exception as e:
        print("error: " + e)


def signsend(text):
    cont = session.prompt("You want to sign or send? (sign/send) > ")
    data = text.split()[1]
    builder = transaction_builder()
    if cont.lower() == "sign":
        print(" signing " + data)
        builder.from_xdr(data, network_passphrase=network_passphrase())
        # key = session.prompt(u'Enter who you sign for? %s > ' % CONF['multisig'])
    envelope = builder.build()
    envelope.sign(keypair())
    print("send this to the other wallet and ask them to signsend it\n")
    print(envelope.to_xdr())


def start_app():
    print_formatted_text(
        HTML(
            "### WELCOME TO <ansired>stcli</ansired> - "
            + "type <ansiblue>?</ansiblue> or help for commands ####\n\n"
        )
    )
    load_conf()
    try:
        if "private_key" not in CONF:
            create_conf()
    except Exception:
        print(
            "no wallet? type k [key] to set the private key or c [create] to create wallet"
        )
    try:
        print_formatted_text(
            HTML(
                "Public key: <ansiyellow>"
                + CONF["public_key"]
                + "</ansiyellow> network: "
                + CONF["network"]
            )
        )
    except Exception:
        create_conf()
        print("using public key:" + CONF["public_key"] + "network: " + CONF["network"])
    if CONF["public_key"]:
        list_balances()


def path_payment_send(text):
    if CONF["private_key"] == "":
        print("no private key setup  - pls type set to set key or c to create wallet")
        return
    val = text.split()
    memo_type = "text"
    if len(val) < 3:
        print(
            "invalid syntax please use pp <amount> <source asset> <destination address> e.g.  pps 10 EURT antb123*papayame.com"
        )
        return
    amount, s_asset, address = val[1], val[2].upper(), val[3]
    ret, asset_issuer = get_balance_issuer(amount, s_asset)
    if ret:
        return
    if len(s_asset) < 5:
        sstype = "credit_alphanum4"
    else:
        sstype = "credit_alphanum12"
    _url = (
        horizon_url()
        + "paths/strict-send?destination_account="
        + address
        + "&source_asset_code="
        + s_asset
        + "&source_asset_type="
        + sstype
        + "&source_amount="
        + amount
        + "&source_asset_issuer="
        + asset_issuer
    )
    response = requests.get(_url)
    if response.status_code == 200:
        data = response.json()
        if len(data["_embedded"]["records"]) == 0:
            print("no path found")
            return
        record = data["_embedded"]["records"][0]
        print("best path found")
        print(record)
        _asset = Asset(
            record["destination_asset_code"], record["destination_asset_issuer"]
        )
        builder = transaction_builder()
        builder.append_payment_op(address, _asset, record["destination_amount"])
        try:
            envelope = builder.build()
            if CONF["multisig"] != "":
                print(
                    "You have 2of2 multisig - send this data to the other key to sign when you get it back type signsend data"
                )
                print(envelope.to_xdr())
                return
            envelope.sign(keypair())
            print(server().submit_transaction(envelope))
        except Exception as e:
            print("error: " + e)
    else:
        print("error: " + str(response.status_code))


def path_payment_receive(text):
    if CONF["private_key"] == "":
        print("no private key setup  - pls type set to set key or c to create wallet")
        return
    val = text.split()
    memo_type = "text"
    if len(val) < 3:
        print(
            "invalid syntax please use pp <amount> <destination asset> <source address> e.g.  s 10 EURT BTCLN antb123*papayame.com"
        )
        return
    amount, d_asset, address = val[1], val[2].upper(), val[3]
    ret, asset_issuer = get_balance_issuer(amount, d_asset)
    if ret:
        return
    # _asset = Asset(s_asset, asset_issuer)
    if len(d_asset) < 5:
        dstype = "credit_alphanum4"
    else:
        dstype = "credit_alphanum12"
    _url = (
        horizon_url()
        + "paths/strict-receive?source_account="
        + address
        + "&destination_asset_code="
        + d_asset
        + "&destination_asset_type="
        + dstype
        + "&destination_amount="
        + amount
        + "&destination_asset_issuer="
        + asset_issuer
    )
    response = requests.get(_url)
    if response.status_code == 200:
        data = response.json()
        if len(data["_embedded"]["records"]) == 0:
            print("no path found")
            return
        record = data["_embedded"]["records"][0]
        print("best path found")
        print(record)
        _asset = Asset(record["source_asset_code"], record["source_asset_issuer"])
        builder = transaction_builder()
        builder.append_payment_op(address, _asset, record["source_amount"])
        try:
            envelope = builder.build()
            if CONF["multisig"] != "":
                print(
                    "You have 2of2 multisig - send this data to the other key to sign when you get it back type signsend data"
                )
                print(envelope.to_xdr())
                return
            envelope.sign(keypair())
            print(server().submit_transaction(envelope))
        except Exception as e:
            print("error: " + e)
    else:
        print("error: " + str(response.status_code))


def deposit(text):
    print_formatted_text(HTML("<ansiblue>\n### DEPOSIT ###</ansiblue>\n"))
    print(
        "Deposit servers allow you to cash in assets into your wallet. We support naobtc.com, apay.io and tempo.eu.com"
    )
    print("you need to trust the asset before depositing.. eg. BCH")
    res = text.split()
    if len(res) > 2:
        server = text.split()[1]
        asset = text.split()[2].upper()
        print("deposit to " + server + " asset " + asset)
    else:
        print("server asset e.g. apay.io bch or naobtc.com btc")
        res = session.prompt("server asset > ")
        server, asset = res.split()[0], res.split()[1]
        token = auth(asset=asset)
        # print(token)
        if token is not None:
            data = {
                "asset_code": asset,
                "account": CONF["public_key"],
            }
            headers = {"Authorization": "Bearer " + token}
            toml_link = get_stellar_toml(asset)
            if toml_link is None:
                print("no toml link found for " + asset)
                return
            else:
                print(toml_link)
                url = (
                    toml_link["TRANSFER_SERVER_SEP0024"]
                    + "/transactions/deposit/interactive"
                )
                response = requests.post(url, data=data, headers=headers).json()
                webbrowser.open(response["url"], new=0, autoraise=True)

        else:
            print("Auth server not found for " + asset)
            return

        transaction_id = response["id"]
        print("transaction id: " + transaction_id)


def set_multisig(trusted_key):
    print_formatted_text(HTML("<ansiblue>\n### SET MULTISIG ###</ansiblue>\n"))
    print("set multisig will currently make your key a 2 of 2 multisig address")
    print_formatted_text(HTML("trusted key is:<ansired>" + trusted_key + "</ansired>"))
    print(
        "it will set med threshold and high to 2 and master weight to 1 so you can use 2 keys for all sending or issuing tokens\n\n"
    )
    builder = transaction_builder()
    # signer = SignerKey.ed25519_public_key(trusted_key, 1)
    builder.append_set_options_op(master_weight=1, med_threshold=2, high_threshold=2)
    envelope = builder.build()
    envelope.sign(keypair())
    print(server().submit_transaction(envelope))


def withdrawal(text):
    print_formatted_text(HTML("<ansiblue>\n### WITHDRAWAL ###</ansiblue>\n"))
    print(
        "withdrawal allows you to remove assets from your wallet such as EUR, BCH, BTC"
    )
    res = text.split()
    if len(res) > 1:
        asset = text.split()[1]
    else:
        print("server asset e.g. BTCLN <asset issuer>")
        asset = session.prompt("enter asset> ")

    if asset is not None:
        token = auth(asset=asset)
        if token is not None:
            data = {
                "asset_code": asset,
            }
            headers = {"Authorization": "Bearer " + token}
            toml_link = get_stellar_toml(asset=asset)
            url = (
                toml_link["TRANSFER_SERVER_SEP0024"]
                + "/transactions/withdraw/interactive"
            )
            response = requests.post(url, data=data, headers=headers).json()
            # print(response)
            webbrowser.open(response["url"], new=0, autoraise=True)
            transaction_id = response["id"]
            print("transaction id: " + transaction_id)

            # sep 24 withdrawal transaction flow
            print("pending user transfer start")
            print("waiting for user to start transfer")
            while True:
                time.sleep(5)
                transaction_details = requests.get(
                    toml_link["TRANSFER_SERVER_SEP0024"]
                    + "/transaction?id="
                    + transaction_id,
                    headers=headers,
                ).json()
                print(transaction_details)
                transaction = transaction_details["transaction"]
                if transaction["status"] == "pending_user_transfer_start":
                    print("Transfer started")
                    _asset_issuer = get_asset_issuer(asset)
                    _asset = Asset(asset, _asset_issuer)
                    if _asset is None:
                        print("asset not found")
                        return
                    else:
                        builder = transaction_builder()
                        if transaction["withdraw_memo_type"] == "text":
                            builder.add_text_memo(transaction["withdraw_memo"])
                        elif transaction["withdraw_memo_type"] == "id":
                            builder.add_id_memo(transaction["withdraw_memo"])
                        elif transaction["withdraw_memo_type"] == "hash":
                            builder.add_hash_memo(
                                base64.b64decode(transaction["withdraw_memo"])
                            )
                        builder.append_payment_op(
                            destination=transaction["withdraw_anchor_account"],
                            asset=_asset,
                            amount=transaction["amount_in"],
                        )
                        envelope = builder.build()
                        envelope.sign(keypair())
                        tran_response = server().submit_transaction(envelope)
                        print(tran_response["hash"])
                        break

            while True:
                # Continue with transaction
                time.sleep(5)
                transaction_details = requests.get(
                    toml_link["TRANSFER_SERVER_SEP0024"]
                    + "/transaction?id="
                    + transaction_id,
                    headers=headers,
                ).json()
                transaction = transaction_details["transaction"]
                if transaction["status"] == "completed":
                    print(transaction["status"])
                    break
                elif transaction["status"] == "pending_stellar":
                    print("waiting for stellar approval")
        else:
            print("Auth server not found for " + asset)
    else:
        print("enter valid asset")


def transactions():
    print_formatted_text(HTML("<ansiblue>\n### TRANSACTIONS ###</ansiblue>\n"))
    print("transactions will show you the last 10 transactions")
    print("you can also use the stellar.expert explorer")
    print("https://stellar.expert/explorer/public/account/" + CONF["public_key"])
    response = server().transactions().for_account(CONF["public_key"]).limit(10).call()
    for record in response["_embedded"]["records"]:
        print(record)


def server():
    return Server(horizon_url=horizon_url())


def sys_exit():
    saveconf = session.prompt("save zip encrypted configuration (y/n)> ")
    if saveconf.lower() == "y":
        passw = prompt("password for conf file: ", is_password=True)
        zipfile(passw)
    sys.exit()


def auth(asset):
    try:
        toml_link = get_stellar_toml(asset=asset)
        print(toml_link)
        if toml_link is not None:
            auth_url = toml_link["WEB_AUTH_ENDPOINT"]
            # get challenge transaction and sign it
            client_signing_key = Keypair.from_secret(CONF["private_key"])
            response = requests.get(
                f"{auth_url}?account={client_signing_key.public_key}"
            )
            content = json.loads(response.content)
            envelope_xdr = content["transaction"]
            envelope_object = TransactionEnvelope.from_xdr(
                envelope_xdr, network_passphrase=network_passphrase()
            )
            envelope_object.sign(client_signing_key)
            client_signed_envelope_xdr = envelope_object.to_xdr()
            # submit the signed transaction to prove ownership of the account
            response = requests.post(
                auth_url,
                json={"transaction": client_signed_envelope_xdr},
            )
            content = json.loads(response.content)
            token = content["token"]
            return token
        else:
            return None
    except Exception as e:
        print(e)
        return None


def trust_asset(text):
    val = text.split()
    asset, asset_issuer = val[1], val[2]
    print("Adding trustline to the asset issuer...")
    private_key = CONF["private_key"]
    url = Server(horizon_url=horizon_url())
    toml_link = get_stellar_toml(asset=asset, asset_issuer=asset_issuer)
    asset_info = toml_link["CURRENCIES"][0]
    keypair = Keypair.from_secret(private_key)
    account = url.load_account(keypair.public_key)
    builder = TransactionBuilder(
        source_account=account, network_passphrase=network_passphrase()
    )
    asset = Asset(asset_info["code"], asset_info["issuer"])
    builder.append_change_trust_op(asset=asset).set_timeout(30)
    envelope = builder.build()
    envelope.sign(keypair)
    response = url.submit_transaction(envelope)
    return response["successful"]


def direct_transfer():
    print_formatted_text(HTML("<ansiblue>\n### DIRECT TRANSFER ###</ansiblue>\n"))
    print("direct transfer allows you to send assets to another account")
    print("direct transfer e.g. kbtrading.org eurt 10")
    res = session.prompt("direct transfer> ")
    rlen = res.split()
    if len(rlen) > 2:
        try:
            server, asset, amount = res.split()[0], res.split()[1], res.split()[2]
            if asset is not None:
                print("Authencating with " + server + "...")
                token = auth(asset=asset)
                if token is not None:
                    toml_link = get_stellar_toml(asset=asset)
                    if toml_link["DIRECT_PAYMENT_SERVER"] is not None:
                        remitter_email = session.prompt("remitter email> ")
                        remitter_first_name = session.prompt("remitter_first_name> ")
                        remitter_last_name = session.prompt("remitter_last_name> ")
                        remitter_phone_number = session.prompt(
                            "remitter_phone_number> "
                        )
                        beneficiary_email = session.prompt("beneficiary_email> ")
                        beneficiary_first_name = session.prompt(
                            "beneficiary_first_name> "
                        )
                        beneficiary_last_name = session.prompt(
                            "beneficiary_last_name> "
                        )
                        beneficiary_bank_iban = session.prompt(
                            "beneficiary_bank_iban> "
                        )
                        beneficiary_bank_bic = session.prompt("beneficiary_bank_bic> ")
                        beneficiary_phone_number = session.prompt(
                            "beneficiary_phone_number> "
                        )
                        payload = {
                            "amount": amount,
                            "asset_code": asset,
                            "fields": {
                                "transaction": {
                                    "remitter_email": remitter_email,
                                    "remitter_first_name": remitter_first_name,
                                    "remitter_last_name": remitter_last_name,
                                    "remitter_phone_number": remitter_phone_number,
                                    "beneficiary_email": beneficiary_email,
                                    "beneficiary_first_name": beneficiary_first_name,
                                    "beneficiary_last_name": beneficiary_last_name,
                                    "beneficiary_bank_iban": beneficiary_bank_iban,
                                    "beneficiary_bank_bic": beneficiary_bank_bic,
                                    "beneficiary_phone_number": beneficiary_phone_number,
                                }
                            },
                        }
                        print(payload)
                        headers = {"Authorization": "Bearer " + token}
                        url = toml_link["DIRECT_PAYMENT_SERVER"] + "/transactions"
                        response = requests.post(
                            url, json=payload, headers=headers
                        ).json()
                        print(response)
                    else:
                        print("Direct Payment not supported for " + asset)
                        return
                else:
                    print("Auth server not found for " + asset)
                    return
            else:
                print("Please enter valid asset")
                return
        except Exception:
            print("Transaction format error")
            return
    else:
        print("Request format error")
        return


def main():
    start_app()
    while True:
        text = session.prompt(
            "> ",
            completer=compl,
            complete_while_typing=True,
            vi_mode=True,
            auto_suggest=AutoSuggestFromHistory(),
        )
        text = text.strip()
        if text == "help" or text == "?":
            print_help()
        elif text == "":
            continue
        elif text == "create" or text == "c":
            create_wallet()
        elif text == "balance" or text == "b":
            list_balances()
        elif text == "history" or text == "h":
            history()
        elif text[:8] == "signsend":
            signsend(text)
        elif text == "quit" or text == "q":
            sys_exit()
        elif text == "key" or text == "k":
            set_private_key()
        elif text == "receive" or text == "r":
            receive()
        elif text == "fund" or text == "f":
            fund()
        # elif text == 'list'or text == 'l': list_assets()
        elif text == "conf":
            print(toml.dumps(CONF))
        elif text.split(" ")[0] == "set":
            set_var(text)
        elif text == "version" or text == "v":
            print("VERSION: " + VERSION)
        elif text[0] == "d" and text[1] == "t":
            direct_transfer()
        elif text[0] == "t" and text[1] == "t":
            trust_asset(text)
        elif text[0] == "u" and text[1] == "t":
            trust_asset(text, untrust=True)
        elif text[0] == "d":
            deposit(text)
        elif text[0] == "w":
            withdrawal(text)
        elif text[0] == "s":
            send_asset(text)
        elif text[0] == "!":
            os.system(text[1:])
        elif text[0] == "p" and text[1] == "p" and text[2] == "s":
            path_payment_send(text)
        elif text[0] == "p" and text[1] == "p" and text[2] == "r":
            path_payment_receive(text)
        elif text[0] == "t":
            transactions()
        elif text == "cls":
            if platform.system() == "Windows":
                os.system("cls")
            elif platform.system() == "Linux":
                os.system("clear")
            else:
                print("unsupported platform")
        else:
            print("You entered:", text)


if __name__ == "__main__":
    main()
