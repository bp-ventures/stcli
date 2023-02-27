# stcli

stcli - a repl command line crypto wallet for stellar that is simple and all in one python file

## Getting Started

If you have the Ubuntu you may be able to just clone the one file stcli.py. Everything resides in the one file... it will generate an stcli.conf in the same
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

## Virtual environment (Optional)

Install, create & activate virtual enviroment on Unix/macOS
```
python3 -m pip install --user virtualenv
python3 -m venv env
source env/bin/activate
```

Install, create & activate virtual enviroment on Windows
```
py -m pip install --user virtualenv
py -m venv env
.\env\Scripts\activate
```

### Installing STCLI

```
git clone https://github.com/antb321/stcli.git
cd stcli
python3 -m pip install -e stcli/
stcli --help
press ? for help
```

![stcli help screen](https://user-images.githubusercontent.com/46220827/220412161-5792b1f0-556b-4dd3-9076-48e1ff0dee3d.png)


## License

This project is licensed under the Apache 2.0 License - see the [LICENSE.md](LICENSE.md) file for details
