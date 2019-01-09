# Copyright: (c) 2019, Josef Fuchs <terrjosef.fuchs@j-fuchs.at>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from ansible.errors import AnsibleFilterError

import sys
import os
import copy

LIBRARIES_DIR = '../library'
sys.path.append( os.path.join( os.path.dirname(__file__), LIBRARIES_DIR ) )

# Append relative path for library directory. Allow copy filestructure
# without need to alter path definition
from iosconfigregexp import IosConfigRegexp, MissingEndOfBannerError

class FilterModule(object):

    def filters(self):
        return {
            'ios_config_section_extract': self.ios_config_section_extract,
            'ios_config_section_remove': self.ios_config_section_remove
        }

    def ios_config_section_extract(self, a, regexp=[], ignorecase=False, prefix_str='', filename='', *args, **kw):
        '''
        Extract all sections selected by regexp list and save to a file if filename != ''
        '''
        icr = IosConfigRegexp(a, regexp, ignorecase, prefix_str)
        try:
            sec = icr.extract_section()
            if filename != '' and sec != None and len(sec) > 0:
                try:
                    with open(filename, 'w') as f:
                        for l in sec:
                            f.write(l + os.linesep)
                except:
                    raise AnsibleFilterError(
                        ("'Error in filter ios_config_section_extract! "
                        "File '{}' could not be written").format(filename))
            return sec
        except MissingEndOfBannerError as e:
            raise AnsibleFilterError(e.message)

    def ios_config_section_remove(self, a, regexp=[], ignorecase=False, prefix_str='', filename='', *args, **kw):
        ''' Extract all sections selected by regexp list'''
        icr = IosConfigRegexp(a, regexp, ignorecase, prefix_str)
        try:
            sec = icr.remove_section()
            if filename != '' and sec != None and len(sec) > 0:
                try:
                    with open(filename, 'w') as f:
                        for l in sec:
                            f.write(l + os.linesep)
                except:
                    raise AnsibleFilterError(
                        ("'Error in filter ios_config_section_remove! "
                        "File '{}' could not be written").format(filename))
            return sec
        except MissingEndOfBannerError as e:
            raise AnsibleFilterError(e.message)
