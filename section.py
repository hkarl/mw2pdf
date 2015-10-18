"""A small helper module to deal with sections in the control page.
"""


import os
import re
import wikiconnector


def linesFromBulletlist(t):
    """Assume t is a mediawiki bullet list produced by readlines,
    one item per line.
    Return a list of the items, without the bullet syntax.
    """
    r = [re.sub(' *\* *', '', x, count=1)
         for x in t
         if re.match(' *\* *', x)]

    # get the content of the link:
    match = [re.search('\[\[ *(.*?) *\]\]', x) for x in r]

    r = [(m.group(1) if m else x.strip())
         for (x, m)
         in zip(r, match)]

    # remove any possible readable name suffices
    match = [re.search('(.*?)\|(.*)', x) for x in r]

    r = [(m.group(1) if m else x.strip())
         for (x, m)
         in zip(r, match)]

    print r
    return r

#------------------------------------------
# helper functions to deal with sections

def getSection(text, section):
    """Assume text is a mediawiki formatted text.
    Assume it has L1 headings.
    Obtain the L1 heading with section as title
    """

    # print "getSection: ", text, section
    m = re.search('= *' + section + ' *=([^=]*)',
                  text, re.S)

    if m:
        blocktext = m.group(1).strip()
        return blocktext
    else:
        return ""


def getSectionLines(text, section):
    blocktext = getSection(text, section)
    if blocktext:
        return blocktext.split('\n')

    return []


def writeSectionContent(text, section,
                        filename):
    """grab content of a desired section
    and write it into a file.
    """

    content = getSection(text, section)

    with open(filename, 'w') as fp:
        fp.write(content)

    return content


def downloadSectionFiles(text, section, dirname, downloadFlag):
    """download all files mentioned
    in the given section as a bullet list.
    download them to dirname.
    return list of successfull file names
    """

    filenames = linesFromBulletlist(
        getSectionLines(text, section))

    print "filenames: ", filenames
    r = []

    for f in filenames:
        tmp = f.strip()
        print "trying to download: ", tmp, '\n'
        if tmp:
            if downloadFlag:
                try:
                    wikiconnector.download(
                        target=tmp,
                        output=dirname)

                    r.append(f)
                except:
                    pass
            else:
                # no download, but does the file already exist locally?
                fname = os.path.join(dirname, tmp + '.md')
                print "tmp: >>>", tmp, "<<<", dirname, fname

                try:
                    fp = open(fname, 'r')
                    r.append(tmp)
                    fp.close()
                except:
                    pass

    print "reutrning: ", r
    return r


def getBullets(text, section):
    return linesFromBulletlist(
        getSectionLines(text, section))


def getProperties(text, section):
    tmp = getBullets(text, section)
    tmp = [x.split(':') for x in tmp]
    tmp = filter(lambda x: len(x) == 2, tmp)

    properties = [(k.strip(), v.strip())
                  for (k, v) in tmp]

    return properties
