# Experiences and Optimizations

_This article describes a solution **Josef Fuchs**, Network and Security Engineer at **Pankl Racing Systems AG Austria** developed while attending the Building **Network Automation Solutions** online course._

The Jinja2-only solution was working fine but suffers from poor performance when used on edge switches that have numerous managed client ports (some of my switches have up to 240 ports). The performance of looping over every single regex, parsing the whole configuration and rereading the result was not acceptable, so I optimized the configuration management by implementing two Jinja2 filters in Python. These filters work much faster than Ansible loops I used in the original solution.

## Filter: ios_config_section_extract

This filter is used to extract a configuration section and optionally save it into a file. Here's how you could use it:

```yaml
  - set_fact:
      src_config = "{{ src_config | ios_config_section_extract(regexp, ignorecase, prefix_str, filename) }}"

```

### Input

The input (`src_config`) can be either a single string with line-separators or a list of strings.

### Paramters

|Parameter|Required|Default|Description|
|---|---|---|---|
|regexp| Yes | | A list of strings containing the regular expressions to select the config-section headers. Also a single string can be passed. If line-start marker '^' or line-end marker '$' is omitted,the filter will set it. This allows to pass for e.g. the plain interface name and ensure that only the interface configuration will match and dot a string in any description.|
|ignorecase| No | false | If set to true, the regex matches strings case insensitive|
|prefix_str| No  | '' | Allows to prepend a common string to the regex data that is used for matching. This string will be directly prepended (`expr = self.prefix_str + pat`). Missing line-start and -end markers will be inserted automatically is needed. This allows for e.g. to pass a list o  vlan-numbers as `regex` and use the string 'vlan' as `prefix_str` to extract the specific vlan configurations that are selected by `regex`.|
|filename| No | '' | If a filename is passed, all the selected configurations will be saved as a textfile. The directory must exist.|

### Result

* Selected configuration: list of strings
* Textfile:  if filename was specified the textfile will contain the selected configuration sections

## Filter: ios_config_section_remove

This filter deletes parts of device configuration. Here's the simplest way to use it:

```yaml
- name: Remove all blocks or commands defined in delete_section_regex
  set_fact:
    src_config: "{{ src_config | ios_config_section_remove(delete_section_regex) }}"
```

This filter has the same input and parameters as the `ios_config_section_extract` filter and returns the contents of input configuration after deleting all configuration sections matched by regular expressions.

### Requirements

The productive environment is tested with:

* ansible &nbsp; 2.7.5
* python version = 3.6.7 (default, Oct 22 2018, 11:32:17) [GCC 8.2.0]
* Python module ( pip install ... )
  * textfsm &nbsp; 0.4.1
  * napalm &nbsp; 2.3.3
  * var_dump &nbsp; 1.2

* Tested with:
  * Cisco Catalyst 9300-48P &nbsp; (16.6.4a)
  * Cisco Catalyst WS-C3560CX-8XPD-S &nbsp; (15.2(4)E5)
  * Cisco Catalyst 2960
  * Cisco Catalyst 6824 &nbsp; (15.5(1)SY2)

### List of files

```bash
ansible@ubuntu:~/set_managed_configuration_ios (master)*$ tree
.
├── ansible.cfg
├── blog       # blog article as published
├── compiled
│   └── R01    # directory where template files for device R01 are stored during runtiome
│       ├── R01_0001_unmanaged_configuration.ios
│       ├── R01_0010_vlan_configuration.ios
│       ├── R01_0100_acl_emergency_access_configuration.ios
│       ├── R01_0800_client_ports_configuration.ios
│       ├── R01_9010_banner_client_ports_configuration.ios
│       ├── R01_9999_end.ios
│       └── R01_managed_client_ports.yml
├── configs
│   └── R01 # directory where the managed configuration and the differnce to running configuratio is stored
│       ├── R01__ios_banner.ios   # data generated for set_ios_banner.yml
│       ├── R01_managed_configuration.ios
│       └── R01_managed_configuration.ios.diff
├── filter_plugins
│   ├── client_intf_str.py
│   ├── ios_config_section.py     # ansible filter plugin
│   └── __pycache__
│       └── ios_config_section.cpython-36.pyc
├── group_vars
│   ├── all.yml
│   ├── ios.yml
│   ├── lab.yml
│   └── switches
│       ├── switches_vault.yml   # encrypted vars naming: vault_xxxxxx
│       └── switches.yml
├── host_vars
│   └── R01
│       ├── conf_client_ports.yml  # manual
│       ├── device_uplinks.yml     # automatically generated from datamodel
│       ├── device_vlans.yml
│       └── R01.yml
├── include
│   ├── inc_set_managed_configuration_ios.yml
│   ├── inc_template.yml
│   ├── inc_validate_directories.yml
│   └── inc_validate_directory_already_exists.yml
├── inv_develop.yml   # inventory file
├── library
│   ├── iosconfigregexp.py        # Class used by filter
│   ├── __pycache__
│   │   └── iosconfigregexp.cpython-36.pyc
│   └── test_iosconfigregexp.py   # Unittest for class
├── LICENSE
├── README.md
├── reports                      # default directory for reports (not used here)
├── set_ios_banner_motd.yml             # Playbook to set the MOTD banner
├── set_managed_configuration_ios.yml   # Playbook to push managed configuration to device
├── templates
│   ├── gen_managed_client_interface_list.j2
│   ├── ios
│   │   ├── config_acl_emergency_access.j2
│   │   ├── config_client_interfaces.j2
│   │   ├── config_ios_banner_motd.j2
│   │   ├── config_vlans.j2
│   │   └── ios_banner_motd.j2
│   └── textfsm
│       └── cisco_ios_show_run_interface_part.template
└── vars
    └── PLANT_A                # fabric datamodel
        ├── uplinks_db.yml
        └── vlan_db.yml
```

## Github

The full source is available at github.

<https://github.com/jifox/set_managed_configuration_ios>

## N.A.P.A.L.M Compatibilty

NAPALM (Network Automation and Programmability Abstraction Layer with Multivendor support)

<https://github.com/napalm-automation/napalm-ansible>

A detailed description of the napalm module can be found here: <https://napalm.readthedocs.io/en/latest/index.html>

The IOS network devices must be configured to use napalm.
see: <https://napalm.readthedocs.io/en/latest/support/ios.html>

```text
! NAPALM compatible settings
archive
 path flash:archive
!
ip scp server enable
!
```

---

Author:

**DI Josef Fuchs, MSc.**

Network and Security Engineer at Pankl Racing Systems AG Austria. (<https://www.pankl.com>)

Email:  <mailto:josef.fuchs@j-fuchs.at><br>
LinkedIn: <https://www.linkedin.com/pub/fuchs-josef/75/a38/16b>|
