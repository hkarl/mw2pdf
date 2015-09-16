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
import subprocess
import mwclient  # pip install mwclient


def setup_connection(host, user=None, password=None):
    """
    Setup mwclient connection to wiki
    """
    site = mwclient.Site(host, path='/')
    if user is not None:
        site.login(user, password)
    return site


def fetch_wiki_page(site, page, out=None):
    """
    Arguments:
    - site : mwclient site object
    - page : either mwclient page object or pagename as string
    """
    if isinstance(page, basestring) or isinstance(page, str):
        # if we get a pagename: fetch the page object
        page = site.Pages[page]
    out = "out" if out is None else out
    ensure_dir(out)

    print "Fetching page: %s" % page.name
    # fetch page content as markdown
    with open("%s%s.md" % (out, page.name), 'w') as f:
        f.write(page.text().encode('utf8'))
    print "Stored page content in %s.md" % page.name

    # fetch all images used in page
    # TODO: Filter? This will download all linked files (e.g. PDFs)
    print "Fetching page's images"
    for img in page.images():
        subprocess.call(
            ["wget", "-xNq",
             "-O%s%s" % (out, img.name.replace("File:", "")),
             img.imageinfo['url']
             ])
        print "Downloaded: %s" % img.name


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


def download(host, target,
             user=None, password=None,
             output="out/", category=None):

    if not output[-1] == '/':
        output += '/'
        
    site = setup_connection(host, user, password)
    if category:
        fetch_wiki_category(site, target, output)
    else:
        fetch_wiki_page(site, target, output)


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
    parser.add_argument("--out", dest="output", default=None,
                        help="Output directory (default is 'out' or name of category)")
    parser.add_argument("target",
                        help="Page name or category name to fetch")
    return parser

if __name__ == '__main__':
    parser = setup_cli_parser()
    download(**vars(parser.parse_args()))
