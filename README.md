# oec

oec is an open replacement for the IBM 3174 Establishment Controller.

It is a work in progress - as of now it only provides basic TN3270 and VT100 emulation.

## Usage

You will need to build a [interface](https://github.com/lowobservable/coax-interface) and connect it to your computer.

Then configure a Python virtual environment and install dependencies:

```
python -m venv VIRTUALENV
. VIRTUALENV/bin/activate
pip install -r requirements.txt --no-deps
```

Assuming your interface is connected to `/dev/ttyUSB0` and you want to connect to a TN3270 host named `mainframe`:

```
python -m oec /dev/ttyUSB0 tn3270 mainframe
```

If you want to use the VT100 emulator and run `/bin/sh` as the host process:

```
python -m oec /dev/ttyUSB0 vt100 /bin/sh -l
```

## See Also

* [coax-interface](https://github.com/lowobservable/coax-interface) - Tools for interfacing with IBM 3270 type terminals
* [pytn3270](https://github.com/lowobservable/pytn3270) - Python TN3270 library
