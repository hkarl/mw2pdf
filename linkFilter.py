#!/usr/bin/python

#original (does not work on Linux or default OSX):
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

            if ("talk:" in link.lower()) and (kind == "wikilink"):
                # deal with talk extension
                # sys.stderr.write('unknown: {}\n'.format([u['c'] for u in unknown]))

                textlist = [u['c'] if u['c'] else ' ' for u in unknown]
                # sys.stderr.write('unknown: {}\n'.format(textlist))

                textlist = ''.join(textlist)
                # sys.stderr.write('unknown: {}\n'.format(textlist))

                try:
                    return RawInline('latex', textlist)
                except:
                    return RawInline('latex', '??')
                    
            
            if kind == "wikilink":
                if "#" in link:
                    link = link.split('#')[1]

                sys.stderr.write("link: {}\n---\n\n".format(link))
                link = '_'.join([x.lower() for x in link.split('_')])
                return RawInline('latex', "\\autoref{{{}}}".format(link))


if __name__ == "__main__":
    toJSONFilter(linkhandler)
