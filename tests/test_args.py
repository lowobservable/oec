import unittest
from unittest.mock import patch

import context

from oec.args import parse_args

class ParseArgsTestCase(unittest.TestCase):
    def setUp(self):
        patcher = patch('argparse.ArgumentParser.error')

        self.parser_error = patcher.start()

        self.addCleanup(patch.stopall)

    def test_tn3270_host_only(self):
        args = parse_args(['/dev/ttyACM0', 'tn3270', 'host'], False)

        self.assertEqual(args.emulator, 'tn3270')
        self.assertEqual(args.host, 'host')
        self.assertEqual(args.port, 23)
        self.assertIsNone(args.device_names)

    def test_tn3270_host_and_port(self):
        args = parse_args(['/dev/ttyACM0', 'tn3270', 'host:3270'], False)

        self.assertEqual(args.emulator, 'tn3270')
        self.assertEqual(args.host, 'host')
        self.assertEqual(args.port, 3270)
        self.assertIsNone(args.device_names)

    def test_tn3270_host_and_device_names(self):
        args = parse_args(['/dev/ttyACM0', 'tn3270', 'lu1@host'], False)

        self.assertEqual(args.emulator, 'tn3270')
        self.assertEqual(args.host, 'host')
        self.assertEqual(args.port, 23)
        self.assertEqual(args.device_names, ['lu1'])

    def test_tn3270_missing_host(self):
        for arg in [':3270', 'lu1@', 'lu1@:3270']:
            with self.subTest(arg=arg):
                self.parser_error.reset_mock()

                parse_args(['/dev/ttyACM0', 'tn3270', arg], False)

                self.parser_error.assert_called_once()

                self.assertEqual(self.parser_error.call_args.args[0], f'argument host: host name is required: {arg}')

    def test_tn3270_invalid_port(self):
        for port in ['-1', '0', '100000']:
            with self.subTest(port=port):
                self.parser_error.reset_mock()

                parse_args(['/dev/ttyACM0', 'tn3270', 'host:' + port], False)

                self.parser_error.assert_called_once()

                self.assertEqual(self.parser_error.call_args.args[0], f'argument host: invalid port: {port}')

    def test_tn3270_deprecated_port(self):
        args = parse_args(['/dev/ttyACM0', 'tn3270', 'host', '3270'], False)

        self.assertEqual(args.emulator, 'tn3270')
        self.assertEqual(args.host, 'host')
        self.assertEqual(args.port, 3270)
        self.assertIsNone(args.device_names)

    def test_tn3270_deprecated_port_overridden_by_new_port(self):
        args = parse_args(['/dev/ttyACM0', 'tn3270', 'host:3270', '9999'], False)

        self.assertEqual(args.emulator, 'tn3270')
        self.assertEqual(args.host, 'host')
        self.assertEqual(args.port, 3270)
        self.assertIsNone(args.device_names)

    def test_tn3270_invalid_deprecated_port(self):
        for port in ['-1', '0', '100000']:
            with self.subTest(port=port):
                self.parser_error.reset_mock()

                parse_args(['/dev/ttyACM0', 'tn3270', 'host', port], False)

                self.parser_error.assert_called_once()

                self.assertEqual(self.parser_error.call_args.args[0], f'argument port: invalid port: {port}')
