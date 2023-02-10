# stcli

stcli - a repl command line crypto wallet for stellar that is simple and all in one python file

## Getting Started

If you have the Ubuntu you may be able to just clone the one file stcli.py
Everything resides in the one file... it will generate an stcli.conf in the same
directory or an encrypted stcli.zip.

The reason for this tiny app is I wanted a stellar wallet:

- written in python
- 100% auditable
- usable from a secured server
- for testing deposits and withdrawals
- fully command line text based
- keep on a USB key and run under tails
- multisig that can be used on a read only linux box

THIS APP IS MADE FOR TESTING PURPOSES AUTHORS TAKE NO RESPONSIBILITY FOR USE

### Prerequisites

Command line - preferably Linux but MacOS or Windows 10 with Linux should work. Python 3.8+ is required

- python
- zip/unzip

### Installing

```
git clone https://github.com/antb321/stcli.git
cd stcli
sudo python3 -m pip install -e stcli/
stcli --help
press ? for help
```

![stcli help screen](https://user-images.githubusercontent.com/40919851/42498875-acfbe7ba-842d-11e8-97f5-169bc86a194e.png)

### TODO

- There is a test suite for stellar_base but none for this mini app
- path payments
- SEP 007
- update SEP 006 support
- integrate chrome for those who want to use a ledger
- add to pypi
- make a proper install
- view order book, buy, sell
- modules
- offline

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details
