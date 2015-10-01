"""Build all the desired documents from the Sonata wiki.
"""

# configuration:
import config

# imports:

import os
import glob
import re
import string
import shutil
import pickle
import subprocess
import pypandoc
from pprint import pprint as pp
from collections import defaultdict

import wikiconnector as wiki
import path_checksum

# debugging flags:
dbgDownload = True
dbgLatex = True


def ensure_dir(path):
    try:
        os.makedirs(path)
    except OSError:
        if not os.path.isdir(path):
            raise


def linesFromBulletlist(t):
    """Assume t is a mediawiki bullet list produced by readlines,
    one item per line.
    Return a list of the items, without the bullet syntax.
    """
    r = [re.sub(' *\* *', '', x, count=1)
         for x in t
         if re.match(' *\* *', x)]

    match = [re.search('\[\[ *(.*?) *\]\]', x) for x in r]

    r = [(m.group(1) if m else x.strip())
         for (x, m)
         in zip(r, match)]
    print r
    return r


def download(target, output, category=None):
    if dbgDownload:
        try:
            wiki.download(target=target,
                          output=output,
                          category=category)
        except:
            pass


def processUML(doc, directory):
    """extract any included UML, put them in the UML dir,
    write the reduced document back with an input command
    """

    print "UMLing ", doc, " in ", directory

    filename = os.path.join(directory,
                            doc + '.md')
    umldir = os.path.join(
        os.path.abspath(os.path.join(directory,
                                     os.pardir)),
        'uml')

    print filename, umldir

    # read the file:
    with open(filename, 'r') as f:
        data = f.read()

    i = 1
    m = re.search("<uml>(.*?)</uml>", data, re.S)
    while (m):
        umlfile = doc + "_" + str(i)
        with open(os.path.join(umldir,
                               umlfile + '.uml'),
                  'w') as umlhandle:

            umlhandle.write("@startuml")
            umlhandle.write(m.group(1))
            umlhandle.write("@enduml")

        # try to extract the title, to use for the caption:
        title_match = re.search("^title (.*)$",
                                m.group(1),
                                re.M)
        if title_match:
            title_text = title_match.group(1)
        else:
            title_text = "UML figure (no caption provided)"
            
        # trigger the generation of the actual UML figure
        subprocess.call(['java',
                         '-jar',
                         '../../plantuml.jar',
                         '-teps',
                         umlfile+'.uml'],
                        cwd=umldir)

        data = string.replace(data, m.group(0),
                              "[[File:" + umlfile +
                              ".eps|" + title_text + "]]",
                              1)
        i += 1
        m = re.search("<uml>(.*?)</uml>", data, re.S)

    with open(filename, 'w') as f:
        f.write(data)


def processRawFile(doc, directory):
    """Check whether the file qualifies as a raw file.
    If so, just copy it to the tex directory without further handling.
    Returns True is raw, False if not.
    """

    # add further tests here if desired:
    isRawFile = doc.endswith('.bib')

    print "raw: ", doc, isRawFile, directory
    if isRawFile:
        srcFilename = os.path.join(directory,
                                   doc)
        destFilename = os.path.abspath(
            os.path.join(directory,
                         '..',
                         'tex',
                         doc))
            
        print srcFilename, destFilename
        shutil.copy(srcFilename, destFilename)




def processPandoc(doc, directory):
    print "pandoc ", doc, directory

    filename = os.path.join(directory,
                            doc + '.md')

    outfile = os.path.join(
        os.path.join(
            os.path.abspath(os.path.join(directory,
                                         os.pardir)),
            'tex'),
        doc + '.tex')

    filters = [os.path.join(
        os.getcwd(),
        'linkFilter.py'),
         ]

    output = pypandoc.convert(filename,
                              format='mediawiki',
                              to='latex',
                              filters=filters,
                              extra_args=['--chapters'],
                              outputfile=outfile)
    print "padnoc output", output
    assert output == ""


def processFile(doc, directory):
    """process file doc in directory. Currently defined processing steps:
    - check whether it is a raw file, then just copy it and do nothing else 
    - extract all included umls and run them thorugh plant uml
    - run pandoc on the remaining file
    """

    if not processRawFile(doc, directory):
        processUML(doc, directory)
        processPandoc(doc, directory)


def prepareDirectory(docname, filelist, properties, rawlatex):
    # put the latex main document into the directory
    shutil.copy('templates/main.tex',
                os.path.join(docname,
                             'tex'))
    shutil.copy('templates/documentProperties.tex',
                os.path.join(docname,
                             'tex'))
    shutil.copy('templates/logo.jpg',
                os.path.join(docname,
                             'tex'))

    # prepare the additional properties:
    print "writing properties"
    with open(os.path.join(docname,
                           'tex',
                           'moreProperties.tex'),
              'w') as propFile:
        if properties:
            for k, v in properties:
                propFile.write(
                    '\\providecommand{{\\{}}}{{{}}}\n\\renewcommand{{\\{}}}{{{}}}\n'
                    .format(
                        k, v, k, v
                        ))

    # and any raw LaTeX we are given:
    if rawlatex:
        print rawlatex
        with open(os.path.join(docname,
                               'tex',
                               'rawtex.tex'),
                  'w') as rawtex:
            rawtex.write('\n'.join(rawlatex))

    # write the include instructions for the chapters:
    with open(os.path.join(docname,
                           'tex',
                           'includer.tex'),
              'w') as includer:

        if rawlatex:
            includer.write('\\include{rawtex}\n')
        for f in filelist:
            includer.write('\\include{' + f + '}\n')


def preProcessLatex(docdir):
    """Because of limitations in pondoc's mediawiki parser
    and Mediawiki's markup syntax, we need a few tricks 
    to get the right LaTeX for figure and table crossreferencing 
    as well as table column styles 
    """

    def replace_tablehead(m):
        print m
        print "======"
        print m.group(1)
        print "-----"
        print m.group(2)
        print "-----"
        print m.group(3)
        print "-----"
        print m.group(4)
        print "======"

        tmp = m.group(4)
        tmp = re.sub(r'\\{', '{', tmp)
        tmp = re.sub(r'\\}', '}', tmp)
        
        res = r"\begin{{longtable}}[c]{{{}}} \caption{{{}}}\label{{{}}}\tabularnewline".format(
            tmp,
            m.group(2),
            m.group(3),
            )
            
        print res
        return res

    print "preprocessing in ", docdir

    for f in glob.glob(os.path.join(docdir, '*.tex')):
        if f.endswith('main.tex'):
            continue
        print "copying ", f
        shutil.copy(f, f+'.bak')
        with open(f, 'r') as fhandle:
            doc = fhandle.read()

        # first, let's see if there is a table head with a caption, and labal, and position marks
        doc = re.sub(r'\\begin{longtable}\[c\]{(.*?)}\n\\caption{(.*?)\\#(.*?)\\#(.*)}\\tabularnewline',
                     # r'\\begin{longtable}[c]{\4}\caption{\2}\label{\3}\tabularnewline',
                     replace_tablehead,
                     doc,
                     flags=re.S)
        
        # second, lets create labels from the text after a hashmark of a caption:
        doc = re.sub(r'\\caption{(.*?)(\\#(.*?))}',
                     r'\caption{\1}\label{\3}',
                     doc,
                     flags=re.S)

        # looks not necessary on account of autoref: 
        # # third, turn any \url references into proper refs, unless they point to a true http
        # doc =  re.sub('\url{(?!http://)(.+?)}', '\\ref{\\1}', doc, flags=re.S)
        
        
        with open(f, 'w')  as fhandle:
            fhandle.write(doc)
        
            
def processLatex(docname):
    # run latx
    print os.path.join(docname, 'tex')

    preProcessLatex(os.path.join(docname, 'tex'))
    
    try:
        if dbgLatex:
            subprocess.check_output(
                ['pdflatex',
                 '-shell-escape',
                 '-interaction=nonstopmode',
                 'main.tex'],
                stderr=subprocess.STDOUT,
                cwd=os.path.join(docname, 'tex'),
            )
            subprocess.check_output(
                ['pdflatex',
                 '-shell-escape',
                 '-interaction=nonstopmode',
                 'main.tex'],
                stderr=subprocess.STDOUT,
                cwd=os.path.join(docname, 'tex'),
            )
            subprocess.check_output(
                ['pdflatex',
                 '-shell-escape',
                 '-interaction=nonstopmode',
                 'main.tex'],
                stderr=subprocess.STDOUT,
                cwd=os.path.join(docname, 'tex'),
            )
        e = None
    except subprocess.CalledProcessError as e:
        print e, e.output
        pass
    except Exception as e:
        print e

    return e


def getSection(text, section):
    """Assume text is a mediawiki formatted text.
    Assume it has L1 headings.
    Obtain the L1 heading with section as title
    """

    print "getSection: ", text, section
    m = re.search('= *' + section + ' *=([^=]*)',
                  text, re.S)

    if m:
        blocktext = m.group(1).strip()
        return blocktext.split('\n')
    else:
        return None


def processDocument(docname, fingerprint):
    print docname
    download(target=docname,
             output=docname)

    # make sure that at least md subdirectory is empty
    # later on, might remove all other stuff as well
    # (only clear, when folder already exists)
    # but only when actually download things!! not in debug mode!
    if dbgDownload:
        if os.path.exists(os.path.join(docname, 'md')):
            shutil.rmtree(os.path.join(docname, 'md'))

    ensure_dir(os.path.join(docname, 'figures'))
    ensure_dir(os.path.join(docname, 'uml'))
    ensure_dir(os.path.join(docname, 'md'))
    ensure_dir(os.path.join(docname, 'tex'))

    filelist = []

    # now grab the files for this document:
    with open(os.path.join(docname,
                           docname + '.md'),
              'r') as doc:

        doclines = doc.read()

    doctoc = getSection(doclines, 'TOC')
    docprop = getSection(doclines, 'Properties')
    doclatex = getSection(doclines, 'Latex')

    # process the toc: which files to download, include?
    if doctoc:
        for doc in linesFromBulletlist(doctoc):
            doc = doc.strip()
            if doc:
                print "processing: >>", doc, "<<"
                mddir = os.path.join(docname, 'md')
                try:
                    download(target=doc,
                             output=mddir)

                    # process each document separately
                    processFile(doc, mddir)
                    filelist.append(doc)
                except:
                    pass

    # process any additional properties:
    if docprop:
        tmp = linesFromBulletlist(docprop)
        tmp = [x.split(':') for x in tmp]
        tmp = filter(lambda x: len(x) == 2, tmp)

        properties = [(k.strip(), v.strip())
                      for (k, v) in tmp]
        print properties
    else:
        properties = None

    # prepare directory
    prepareDirectory(docname, filelist, properties, doclatex)

    # check against fingerpint
    newfingerprint = path_checksum.path_checksum(
        [os.path.join(docname, 'md')])

    print "fingerprints: ", fingerprint, newfingerprint
    if not fingerprint == newfingerprint:
        e = processLatex(docname)
    else:
        print "nothing has changed in ", docname
        e = None

    return e, newfingerprint

    # report the results back: stdout, pdf file


def main():
    # initialize wiki connection
    try:
        if dbgDownload:
            wiki.setup_connection(host=config.WIKIROOT,
                                  user=config.USER,
                                  password=config.PASSWORD)
    except:
        print "Connection to remote wiki broken. Stopping."
        exit(1)

    # try to get the fingerprints:
    try:
        with open('fingerprints', 'r') as fp:
            fingerprints = pickle.load(fp)
    except:
        fingerprints = defaultdict(str)

    # start the download
    print "downloading documentlist"
    download(target=config.DOCUMENTLIST,
             output="DocumentList")

    print os.getcwd()
    fname = os.path.join('DocumentList',
                         config.DOCUMENTLIST + '.md')
    print fname
    print os.path.abspath(fname)
    # iterate over the documents contained in documentlist:
    with open(fname,
              'r') as f:
        for line in linesFromBulletlist(f.readlines()):
            e, newfp = processDocument(line,
                                       fingerprints[line])

            if not fingerprints[line] == newfp:
                if dbgDownload:
                    wiki.upload_document(line, e)
                fingerprints[line] = newfp

    with open('fingerprints', 'w') as fp:
        pickle.dump(fingerprints, fp)

if __name__ == '__main__':
    main()
