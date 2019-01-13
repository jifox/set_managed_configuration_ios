#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Copyright: (c) 2019, Josef Fuchs <josef.fuchs@j-fuchs.at>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import unittest
import copy

from iosconfigregexp import IosConfigRegexp, MissingEndOfBannerError
from var_dump import var_dump

class TestIosConfigRegexp(unittest.TestCase):

    def setUp(self):
        self.ios_config = [
            "line 1",
            "start block erronous",
            "  should not be selected in start block erronous section",
            "start block",
            " should be seleted in start block section",
            "after start block section, should not be selected",
            "banner motd ^C",
            "! banner motd line1",
            "! banner motd line2",
            "^C",
            "banner illegal ^C ",
            "! shoult not be selected because ^C is not at line end",
            "^C",
            "banner login \x03",
            "! banner login line1",
            "! banner login line2",
            "^C",
            "start block",
            " should be seleted",
            "after section should not be selected",
            "xxxx ends with block end",
            " should be seleted1 block end",
            " should be seleted2 block end",
            "after section should not be selected",
            "banner exception ^C",
            "! raise exception because block end line ^C is missing",
            "interface GigabitEthernet1/0/30",
            " switchport mode access",
            " switchport voice vlan 60",
            " ip flow monitor IPv4_STEALTHWATCH_NETFLOW input",
            " switchport nonegotiate",
            " spanning-tree portfast",
            " storm-control multicast level 5.00",
            " storm-control broadcast level 5.00",
            " storm-control action trap",
            " storm-control action shutdown",
            " spanning-tree guard root",
            " ip arp inspection limit rate 400 burst interval 3",
            "!",
            "interface GigabitEthernet1/0/31",
            " switchport mode access",
            " switchport voice vlan 60",
            " ip flow monitor IPv4_STEALTHWATCH_NETFLOW input",
            " switchport nonegotiate",
            " spanning-tree portfast",
            " storm-control multicast level 5.00",
            " storm-control broadcast level 5.00",
            " storm-control action trap",
            " storm-control action shutdown",
            " spanning-tree guard root",
            " ip arp inspection limit rate 400 burst interval 3",
            "!",
            "interface GigabitEthernet1/0/32",
            " switchport mode access",
            " switchport voice vlan 60",
            " ip flow monitor IPv4_STEALTHWATCH_NETFLOW input",
            " switchport nonegotiate",
            " spanning-tree portfast",
            " storm-control multicast level 5.00",
            " storm-control broadcast level 5.00",
            " storm-control action trap",
            " storm-control action shutdown",
            " spanning-tree guard root",
            " ip arp inspection limit rate 400 burst interval 3",
            "!",
            ""
        ]
        self.icr = IosConfigRegexp(copy.deepcopy(self.ios_config))


    def test_iosconfigregexp_property_conf_lines(self):
        ic = self.icr.conf_lines
        self.assertEqual(len(ic), len(self.ios_config),
            "Error in property conf_lines. Length do not match parameters length")
        for i in range(0, len(self.ios_config)):
            self.assertEqual(ic[i], self.ios_config[i],
                ("Error in property conf_lines. "
                "line {} ({} != {}) do not match").format(i, ic[i], self.ios_config[i]))

    def test_iosconfigregexp_property_regexplist(self):
        self.icr.regexplist = "string"
        self.assertIsInstance(self.icr.regexplist, list, "Regexplist should return a list or strings")

        self.icr.regexplist = r"^banner motd \^C"
        self.assertEqual(len(self.icr.regexplist), 2, r"Missing automatically added regexp changing \^C to ACSII(03) char")

        self.assertEqual(self.icr.regexplist[0], r"^banner motd \^C", "Invalid Value")
        self.assertEqual(self.icr.regexplist[1], "^banner motd \x03", "Invalid Value")

    def test_iosconfigregexp_extract_section(self):
        self.icr.regexplist = [ r"^start\s+block$", r"^banner\s+[m|l].*\^C$", r"^.*block\s+end" ]
        res = self.icr.extract_section()
        self.assertEqual(len(res), 15, "Invalid result set")

        self.icr.regexplist = [ r"^banner\s+ex.*\^C$" ]
        with self.assertRaises(MissingEndOfBannerError):
            res = self.icr.extract_section()

    def test_iosconfigregexp_ignorecase(self):
        self.icr.regexplist = [ r"START\s+BLOCK$" ]
        self.icr.ignorecase = True
        res = self.icr.extract_section()
        self.assertEqual(len(res), 4, "Invalid result set")

    def test_iosconfigregexp_remove_section(self):
        self.icr.regexplist = [ r"^start\s+block$", r"^banner\s+[m|l].*\^C$", r"^.*block\s+end$" ]
        res = self.icr.remove_section()
        self.assertEqual(len(res), 51, "Invalid result set")

        self.icr.regexplist = [ r"^banner\s+ex.*\^C$" ]
        with self.assertRaises(MissingEndOfBannerError):
            res = self.icr.remove_section()

    def test_iosconfigregexp_remove_section_with_prefix_str(self):
        self.icr.regexplist = [ r"GigabitEthernet1/0/31" ]
        self.icr.prefix_str = r'interface\s+'
        res = self.icr.remove_section()
        self.assertEqual('interface GigabitEthernet1/0/31' in [res], False, "Invalid Result set.")

if __name__ == '__main__':
    unittest.main()
