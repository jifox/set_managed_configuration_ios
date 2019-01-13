# Copyright: (c) 2019, Josef Fuchs <josef.fuchs@j-fuchs.at>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


from __future__ import (absolute_import, division, print_function)
__metaclass__ = type


ANSIBLE_METADATA = {
    'metadata_version': '1.0',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: client_intf_str
short_description: This filter allows to get Cisco IOS compatible interface name and number form short name e.g. "gi1/0/10" -> "GigabiEthernet1/0/10"

version_added: "2.7"
description:

  client_intf_str:
  =================

    This filter is parsing a case insensitive string and returning the apropriate
    interface name. The first two chars are used to determine the interface name.

    String start with:
      "et" - eth
      "Fa" - FastEthernet
      "Gi" - GigabitEthernet
      "Te" - TenGigabitEthernet
      "Tw" - TwentyfiveGigabitEthernet
      "Fo" - FortyGigabitEthernet
      "Hu" - HundredGigabitEthernet
      "Lo" - Loopback
      "Ma" - Management
      "Po" - ""      # only port number will be set

  For e.g.:

    - set_fact:
        - intf: "{{ 'gi1/0/4' | client_intf_str }}

    will return the dictionary intf:

    intf:
      name: "GigabitEthernet"
      number: "1/0/4"

  shorten_intf_str:
  =================

    This filter accepts a expanded interface name (GigabitEthernet1/0/4) or a short
    interface name (Gi1/0/4) and returns always the short interface name.

  For e.g.:

    - set_fact:
        - intf: "{{ 'TenGigabitEthernet1/1/4' | shorten_intf_str }}

    will return the dictionary intf:

    intf:
      name: "Te"
      number: "1/1/4"

'''

from ansible.errors import AnsibleFilterError


def parse_client_intf_str(str):
  id = str[:2].lower()
  if id == u'fa':
    _interface = u'FastEthernet'
  elif id == u'gi':
    _interface = u'GigabitEthernet'
  elif id == u'te':
    _interface = u'TenGigabitEthernet'
  elif id == u'tw':
    _interface = u'TwentyfiveGigabitEthernet'
  elif id == u'fo':
    _interface = u'FortyGigabitEthernet'
  elif id == u'hu':
    _interface = u'HundredGigabitEthernet'
  elif id == u'ma':
    _interface = u'Management'
  elif id == u'lo':
    _interface = u'Loopback'
  elif id == u'et':
    _interface = u'eth'
  elif id == u'po':
    _interface = u''
  else:
    raise AnsibleFilterError('client_intf_str: unknown category: %s' % id)
  return {'name': _interface, 'number': str[2:]}


def find_digit(str):
  i = -1
  j = 0
  for c in str:
    j = j+1
    if c >= '0' and c <= '9' and i == -1:
      i = j
  return i


def parse_shorten_intf_str(str):
  id = str.lower()
  p = find_digit(id)
  if p == -1:
    raise AnsibleFilterError('parse_shorten_intf_str: missing interface number: %s' % str)
  p = p -1
  ifn = id[:p].strip()
  if (ifn == u'fastethernet') or (ifn == u'fa'):
    _interface = u'Fa'
  elif (ifn == u'gigabitethernet') or (ifn == u'gi'):
    _interface = u'Gi'
  elif (ifn == u'ten-gigabitethernet') or (ifn == u'te'):
    _interface = u'Te'
  elif (ifn == u'tengigabitethernet'):
    _interface = u'Te'
  elif (ifn == u'twentyfivegigabitethernet') or (ifn == u'tw'):
    _interface = u'Tw'
  elif (ifn == u'fortygigabitethernet') or (ifn == u'fo'):
    _interface = u'Fo'
  elif (ifn == u'hundredgigabitethernet') or (ifn == u'hu'):
    _interface = u'Hu'
  elif (ifn == u'management') or (ifn == u'Ma') or (ifn == u'mgmt'):
    _interface = u'Ma'
  elif (ifn == u'loopback') or (ifn == u'lo'):
    _interface = u'Lo'
  elif (ifn == u'eth') or (ifn == u'et'):
    _interface = u'et'
  elif (ifn == u''):
    _interface = u'Po'
  else:
    raise AnsibleFilterError('parse_shorten_intf_str: unknown category: %s' % str)
  return {'name': _interface, 'number': str[p:]}

# ---- Ansible filters ----
class FilterModule(object):
    def filters(self):
        return {
            'client_intf_str': parse_client_intf_str,
            'shorten_intf_str': parse_shorten_intf_str
        }
