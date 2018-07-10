# stcli
stcli - a repl command line crypto wallet for stellar that is simple and all in one file

## Getting Started
If you have the Ubuntu you may be able to just clone the one file stcli.py
Everything resides in the one file... it will generate an stcli.conf in the same
directory or an encrypted stcli.zip


THIS APP is MADE FOR TESTING PURPOSES


### Prerequisites
Command line - preferably Linux but MacOS or Windows 10 with Linux should work
* python
* zip/unzip

These libraries:
```
toml>=0.9.4
prompt_toolkit>=2.0.3
requests>=2.13.0
stellar_base>=0.1.6
PyQRCode>=1.2.1
```

### Installing

```
git clone https://github.com/antb123/stcli.git
cd stcli
pip install -r requirements.txt
less stcli.py

Once you are satisfied it looks ok you can make it executable and then run it
chmod +x stcli.py
./stcli.py
```

in the future this should be available on 

### TODO

* There is a test suite for stellar_base but none for this mini app
* path payments
* SEP 007
* update SEP 006 support
* integrate chrome for those who want to use a ledger




## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details









