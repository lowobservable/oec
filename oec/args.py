"""
oec.args
~~~~~~~~
"""

import argparse
import codecs
import logging

logger = logging.getLogger('oec.args')

def parse_args(args, is_vt100_available):
    parser = argparse.ArgumentParser(description='IBM 3270 terminal controller')

    parser.add_argument('serial_port', help='serial port')

    subparsers = parser.add_subparsers(dest='emulator', required=True,
                                       description='emulator')

    tn3270_parser = subparsers.add_parser('tn3270', description='TN3270 emulator',
                                          help='TN3270 emulator')

    tn3270_parser.add_argument('host', metavar='[lu[,lu...]@]host[:port]',
                               help='host and optional port and LUs')
    tn3270_parser.add_argument('port', nargs='?', type=int, help=argparse.SUPPRESS)

    tn3270_parser.add_argument('--codepage', metavar='encoding', default='ibm037',
                               dest='character_encoding', type=get_character_encoding,
                               help='host EBCDIC code page')

    tn3270_parser.add_argument('--tn3270e', choices=['off', 'basic', 'default'],
                               metavar='profile', default='default',
                               dest='tn3270e_profile',
                               help='TN3270E profile: off, basic, default')

    if is_vt100_available:
        vt100_parser = subparsers.add_parser('vt100', description='VT100 emulator',
                                             help='VT100 emulator')

        vt100_parser.add_argument('command', help='host process')
        vt100_parser.add_argument('command_args', nargs=argparse.REMAINDER,
                                  help='host process arguments')

    args = parser.parse_args(args)

    if args.emulator == 'tn3270':
        (args.host, args.port, args.device_names) = parse_tn3270_host_args(args, parser)

    return args

def get_character_encoding(encoding):
    try:
        codecs.lookup(encoding)
    except LookupError:
        raise argparse.ArgumentTypeError(f'invalid encoding: {encoding}')

    return encoding

def parse_tn3270_host_args(args, parser):
    elements = args.host.rsplit(':', 1)

    port = None

    if len(elements) > 1:
        try:
            port = int(elements[1])
        except ValueError:
            parser.error(f'argument host: invalid port: {elements[1]}')

        if not is_valid_port(port):
            parser.error(f'argument host: invalid port: {port}')

    if args.port is not None:
        if port is None:
            if not is_valid_port(args.port):
                parser.error(f'argument port: invalid port: {args.port}')

            port = args.port

            logger.info('The port argument is deprecated and will be removed in the future, use host:port instead.')
        else:
            logger.warning('The port argument is deprecated and will be removed in the future, port from host:port is being used.')

    if port is None:
        port = 23

    elements = elements[0].split('@', 1)

    host = elements[-1].strip()

    if not host:
        parser.error(f'argument host: host name is required: {args.host}')

    device_names = None

    if len(elements) > 1:
        device_names = elements[0].split(',')

    return (host, port, device_names)

def is_valid_port(port):
    return port >= 1 and port <= 65535
