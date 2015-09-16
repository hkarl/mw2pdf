#!/Library/Frameworks/Python.framework/Versions/2.7/bin/python


"""
Pandoc filter to convert links from mediawiki in a more
useful format.
"""
import sys
from pandocfilters import toJSONFilter, Link, Str, RawInline


def linkhandler(key, value, frmt, meta):
    if key == 'Link':
        sys.stderr.write(
            'Key: {} Type of Key: {} \nValue: {}\nfrmt: {} \nmeta: {}\n-------\n'
            .format(
                key, type(key),
                value, frmt, meta))

        if frmt == 'latex':
            [unknown, [link, kind]] = value

            if kind == "wikilink":
                if "#" in link:
                    link = link.split('#')[1]
                    
                link = '-'.join([x.lower() for x in link.split(' ')])
                return RawInline('latex', "\\ref{{{}}}".format(link))


if __name__ == "__main__":
    toJSONFilter(linkhandler)
