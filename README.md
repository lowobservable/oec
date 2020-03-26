# oec

IBM 3270 terminal controller - an open replacement for the IBM 3174 Establishment Controller.

![IBM 3278 terminal and oec](.images/hero.jpg)

## Features

This is a work in progress - as of now it only provides basic TN3270 and VT100 emulation.

- [x] TN3270
    - [x] Basic TN3270
    - [ ] EAB
    - [ ] TN3270E
    - [ ] SSL/TLS
    - [ ] Non-English character sets
- [x] VT100
- [ ] Connection menu
- [ ] Multiple logical terminals

## Usage

You will need to build a [interface](https://github.com/lowobservable/coax) and connect it to your computer.

Then configure a Python virtual environment and install dependencies:

```
python -m venv VIRTUALENV
. VIRTUALENV/bin/activate
pip install -r requirements.txt --no-deps
```

Assuming your interface is connected to `/dev/ttyACM0` and you want to connect to a TN3270 host named `mainframe`:

```
python -m oec /dev/ttyACM0 tn3270 mainframe
```

If you want to use the VT100 emulator and run `/bin/sh` as the host process:

```
python -m oec /dev/ttyACM0 vt100 /bin/sh -l
```

## See Also

* [coax](https://github.com/lowobservable/coax) - Tools for interfacing with IBM 3270 type terminals
* [pytn3270](https://github.com/lowobservable/pytn3270) - Python TN3270 library
