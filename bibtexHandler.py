"""this file encapsulates the bibtex handling routines.
Only in a separate file because elpy crashed on bibtexparser import :-(
"""

import bibtexparser
import re
import os

def processBibtex(docname, bibtex):
    """process a raw bibtex input as downloaded from wiki.

    Main steps:
    - remove any wiki anchors
    - sanitize via bibtex library
    - write out bibtex file
    - return a list of bibtex keys, necessary for postprocessing latex

    input:
    - docname: document and subdirectory to be processed
    - bibtex: string containing the collated files

    output:
    - list of bibtex keys
    """

    # remove any wiki anchors, as defined in
    # https://meta.wikimedia.org/wiki/Help:Anchors

    bibtex = re.sub('<( *)div(.*?)>', '', bibtex, re.S)
    bibtex = re.sub('<( *)/( *)div(.*?)>', '', bibtex, re.S)

    # sanitize via bibtex library
    parser = bibtexparser.bparser.BibTexParser()
    parser.customization = bibtexparser.customization.homogeneize_latex_encoding
    bibDB = bibtexparser.loads(bibtex,
                               parser=parser)

    # lowercase all the bibtex keys, just because that's the way pandoc inserts the refs:
    for e in bibDB.entries:
        e['ID'] = e['ID'].lower()


    # dump it to file
    writer = bibtexparser.bwriter.BibTexWriter()
    with open (os.path.join(docname, 'tex', 'bib.bib'),
               'w') as bh:
        bh.write(writer.write(bibDB))

    # get a list keys to return:
    keys = [x['ID'] for x in bibDB.entries]
    print "bibtexkeys (1): ", keys
    return keys
