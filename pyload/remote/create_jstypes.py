#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from os.path import abspath, dirname, join

path = dirname(abspath(__file__))
module = join(path, "..")

from . import apitypes
from .apitypes_debug import enums

# generate js enums
def main():

    print("generating apitypes.js")

    f = open(join(module, 'web', 'app', 'scripts', 'utils', 'apitypes.js'), 'wb')
    f.write("""// Autogenerated, do not edit!
/*jslint -W070: false*/
define([], function() {
\t'use strict';
\treturn {
""")

    for name in enums:
        enum = getattr(apitypes, name)
        values = dict([(attr, getattr(enum, attr)) for attr in dir(enum) if not attr.startswith("_")])

        f.write("\t\t%s: %s,\n" % (name, str(values)))

    f.write("\t};\n});")
    f.close()


if __name__ == "__main__":
    main()
