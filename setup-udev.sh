#!/bin/bash
set -euo pipefail

RULE='SUBSYSTEM=="tty", ATTRS{serial}=="e6613852831c9e32", SYMLINK+="ttyCoax"'
RULE_FILE="/etc/udev/rules.d/99-coax-interface.rules"

echo "$RULE" | sudo tee "$RULE_FILE" > /dev/null
sudo udevadm control --reload-rules
sudo udevadm trigger --subsystem-match=tty

echo "Rule installed at $RULE_FILE"
echo "Symlink /dev/ttyCoax should now be active:"
ls -l /dev/ttyCoax
