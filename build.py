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
import itertools
import argparse
import tarfile

import wikiconnector as wiki
import path_checksum
from bibtexHandler import processBibtex

import wikiBib



import section


# global variables
bibtexkeys = []     # ugly hack to make this global :-/


def ensure_dir(path):
    try:
        os.makedirs(path)
    except OSError:
        if not os.path.isdir(path):
            raise


def download(target, output, category=None, embedded_elements=True):
    try:
        wiki.download(target=target,
                      output=output,
                      category=category,
                      embedded_elements=embedded_elements)
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
        # try to extract the title, to use for the caption:
        title_match = re.search("^title (.*)$",
                                m.group(1),
                                re.M)
        if title_match:
            title_text = title_match.group(1)
        else:
            title_text = "UML figure (no caption provided)"

        # remove title_text from contents written to UML file
        # (we only want Latex figure captions)
        umlcontent = str(m.group(1)).replace("title " + title_text, "")

        # write uml to file for further processing by plantUML
        umlfile = doc + "_" + str(i)
        with open(os.path.join(umldir,
                               umlfile + '.uml'),
                  'w') as umlhandle:

            umlhandle.write("@startuml")
            umlhandle.write(umlcontent)
            umlhandle.write("@enduml")

        if True:
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

    return isRawFile


def processPandoc(doc, directory):

    def guessFormat(filename):
        """Try to guess whether the file contains
        clean mediawiki syntax or messed-up HTML markup from
        the stupid Rich Editor
        """

        with open (filename, 'r') as f:
            text = f.read()

        htmlCount = len(re.findall("< *h[1-9] *>", text))
        wikiCount = len(re.findall("=+.+=+", text))

        if htmlCount > wikiCount:
            frmt = "html"
        else:
            frmt = "mediawiki"

        print "guessing format: ", filename, frmt

        return frmt


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
                              format=guessFormat(filename),
                              to='latex',
                              filters=filters,
                              extra_args=['--chapters'],
                              outputfile=outfile)
    print "padnoc output", output
    assert output == ""


def processFile(doc, directory, umlFlag):
    """process file doc in directory. Currently defined processing steps:
    - check whether it is a raw file, then just copy it and do nothing else
    - extract all included umls and run them thorugh plant uml
    - run pandoc on the remaining file
    """

    if not processRawFile(doc, directory):
        if umlFlag:
            processUML(doc, directory)
        processPandoc(doc, directory)


def prepareDirectory(docname, filelist, appendixlist,
                     properties, rawlatex):
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
    shutil.copy('templates/sonata-logo-large.png',
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
            includer.write('\\input{rawtex}\n')
        for f in filelist:
            includer.write('\\input{' + f + '}\n')

    # write the appendixlist:
    with open(os.path.join(docname,
                           'tex',
                           'appendixlist.tex'),
              'w') as appendixfile:

        appendixfile.write('% appendix\n\n')

        print "appendix: ", appendixlist, filelist

        for f in appendixlist:
            appendixfile.write('\\input{' + f + '}\n')


def processCiteKeys(doc):
    """Turn all the autorefs to bibkeys into cites.

    input:
    - doc is a latex document
    - global variable: bibtexkeys, contains all the keys found in the bibfiles

    output:
    - the rewritten doc
    """

    global bibtexkeys

    # because autoref has the underscores translated to -,
    # (done by the linkFilter.py filter)
    # we have to do the same thing here to the bibtexkeys.

    newbibkeys = [re.sub('_', '-', x) for x in bibtexkeys]
    # print "bibtexkeys: ", newbibkeys

    pattern = 'autoref{(' + '|'.join(newbibkeys) + ')}'
    doc = re.sub(pattern, 'cite{\\1}', doc)

    # and now we have to replace them back to the underscore version,
    # which is the one that is in the bibtex file, probably
    # (this is far too complicated - need a better way to deal with
    # the bloody stupid inconstiency of autoref vs label generation)

    deltaKeys = [(x, y)
                 for (x, y) in zip(bibtexkeys, newbibkeys)
                 if not x == y]
    # print "delatakeys: ", deltaKeys
    for orgkey, wrongkey in deltaKeys:
        # we need to lower-case the citation key for the bib file
        # because the references get all lower-cased by linkFilter
        # (this is becuase the mediawiki reader lower-cases all the
        # labels for headings, and there is no easy way to distinguish
        # links to headings from links to references )
        o = '\\cite{' + orgkey.lower() + '}'
        w = '\\cite{' + wrongkey + '}'

        doc = doc.replace(w, o)

    return doc


def insertFilenameLabel(doc, filename):

    print "inserting: ", filename
    # get basename, remove extension

    f = os.path.basename(filename)
    f = os.path.splitext(f)[0]
    f = re.sub('_', '-', f)
    f = f.lower()

    tmp = re.sub(
        "((subsubsection|subsection|section|chapter|paragraph|subparagraph){.*?})",
        "\\1\\label{" + f + "}", doc,
        count=1,
        flags=re.DOTALL)

    return tmp

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

        caption = m.group(2)

        label = m.group(3).lower()

        width = m.group(4)
        width = re.sub(r'\\{', '{', width)
        width = re.sub(r'\\}', '}', width)

        # support percentage statements in table column widths:
        width = re.sub(r'p\s*{\s*([0-9]+)\s*\\%\s*}', 'p{.\\1\\\\textwidth}', width, re.S)
        print "width: ", width
        print "======"

        if caption:
            res = r"\begin{{longtable}}[c]{{{}}} \caption{{{}}}\label{{{}}}\tabularnewline".format(
                width,
                caption,
                label,
            )
        else:
            res = r"\begin{{longtable}}[c]{{{}}}\tabularnewline".format(
                width,
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
        doc = re.sub(r'\\begin{longtable}\[c\]{(.*?)}\n\\caption{(.*?)\\#(.*?)\\#(.*?)}\\tabularnewline',
                     # r'\\begin{longtable}[c]{\4}\caption{\2}\label{\3}\tabularnewline',
                     replace_tablehead,
                     doc,
                     flags=re.S)

        # second, lets create labels from the text after a hashmark of a caption:
        doc = re.sub(r'\\caption{(.*?)(\\#(.*?))}',
                     # r'\caption{\1}\label{\3}',
                     lambda m: r'\caption{{{}}}\label{{{}}}'.format(
                         m.group(1),
                         m.group(3).lower()),
                     doc,
                     flags=re.S)

        # third: there might be undersscorces in labels. right in principle, but
        # they get escaped by pandoc with an \ . We have to remove the backslash here
        doc = re.sub(r'\\label{(.*?)}',
                     lambda m: '\label{' + re.sub(r'\\', '', m.group(1)) + '}',
                     doc)

        # looks not necessary on account of autoref:
        # # foruth, turn any \url references into proper refs, unless they point to a true http
        # doc =  re.sub('\url{(?!http://)(.+?)}', '\\ref{\\1}', doc, flags=re.S)

        # handle cites
        doc = processCiteKeys(doc)

        # insert a label with the file name after the first section
        doc = insertFilenameLabel(doc, f)

        with open(f, 'w')  as fhandle:
            fhandle.write(doc)


def processLatex(docname):

    def oneRunLatex(docname):
        e = None
        try:
            subprocess.check_output(
                ['pdflatex',
                 '-shell-escape',
                 '-interaction=nonstopmode',
                 'main.tex'],
                stderr=subprocess.STDOUT,
                cwd=os.path.join(docname, 'tex'),
            )
        except subprocess.CalledProcessError as e:
            print e, e.output
            pass

        return e

    def oneRunBibtex(docname):
        e = None
        try:
            subprocess.check_output(
                ['bibtex',
                 'main'],
                stderr=subprocess.STDOUT,
                cwd=os.path.join(docname, 'tex'),
            )
        except subprocess.CalledProcessError as e:
            print e, e.output
            pass

        return e


    e = None
    try:
        print "latex first pass"
        e = oneRunLatex(docname)
        print "bibtex"
        e = oneRunBibtex(docname)
        print "latex second pass"
        e = oneRunLatex(docname)
        print "latex third pass"
        e = oneRunLatex(docname)

    except Exception as e:
        print e

    return e



def processDocument(docname,
                    fingerprint,
                    downloadFlag,
                    latexFlag,
                    umlFlag,
                    embeddedElemetsFlag):
    global bibtexkeys

    print "========================================"
    print "processing document: ", docname

    if downloadFlag:
        # note: we never download embedded elements from control page
        # as this might point to producedd PDF or tar files.
        # we do that in more fine-grained manner below
        download(target=docname,
                 output=docname,
                 #embedded_elements=embeddedElemetsFlag,
                 embedded_elements=False,
        )

        # make sure that at least md subdirectory is empty
        # later on, might remove all other stuff as well
        # (only clear, when folder already exists)
        # but only when actually downloading things!! not in debug mode!

        if os.path.exists(os.path.join(docname, 'md')):
            shutil.rmtree(os.path.join(docname, 'md'))

    ensure_dir(os.path.join(docname, 'figures'))
    ensure_dir(os.path.join(docname, 'uml'))
    ensure_dir(os.path.join(docname, 'md'))
    ensure_dir(os.path.join(docname, 'tex'))
    bibdir = os.path.join(docname, 'bib')
    ensure_dir(bibdir)

    filelist = []

    # now grab the files/wiki pages for this document:
    with open(os.path.join(docname,
                           docname + '.md'),
              'r') as doc:

        doclines = doc.read()

    # doctoc = section.getSectionLines(doclines, 'TOC')
    # docprop = section.getSectionLines(doclines, 'Properties')
    doclatex = section.getSectionLines(doclines, 'Latex')
    # docbibtex = section.getSectionLines(doclines, 'Bibtex')
    # docwikibib = section.getSectionLines(doclines, 'Wikibib')

    # --------------------------------------------
    # handle abstract, ensure there is always a possibly empty file

    section.writeSectionContent(
        doclines, 'Abstract',
        os.path.join(docname,
                     'md',
                     'propertiesAbstract.md'))

    processFile('propertiesAbstract',
                os.path.join(docname, 'md'),
                umlFlag)

    # -------------------------------------------
    # handle bibtex entries

    bibtex = ""
    # there should always be an even empty bib.bib in tex folder
    with open(os.path.join(docname,
                           'tex', "bib.bib"),
              'w')  as bh:
        bh.write('% empty bibtex file\n')
    bibtexkeys = []

    for f in section.downloadSectionFiles(doclines,
                                          'Bibtex',
                                          bibdir,
                                          downloadFlag,
                                          embeddedElemetsFlag):
        print "bibtex: ", f
        with open(os.path.join(bibdir, f+'.md'), 'r') as fh:
            bibtex += fh.read()
    bibtexkeys = processBibtex(docname, bibtex)

    for doc in section.downloadSectionFiles(doclines,
                                            'Wikibib',
                                            bibdir,
                                            downloadFlag,
                                            embeddedElemetsFlag):
        bibtexkeys += wikiBib.wikibib(infile=os.path.join(bibdir,
                                                          doc + '.md'),
                                      outfile=os.path.join(docname,
                                                           'tex',
                                                           'bib.bib'))

    print "bibtexkeys (2):", bibtexkeys

    #--------------------------------------------------
    # process the toc: which files to download, include?
    mddir = os.path.join(docname, 'md')
    filelist = section.downloadSectionFiles(doclines,
                                            'TOC',
                                            mddir,
                                            downloadFlag,
                                            embeddedElemetsFlag)
    for doc in filelist:
        print "processing: >>", doc
        processFile(doc, mddir, umlFlag)

    # similar for possible appendices:
    appendixlist = section.downloadSectionFiles(doclines,
                                                'Appendix',
                                                mddir,
                                                downloadFlag,
                                                embeddedElemetsFlag)
    for doc in appendixlist:
        print "processing: >>", doc
        processFile(doc, mddir, umlFlag)


    #=============================================
    # process any additional properties:

    properties = section.getProperties(doclines, 'Properties')

    #=============================================
    # copy figures to figures directory, fix spaces in file name!
    figextensions = ['png', 'jpg', 'jpeg', 'eps', 'pdf', 'PNG', 'JPG', 'JPEG', 'EPS', 'PDF']
    figurefiles = list(itertools.chain.from_iterable(
        [glob.glob(os.path.join(docname,
                                'md',
                                '*.' + ext))
         for ext in figextensions]))

    # just the filenames, not the paths:
    figurefiles = [os.path.basename(f) for f in figurefiles]

    # and copy the figures to the figures directory,
    # replace spaces by underscores:
    for f in figurefiles:
        shutil.copy(os.path.join(docname, 'md', f),
                    os.path.join(docname, 'figures', re.sub(' ', '_', f)))

    print figurefiles

    #===========================================
    # start the actual processing
    # prepare directory
    prepareDirectory(docname, filelist, appendixlist, properties, doclatex)

    # check against fingerpint
    newfingerprint = path_checksum.path_checksum(
        [os.path.join(docname, 'md')])
    print "fingerprints: ", fingerprint, newfingerprint

    # which latexing actions do we have to perform?
    e = None
    if (not fingerprint == newfingerprint):
        preProcessLatex(os.path.join(docname, 'tex'))
        if latexFlag:
            e = processLatex(docname)
    else:
        print "nothing to be done in ", docname

    return e, newfingerprint

    # report the results back: stdout, pdf file


def setup_cli_parser():
    """
    Command-line switches, mostly to help with debugging.
    """

    parser=argparse.ArgumentParser(
        description="Translate a set of Mediwiki into PDF via pandoc and LaTeX.")

    parser.add_argument("--download",
                        dest="download",
                        default=False,
                        action="store_true",
                        help="Download from the given wiki (default: False)",
                        )

    parser.add_argument("--document",
                        dest="document",
                        default=None,
                        help="Only process the given document"
                        )

    parser.add_argument("--latex",
                        dest="latex",
                        default=False,
                        action="store_true",
                        help="Run LaTeX (default: False)",
                        )

    parser.add_argument("--upload",
                        dest="upload",
                        default=False,
                        action="store_true",
                        help="Upload resulting PDF to wiki (default: False)",
                        )

    parser.add_argument("--ignore-fingerprint",
                        dest="ignoreFingerprint",
                        default=False,
                        action="store_true",
                        help="Ignore fingerprint, always process (default: False)",
                        )

    parser.add_argument("--uml",
                        dest="uml",
                        default=False,
                        action="store_true",
                        help="Run the plantuml conversion script  (default: False)"
                        )

    parser.add_argument("-p",
                        dest="production",
                        default=False,
                        action="store_true",
                        help="Set all switches to values for a production run."
                        )

    parser.add_argument("--no-elements",
                        dest="noEmbeddedElements",
                        default=False,
                        action="store_true",
                        help="Do not download embedded elements (e.g. images from wiki pages) (default: False)",
                        )

    return parser


def get_documentlist(document, downloadFlag, embeddedElemetsFlag):
    """Determine documents to process.
    Command-line args takes precedence over anything
    that could be downloaded.
    """

    if document:
        return [document]

    documentlist = []
    if downloadFlag:
        # start the download
        print "downloading documentlist"
        download(target=config.DOCUMENTLIST,
                 output="DocumentList", embedded_elements=embeddedElemetsFlag)

        # process the downloaded documentlist:
        fname = os.path.join('DocumentList',
                             config.DOCUMENTLIST + '.md')
        with open(fname,
                  'r') as f:
            documentlist = section.linesFromBulletlist(f.readlines())

    return documentlist


def main(args):

    # initialize wiki connection
    try:
        if args.download:
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

    # iterate over the documents contained in documentlist:
    for line in get_documentlist(args.document,
                                 args.download,
                                 not args.noEmbeddedElements):

        # if we are to ignore fingerprints, let's just pass in a stupid
        # value:
        e, newfp = processDocument(line,
                                   (fingerprints[line]
                                    if not args.ignoreFingerprint
                                    else None),
                                   args.download,
                                   args.latex,
                                   args.uml,
                                   not args.noEmbeddedElements)


        if ((not fingerprints[line] == newfp) or
            (args.ignoreFingerprint)):
            if args.upload:
                # produce tarfile of the produced latex and figure documents
                with tarfile.open(os.path.join(line, line+'-latex.tgz'),
                                  'w:gz') as tar:
                    tar.add(os.path.join(line, 'tex'))
                    tar.add(os.path.join(line, 'figures'))
                    tar.add(os.path.join(line, 'bib'))
                    tar.add(os.path.join(line, 'uml'))

                wiki.upload_document(line, e)


        fingerprints[line] = newfp

    with open('fingerprints', 'w') as fp:
        pickle.dump(fingerprints, fp)


if __name__ == '__main__':

    parser = setup_cli_parser()
    args = parser.parse_args()

    if args.production:
        args.download = True
        args.document = None
        args.latex = True
        args.upload = True
        args.ignoreFingerprint = False
        args.uml = True
        args.noEmbeddedElements = False

    main(args)
