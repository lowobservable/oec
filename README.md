# oec

oec is an open replacement for the IBM 3174 Establishment Controller.

It is still a work in progress - as of now it only provides basic VT100 emulation but the goal is to implement TN3270 and multiple logical terminal support.

## Usage

You will need to build a [interface](https://github.com/lowobservable/coax-interface) and connect it to your computer.

Then configure a Python virtual environment and install dependencies:

```
python -m venv VIRTUALENV
. VIRTUALENV/bin/activate
pip install -r requirements.txt --no-deps
```

Assuming your interface is connected to `/dev/ttyUSB0` and you want to run `/bin/sh` as the host process:

```
python -m oec /dev/ttyUSB0 /bin/sh -l
```

## See Also

* [coax-interface](https://github.com/lowobservable/coax-interface) - tools for interfacing with IBM 3270 type terminals
