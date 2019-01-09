# Ansible Network-Automation - Cisco IOS - Brownfield migration

One of the problems that I ran into during starting with network automation was the decision on how to migrate to managed-configuration step by step.

In a first step I’ve tried to use ansible standard modules for cisco-ios network devices. For some parts of the configuration this works fine but when it comes to access-lists, device-vlan configurations etc. the complexity of ansible playbooks is growing rapidly. This complexity is introduced by determining the sequence of add- and delete-statements needed to transform the running-configuration into the managed configuration.

After further investigating this problem, I switched over to ansible napalm modules. The `napalm_install_config` module is used to replace the whole device configuration at once and provides a mechanism to show the configuration-diff and commit or rollback the changes.

Replacing the whole configuration is an elegant way of removing unwanted device configuration and simplifies the playbooks. Now the problem needed to be solved was, how to migrate just the parts of the device configuration that are managed.

None of the existing Ansible modules provides sufficient support for changing parts of the ios-device configuration. I resoved this problem by implementing a playbook that uses a list of regular-expressions to identify the managed-parts of the device configuration and jinja2 templates to remove or extract the selected configuration sections.

## Brownfield Workfow

To allow replacing the whole ios-device configuration while only some parts of it are managed-configuration I implemented a playbook that:

* reads the device configuration from network-device or a backup-file.
* removes the managed-configuration parts from the running-configuration via a list of regex that selects the configuration-sections.
* saves the remaining configuration as unmanaged-configuration.
* generates the managed-configuration from a hardware agnostic data model via Jinja2 templates.
* assembles the configuration parts into a single configuration file.
* uses napalm_install_config module to push configuration to device.
* displays the configuration differences that will be applied.

A big advantage in my opinion is that this workflow will allow the network-operators to continue doing their work the same way as usual. They just need to know which parts of the configuration are managed. Even if they change a part of the managed configuration, the playbook will list the difference so that appropriate actions can be taken.

## Known Limitations

* The napalm_install_config module will not allow to change the switchport type from `switchport mode trunk` to `switchport mode access`. Execute `default interface INTERFACENAME` for those ports before applying config with commit. The diff shows without problem.

## Manage Configuration via Regex

The Cisco IOS configuration is a structured textfile that uses one level of indention to group configuration sections.

e.g. the definition for a client switchport starts with the header-line `interface GigabitEthernet1/0/2` and all configuration lines for this interface are indented by one blank.

```text
interface GigabitEthernet1/0/2
 description Door-Lock no Voip
 switchport mode access
 switchport access vlan 40
 ip flow monitor IPv4_STEALTHWATCH_NETFLOW input
 storm-control multicast level 5.00
 storm-control broadcast level 5.00
 storm-control action trap
 storm-control action shutdown
 spanning-tree portfast
 spanning-tree guard root
 ip arp inspection limit rate 400 burst interval 3
!
```

Here you can see the Jinja2 template to remove such a configuration-section via a regex that also matches the above interface.

### Playbook Snippets

The full source of the playbook can be found on github.
INSERT MISSING LINK HERE!

```yaml
  ...

  vars:
    # Switch running configuration backup file. if empty the devic's
    # running-config wil be used
    src_config_filename: ""

    # Filename of assembled new configuration
    managed_config_dest: "{{ config_dir }}/{{ inventory_hostname }}_managed_configuration.{{ ansible_network_os }}"

    # Filenem or remaining unmanaged configuration
    unmanaged_config_dest: "{{ host_tmpdir }}/{{ inventory_hostname }}_0001_unmanaged_configuration.{{ ansible_network_os }}"

    # Regex to remove managed configuration sections from current switch
    delete_section_regex:
      - ^interface\s+GigabitEthernet.*$$
      - ^Building\s+configuration.*$$
      - ^Current\s+configuration.*$$
      - ^Load\s+for\s+five\s+secs.*$$
      - ^Time\s+source\s+is\s+NTP.*$$
      - ^vlan\s+\d*$$
      - ^ip access-list\s+standard\s+emergency-access$$
      - ^banner\s+.*\^C$$
      - ^end$$
      - ...

    # Regex to remove messages from config compare result
    delete_section_diff_result:
    - ^Load\s+for\s+five\s+secs.*$$
    - ^Time\s+source\s+is\s+NTP.*$$
```

On top of the playbook some common variables are defined. The delete_section_regex is an example. It's important to remove the 'end' statement at the end of the running-config and put it at the end of the assembled file. The configuration file will be loaded only to the 'end' statement.

In the playbook the regex for the client interface-configurations to remove will be generated from data-model, so the '^interface..' expression above is only an example.

```yaml
  tasks:

    ...

    - name: Read configuration from switch and store into src_config
      block:
        - napalm_get_facts:
            hostname: "{{ ansible_host  }}"
            username: "{{ ansible_user }}"
            dev_os: "{{ ansible_network_os }}"
            password: "{{ ansible_ssh_pass }}"
            timeout: 120
            filter:
              - "config"
        - set_fact:
            src_config: "{{ napalm_config.running }}"
      when:
        - src_config_filename == ""

```

The module nampalm_get_facts is used to read in the running-configuration from the device and is stored into src_config. This is time consuming, but it makes sure that all the latest changes made to the unmanaged-configuration are contaken int account.

```yaml
    - name: Remove all blocks or commands defined in delete_section_regex
      # The included tasks will re-read the var src_config from template output
      include_tasks: "{{ include_dir }}/inc_gen_unmanaged_configuration.yml"
      vars:
        template_dest: "{{ unmanaged_config_dest }}"
        del_section_regex: "{{ item }}"
      delegate_to: localhost
      loop: "{{ delete_section_regex }}"
```

To remove the configuration parts the include file is called within a loop for every list entry in delete_section_regex. See the include file below.

```yaml
---
#
# file: inc_gen_unmanaged_configuration.yml
#

- name: Check inc_gen_unmanaged_configuration Parameters
  assert:
    msg: "Missing Parameter in inc_gen_unmanaged_configuration.yml: del_section_regex or template_dest is not defined!"
    that:
      - del_section_regex is defined
      - del_section_regex > ""
      - template_dest is defined
      - template_dest > ""
  delegate_to: localhost

# The template uses the var src_config to render the output.
- template:
    src: "{{ template_dir }}/config_section_remover.j2"
    dest: "{{ template_dest }}"
    lstrip_blocks: true
  delegate_to: localhost

- name: Read the rendered output back to src_config. (chain)
  set_fact:
    src_config: "{{ lookup('file', template_dest ) }}"
  changed_when: false
  delegate_to: localhost

```

To be able to apply a sequence of regex removes, the include file reads the resulting config back to the var rc_config`. The final unmanaged configuration is stored in file "{{ template_dest }}".

```yaml

    - name: Generate VLAN Device-VLAN configuration
      include_tasks: "{{ include_dir }}/inc_template.yml"
      vars:
        dest_filename_part: "0010_vlan_configuration"
        template_dest: "{{ host_tmpdir }}/{{ inventory_hostname }}_{{dest_filename_part}}.{{ ansible_network_os }}"
        template_name: "config_vlans.j2"
      delegate_to: localhost

    - name: Write end marker
      copy:
        content: "end"
        dest: "{{ host_tmpdir }}/{{ inventory_hostname }}_9999_end.{{ ansible_network_os }}"
      delegate_to: localhost
```

Above example shows the generation of the device specific vlans. Because the assemble module will assemble selected files in a directory in alphabetical order of their filename, I prefixed te name with an 4 digit integer. The variable `host_tmpdir` points to a directory that includes the `inventory_hostname`. This ensures that the configurations keep separat per device.

```yaml
    - name: Assemble configuration
      assemble:
        src: "{{ host_tmpdir }}"
        dest: "{{ managed_config_dest }}"
        regexp: "^.*\\.{{ ansible_network_os }}$$"
      delegate_to: localhost
```

After all configuration snippets are available in directory `host_tmpdir`, the assemble statement selects all '*.ios' files and saves the configuration as file specified in `managed_config_dest`.

```yaml
    - name: Set Configuration - Check-Mode if do_commit is not defined
      napalm_install_config:
        config_file: "{{ managed_config_dest }}"
        commit_changes: "{{ do_commit is defined}}"
        replace_config: true
        get_diffs: true
        diff_file: "{{ managed_config_dest }}.diff"
        hostname: "{{ ansible_host  }}"
        username: "{{ ansible_user }}"
        dev_os: "{{ ansible_network_os }}"
        password: "{{ ansible_ssh_pass }}"
        timeout: 120
      register: result
      tags: [print_action]

```

The configuration is pushed to the device with the `napalm_install_config` module. Ansible provides the mechanism of enabling `check_mode` to make a dry-run. I personally don't like this behaviour that commit is default when specifying no extra parameter. This is why I introduced the `do_commit` variable that I specify as a commandline parameter when playbook should commit the changes.

```bash
ansible-playbook -i inv_production --limit SWITCH01 set_managed_configuration.yml -e do_commit=1
```

### Remove Template

Template to remove the section from `src_config`

```jinja
{# file: `config_section_remover.j2` #}
{# parameters: src_config, del_section_regex #}
{% set ns = namespace(is_in_block = false) %}
{% for line in src_config.split('\n') %}
{%   if ns.is_in_block %}
{%     if (line ~ 'x')[0] != ' ' %}
{%       if line != '!' %}
{%         set ns.is_in_block = false %}
{%       endif %}
{%     endif %}
{%   endif %}
{%   set found=line | regex_search(del_section_regex) %}
{%   if found %}
{%     set ns.is_in_block = true %}
{%   endif %}
{%   if not ns.is_in_block %}
{{ line }}
{%   endif %}
{% endfor %}
```

### Extractor Template

Template to save a configuration-section to a file

```jinja
{# file: `config_section_extractor.j2` #}
{# parameters: src_config, del_section_regex #}
{% set ns = namespace(is_in_block = false) %}
{% for line in src_config.split('\n') %}
{%   if ns.is_in_block %}
{%     if (line ~ 'x')[0] != ' ' %}
{%       if line != '!' %}
{%         set ns.is_in_block = false %}
{%       endif %}
{%     endif %}
{%   endif %}
{%   set found=line | regex_search(del_section_regex) %}
{%   if found %}
{%     set ns.is_in_block = true %}
{%   endif %}
{%   if ns.is_in_block %}
{{ line }}
{%   endif %}
{% endfor %}
```

### Banner Templates

Cisco IOS requires that the banner use the EXT character (ASCII 3). This looks like a cntl-C in the file, but as a single character. It is NOT a separate ‘^’ + ‘C’ character, but an ASCII3 character _(Barroso 2016, <https://napalm.readthedocs.io/en/latest/support/ios.html>)_.

Therefore the banner configuration must be extraced from configuration or be part of the managed configuration.

```jinja
{# file: `config_ios_banner_remover.j2` #}
{# parameters: src_config, banner_name #}{% set ns = namespace(is_in_block = false) %}
{% set ns.searchfor = '^banner\s+' ~ banner_name ~ '\s+\^C$$' %}
{% for line in src_config.split('\n') %}
{%   set found=line | regex_search(ns.searchfor) %}
{%   if found %}
{%     set ns.is_in_block = true %}
{%   elif ns.is_in_block %}
{%     if line.find('^C') != -1 %}
{%       set ns.is_in_block = false %}
{%     endif %}
{%   else %}
{{     line }}
{%   endif %}
{% endfor %}
```

```jinja
{# file: `config_ios_banner_extractor.j2` #}
{# parameters: src_config, banner_name #}
{% set ns = namespace(is_in_block = false) %}
{% set ns.searchfor = '^banner\s+' ~ banner_name ~ '\s+\^C$$' %}
{% set ns.is_first = true %}
{% for line in src_config.split('\n') %}
{%   set found=line | regex_search( ns.searchfor ) %}
{%   if found and ns.is_first %}
{%     set ns.is_in_block = true %}
{%     set ns.is_first = false %}
banner {{ banner_name ~ " \x03" }}
{%   elif ns.is_in_block %}
{%     if line.find('^C') != -1 %}
{%       set ns.is_in_block = false %}
{{       "\x03" }}
{%     else %}
{{       line }}
{%     endif %}
{%   endif %}
{% endfor %}
```

## Experiences

The solution was working fine but suffers from poor performance when it comes to edge switches that have up to 240 managed client ports. There the performance of looping over every single regex, parsing the whole configuration and re-read the result was not sufficient.

## Optimizations

To optimize the performance I've implemeted two Jinja2 filters in python that are far more performant than the Ansible loops.

### Filter: ios_config_section_extract

This filter is used to extract and optionally save the extracted configurations into a file.

To extraxt selected device configuration use filter: `ios_config_sectio_extact`.

Example:

```yaml
  - set_fact:
      src_config = "{{ src_config | ios_config_section_extract(regexp, ignorecase, prefix_str, filename) }}"

```

#### Input

The input (`src_config`) can be either a single string with line-separators or a list of strings.

#### Paramters

|Parameter|Required|Default|Description|
|---|---|---|---|
|regexp| Yes | | A list of strings containing the regular expressions to select the config-section headers. Also a single string can be passed. If line-start marker '^' or line-end marker '$' is omitted,the filter will set it. This allows to pass for e.g. the plain interface name and ensure that only the interface configuration will match and dot a string in any description.|
|ignorecase| No | false | If set to true, the regex matches strings case insensitive|
|prefix_str| No  | '' | Allows to prepend a common string to the regex data that is used for matching. This string will be directly prepended (`expr = self.prefix_str + pat`). Missing line-start and -end markers will be inserted automatically is needed. This allows for e.g. to pass a list o  vlan-numbers as `regex` and use the string 'vlan' as `prefix_str` to extract the specific vlan configurations that are selected by `regex`.|
|filename| No | '' | If a filename is passed, all the selected configurations will be saved as a textfile. The directory must exist.|

#### Result

* Selected configuration: list of strings
* Textfile:  if filename was specified the textfile will contain the selected configuration sections

### Filter: ios_config_section_remove

This filter is used to extract and optionally save the extracted configurations into a file.

Example:

```yaml
- name: Remove all blocks or commands defined in delete_section_regex
  set_fact:
    src_config: "{{ src_config | ios_config_section_remove(delete_section_regex) }}"
```

This filter has the same input, parameters and result as the `ios_config_section_extract` filter except it returns the content of `src_config` after deleting all selected configuration sections.

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
