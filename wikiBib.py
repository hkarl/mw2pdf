"""Convert wiki bibformat as invented by Jose Bonnet into bibtex
"""

import sys
import os
import collections
import re

def readwiki(filename):
    entries = []
    with open(filename, 'r') as fp:
        lines = fp.readlines()

    # in d, we store what we know about the current entry
    d = {}

    for l in lines:
        # do we start a new entry?
        try:
            m = re.match('\s*=+(.*?)=+', l)
            key = m.group(1)

            print "found key", key

            # if no exception up to hear, we have found a new entry strat
            # store the old entry:
            if d:
                entries.append(d)

            # start remembering the new entry:
            d = {'key': key.strip().lower(),
                 'type': 'misc'}

            print "dict: ", d
            continue
        except:
            pass

        print l
        m = re.match('\s*\*\s*(.*?)\s*:\s*(.*)', l)
        try:
            key = m.group(1)
            val = m.group(2)
            d[key.strip()]  = val.strip()
        except:
            pass

    entries.append(d)

    return entries


def writebib(entries, outfile):

    keys = []

    with open(outfile, 'a') as fp:
        for e in entries:
            key = e['key']
            keys.append(key)
            fp.write("@{}{{{},\n".format(e['type'],
                                        key))
            for k,v in e.iteritems():
                fp.write(' {} = {{{}}},\n'.format(k,v))
            fp.write('}\n\n')

    return keys


def wikibib(infile, outfile):
    entries = readwiki(infile)
    return writebib(entries, outfile)


if __name__ == '__main__':
    wikibib(sys.argv[1], 'bla.bib')
