"""
    wiki-fetcher.py

    Script to download MediaWiki pages and all embedded
    documents, like images, PDFs, etc.

    (c) 2015 by Manuel Peuster
    manuel (dot) peuster (at) upb (dot) de
"""
"""
    TODO:
        * add recursive mode "-r": Download all content linked
          from a given page (maybe with max_depth parameter)
"""

import argparse
import os
import re
import subprocess
from pprint import pprint as pp
import mwclient  # pip install mwclient

# global pointer to our active wiki
SITE = None


def setup_connection(host, user=None, password=None):
    """
    Setup mwclient connection to wiki
    """
    global SITE
    SITE = mwclient.Site(host, path='/')
    if user is not None:
        SITE.login(user, password)


def no_archived_elements(img_list):
    """
    Removes old revisions from image list.
    Old versions can be identified by having
    'archive' as part of their url.
    Not nice, but the mwclinet APi does not
    provide a build-in solution for revision management.
    """
    return [i for i in img_list if 'archive' not in i.imageinfo['url']]


def fetch_wiki_page(site, page, out=None):
    """
    Arguments:
    - site : mwclient site object
    - page : either mwclient page object or pagename as string
    """
    if isinstance(page, basestring) or isinstance(page, str):
        # if we get a pagename: fetch the page object
        page = site.Pages[page]
    if not page.exists:
        raise Exception("Page not found: %s" % page.name)
    out = "out" if out is None else out
    ensure_dir(out)

    print "Fetching page: %s" % page.name
    # fetch page content as markdown
    pagefile = re.sub(' ', '_', page.name)
    with open("%s%s.md" % (out, pagefile), 'w') as f:
        f.write(page.text().encode('utf8'))
    print "Stored page content in %s.md" % page.name

    # fetch all images used in page
    # TODO: Filter? This will download all linked files (e.g. PDFs)
    print "Fetching page's images"
    download_ps = []
    for img in no_archived_elements(page.images()):
        p = subprocess.Popen(
            ["wget", "-xNq",
             "-O%s%s" % (out, img.name.replace("File:", "")),
             img.imageinfo['url']
             ])
        download_ps.append(p)
        print "Downloading: %s" % img.name
    print "Waiting for all downloads to finish..."
    ecodes = [p.wait() for p in download_ps]
    if 1 in ecodes:
        print "*** WARNING: File download failed. ***"


def fetch_wiki_category(site, catname, out=None):
    """
    Fetches all pages contained in the given
    category.
    """
    print "Fetching category: %s" % catname
    # if output folder not given, use catname
    out = ("%s/" % catname) if out is None else out
    # fetch all pages found in category
    for page in site.Categories[catname]:
        fetch_wiki_page(site, page, out)


def ensure_dir(directory):
    """
    Creates directory if it does not exist.
    """
    if not os.path.exists(directory):
        os.makedirs(directory)


def download(target,
             output="out/", category=None, **kwargs):
    global SITE
    if SITE is None:
        raise Exception("Wiki connection was not initialized.")
    if not output[-1] == '/':
        output += '/'
    if category:
        fetch_wiki_category(SITE, target, output)
    else:
        fetch_wiki_page(SITE, target, output)


def upload_document(doc, excp):
    """upload both build progress information
    as well as a potneitally generated PDF """
    global SITE

    # deal with any possible exceptions
    if SITE is None:
        raise Exception("Wiki connection was not initialized.")

    # deal with the PDF file:
    texdir = os.path.join(doc, 'tex')
    pdffile = os.path.join(texdir,
                           'main.pdf')

    if os.path.isfile(pdffile):
        uploadedName = doc + ".pdf"
        print "pdf exists, uploding ", pdffile, " as ", uploadedName
        res = SITE.upload(open(pdffile),
                          uploadedName,
                          "Generated file for document " + doc,
                          ignore=True)
        pp(res)
    else:
        print "no pdf to upload"

    # any tar file to upload?
    tarfile = os.path.join(doc, doc+'-latex.tgz')
    if os.path.isfile(tarfile):
        uploadName = doc+'-latex.tgz'
        print "tar file exsists, upload: ", tarfile, uploadName
        res = SITE.upload(open(tarfile),
                          uploadName,
                          "Generated intermediate files (figures, uml, latex) for " + doc,
                          ignore=True)
        pp(res)
    else:
        print "no tar file to upload"
    
    # prepare the build report page
    page = SITE.Pages[doc + 'BuildReport']
    text = page.text()
    text = "= Build report for {} =\n".format(doc)

    text += "\n== PDF file ==\n"
    text += "\n[[File:" + doc + ".pdf]]\n"
    
    # deal with the exceptions: 
    if excp:
        text += "== Return code ==\n"
        try: 
            # 
    	    text += str(excp.returncode)
        except:
            # 
            text += "(no returncode found)"
            
        text += "\n== Output ==\n"
        text += "\n<nowiki>\n"
        try:
            # 
            text += excp.output
        except:
            # 
            text += "(no error output exists)"
            
        text += "\n</nowiki>\n"
    else:
        text += "\n== No errors reported! ==\n"
    # done 


    text += "\n[[Category:BuildReport]]\n"

    page.save(text)


def setup_cli_parser():
    """
    CLI definition
    """
    parser = argparse.ArgumentParser(
        description="Download MediaWiki pages/ categories and all linked content.")
    parser.add_argument("--host", dest="host", default="wiki.sonata-nfv.eu",
                        help="Host of Wiki to fetch from")
    parser.add_argument("--user", dest="user", default=None,
                        help="Username for Wiki")
    parser.add_argument("--pass", dest="password", default=None,
                        help="Password for Wiki")
    parser.add_argument("-c", dest="category", action='store_true',
                        help="Fetch entire category instead of single page")
    parser.add_argument("--out", dest="output", default="out/",
                        help="Output directory (default is 'out' or name of category)")
    parser.add_argument("target",
                        help="Page name or category name to fetch")
    return parser

if __name__ == '__main__':
    parser = setup_cli_parser()
    args = parser.parse_args()
    setup_connection(host=args.host, user=args.user, password=args.password)
    download(**vars(args))
