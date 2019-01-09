# -*- coding: utf-8 -*-

import re
import copy

class MissingEndOfBannerError(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message


class IosConfigRegexp:
    '''
    A class used to manipulate cisco ios configuration-sections via regexp.

    The class IosConfigRegexp allows to remove or extract configuration-
    sections (i.e. intended blocks) from an ios-configuration.

    Attributes
    ----------

    conf_lines: list
        contains the ios-configuration.
    ignorecase: bool
        set to True to perform case insensitive regexp searches
    prefix_str: str
        string that will be prepended to all regexp in regexplist
    regexplist: list, str
        regular expressions to identify configuration-section headers

    Methods
    -------

    __init__(self, config=None, regexplist=list(), ignorecase=False, prefix_str='')
        constructor
    is_match(self, i: int) -> bool
        Match all select-patterns against the string conf_line[i].
    extract_section(self) -> list
        returns the configuration without the selected configuration-sections.
    remove_section(self) -> list
        returns the whole configuration without the selected
        configuration-sections.
    '''
    __ignorecase = False
    __regexplist = list()
    __conf_lines = list()
    __re_flags = 0
    __prev_line = ''

    def __init__(self, config=None, regexplist=list(), ignorecase=False, prefix_str=''):
        self.conf_lines = config
        self.regexplist = regexplist
        self.ignorecase = ignorecase
        self.prefix_str = prefix_str
        self.__prev_line = ''

    # property ignorecase
    @property
    def ignorecase(self):
        return self.__ignorecase
    @ignorecase.setter
    def ignorecase(self, value):
        '''   when set to true, regexp will use re.IGNORECASE '''
        if value == None or not value:
            self.__ignorecase = False
            self.__re_flags = 0
        else:
            self.__ignorecase = True
            self.__re_flags = re.IGNORECASE

    # property conf_lines
    @property
    def conf_lines(self) -> list:
        return self.__conf_lines

    @conf_lines.setter
    def conf_lines(self, value):
        ''' property conf_lines set the ios-configuration as a list of strings '''
        if value == None:
            self.__conf_lines = list()
        elif isinstance(value, str):
            self.__conf_lines = value.splitlines()
        elif isinstance(value, list):
            self.__conf_lines = copy.deepcopy(value)
        else:
            raise ValueError("IosConfigRegexp.conf_lines must be a list of strings!")

    # property regexplist
    @property
    def regexplist(self):
        return self.__regexplist

    @regexplist.setter
    def regexplist(self, value):
        if value == None:
            self.__regexplist = list()
        elif isinstance(value, str):
            self.__regexplist = value.splitlines()
        elif isinstance(value, list):
            self.__regexplist = copy.deepcopy(value)
        else:
            raise ValueError("IosConfigRegexp.regexplist must be a list of strings!")

        if len(self.__regexplist) > 0:
            for i in range(0, len(self.__regexplist)):
                # allow using extracetd banner for further filtering
                pos = self.__regexplist[i].find(r"\^C")
                if pos != -1:
                    s = self.__regexplist[i][:pos] + "\x03" + self.__regexplist[i][pos+3:]
                    self.__regexplist.append(s)

    def is_match(self, i: int) -> bool:
        ''' match all regexp to current line indexed by i '''
        line = self.conf_lines[i]
        for pat in self.regexplist:
            expr = self.prefix_str + pat
            if expr[0:1] != '^':
                expr = '^' + expr
            if expr[-1:]  != '$':
                expr = expr + '$'
            m = re.match(expr, line, self.__re_flags)
            if m:
                return True
        return False

    def is_banner(self, idx):
        ''' Checks if conf_line[idx] is a banner header '''
        return (self.conf_lines[idx].lower().find('banner ') != -1
                and (self.conf_lines[idx][-2:] == '^C' or self.conf_lines[idx][-1:] == "\x03"))

    def _extract_section(self, i: int, res: list) -> int:
        ''' Extract ios configuration-section starting at line i '''
        is_in_section = True
        while i < len(self.conf_lines) and is_in_section:
            # append current line
            if (self.__prev_line != '!' or self.conf_lines[i] != '!'):
                res.append(self.conf_lines[i])
                self.__prev_line = self.conf_lines[i]

            # examine next line
            i += 1
            if i < len(self.conf_lines):
                li = self.conf_lines[i]
                if (li + 'X')[0] != ' ':
                    is_in_section = False
        return i

    def _remove_section(self, i: int, res: list) -> int:
        ''' Remove ios configuration-section starting at line i '''
        is_in_section = True
        while i < len(self.conf_lines) and is_in_section:
            i += 1
            if i < len(self.conf_lines):
                li = self.conf_lines[i]
                if (li + 'X')[0] != ' ':
                    is_in_section = False
        return i

    def _extract_banner(self, i: int, res: list) -> int:
        ''' Extract ios-banner starting at line i '''
        is_in_section = True
        is_first = True
        ErrMsg = ("Error in IosConfigRegexp.extract_banner: "
                  "Missing block-end for line-no {} - '{}'").format(i, self.conf_lines[i])
        while i < len(self.conf_lines) and is_in_section:
            if is_first:
                # modify for napalm_install_config compatibility
                res.append(self.conf_lines[i][:-2] + "\x03")
                is_first = False
            else:
                # examine next line
                if i >= len(self.conf_lines):
                    raise MissingEndOfBannerError(ErrMsg)
                li = self.conf_lines[i]
                if (li)[-2:] == '^C' or (li)[-1:] == "\x03":  # ^C at eol
                    is_in_section = False
                    res.append("\x03")
                else:
                    res.append(li)
            i += 1
        if is_in_section:
            raise MissingEndOfBannerError(ErrMsg)
        return i

    def _remove_banner(self, i: int, res: list) -> int:
        ''' Remove ios-banner starting at line i '''
        is_in_section = True
        ErrMsg = ("Error in IosConfigRegexp.remove_banner: "
                  "Missing block-end for line-no {} - '{}'").format(i, self.conf_lines[i])
        while i < len(self.conf_lines) and is_in_section:
            i += 1
            if i >= len(self.conf_lines):
                raise MissingEndOfBannerError(ErrMsg)
            li = self.conf_lines[i]
            if (li)[-2:] == '^C' or (li)[-1:] == "\x03":  # ^C at eol
                i += 1
                is_in_section = False
        if is_in_section:
            raise MissingEndOfBannerError(ErrMsg)
        return i

    def extract_section(self) -> list:
        '''
        Returns the selected configuration-section out of conf_lines

        Returns
        -------

        list
            Selected parts of the configuration or an
            empty list if nothing was found.
        '''
        res = list()
        i = 0
        self.__prev_line = ''
        while i < len(self.conf_lines):
            if self.is_match(i):
                if self.is_banner(i):
                    i = self._extract_banner(i, res)
                else:
                    i = self._extract_section(i, res)
            else:
                i += 1
        return res

    def remove_section(self) -> list:
        '''
        Returns the configuration without the selected configuration-section.

        Returns
        -------
        list
            Content of `conf_lines` without the selected configuration-sections.
        '''
        res = list()
        i = 0
        self.__prev_line = ''
        while i < len(self.conf_lines):
            if self.is_match(i):
                if self.is_banner(i):
                    i = self._remove_banner(i, res)
                else:
                    i = self._remove_section(i, res)
            else:
                if (self.__prev_line != '!' or self.conf_lines[i] != '!'):
                    res.append(self.conf_lines[i])
                    self.__prev_line = self.conf_lines[i]
                i += 1
        return res
