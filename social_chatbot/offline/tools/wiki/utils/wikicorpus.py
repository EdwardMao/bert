'''
Based on:
  https://github.com/RaRe-Technologies/gensim/blob/develop/gensim/corpora/wikicorpus.py
  https://github.com/wikilinks/sift/blob/master/sift/corpora/wikicorpus.py
Credits:
  Radim Rehurek <radimrehurek@seznam.cz>
  Lars Buitinck <larsmans@gmail.com>
  Andy Chisholm <andy.chisholm.89@gmail.com>
'''


import re
from html.entities import name2codepoint


RE_P0 = re.compile(r'<!--.*?-->', re.DOTALL | re.UNICODE)  # comments
RE_P1 = re.compile(r'<ref([> ].*?)(</ref>|/>)', re.DOTALL | re.UNICODE)  # footnotes
RE_P2 = re.compile(r'(\n\[\[[a-z][a-z][\w-]*:[^:\]]+\]\])+$', re.UNICODE)  # links to languages
RE_P3 = re.compile(r'{{([^}{]*)}}', re.DOTALL | re.UNICODE)  # template
RE_P4 = re.compile(r'{{([^}]*)}}', re.DOTALL | re.UNICODE)  # template
RE_P5 = re.compile(r'\[(\w+):\/\/(.*?)(( (.*?))|())\]', re.UNICODE)  # remove URL, keep description
RE_P6 = re.compile(r'\[([^][]*)\|([^][]*)\]', re.DOTALL | re.UNICODE)  # simplify links, keep description
RE_P7 = re.compile(r'\n\[\[[iI]mage(.*?)(\|.*?)*\|(.*?)\]\]', re.UNICODE)  # keep description of images
RE_P8 = re.compile(r'\n\[\[[fF]ile(.*?)(\|.*?)*\|(.*?)\]\]', re.UNICODE)  # keep description of files
RE_P9 = re.compile(r'<nowiki([> ].*?)(</nowiki>|/>)', re.DOTALL | re.UNICODE)  # outside links
RE_P10 = re.compile(r'<math([> ].*?)(</math>|/>)', re.DOTALL | re.UNICODE)  # math content
RE_P11 = re.compile(r'<(.*?)>', re.DOTALL | re.UNICODE)  # all other tags
RE_P12 = re.compile(r'\n(({\|)|(\|-)|(\|}))(.*?)(?=\n)', re.UNICODE)  # table formatting
RE_P13 = re.compile(r'\n(\||\!)(.*?\|)*([^|]*?)', re.UNICODE)  # table cell formatting
RE_P14 = re.compile(r'\[\[Category:[^][]*\]\]', re.UNICODE)  # categories
RE_P15 = re.compile(r'\[\[([fF]ile:|[iI]mage)[^]]*(\]\])', re.UNICODE) # Remove File and Image template

RE_BI = re.compile(r"'''''([^']*?)'''''")
RE_B = re.compile(r"'''(.*?)'''")
RE_IQ = re.compile(r"''\"(.*?)\"''")
RE_I = re.compile(r"''([^']*)''")
RE_QQ = re.compile(r'""(.*?)""')
RE_SECT = re.compile(r'(==+)\s*(.*?)\s*\1')
RE_EMPTY_PARENS = re.compile(r' \(\s*\)')
# RE_EMPTY_PARENS_PLUS = re.compile(r' \([\s,;-]+\)')
RE_EMPTY_PARENS_ZH = re.compile(r'（\s*）')
# RE_EMPTY_PARENS_PLUS_ZH = re.compile(r'（[\s,;-，；：－]+）')

RE_HTML_ENT = re.compile("&#?(\w+);")

RE_P6 = re.compile("\[\[:?([^][]*)\|([^][]*)\]\]", re.DOTALL | re.UNICODE)
RE_P6_ex = re.compile("\[\[:?([^][|]*)\]\]", re.DOTALL | re.UNICODE)

RE_TABLE = re.compile(r'{\|.*?\|}', re.DOTALL | re.UNICODE)


def remove_markup(text, title=None):
    text = re.sub(RE_P2, '', text)  # remove the last list (=languages)
    # the wiki markup is recursive (markup inside markup etc)
    # instead of writing a recursive grammar, here we deal with that by removing
    # markup in a loop, starting with inner-most expressions and working outwards,
    # for as long as something changes.
    text = remove_template(text) # TO-DO: template parser
                                 # TO-DO: {{lang|xx|XXX}}

    # remove table markup
    text = re.sub(RE_TABLE, '', text) # TO-DO: table parser

    # Extract captions for File: and Image: markups, and append to the end of article
    text = extract_tag_content(text, [
        re.compile('\[\[[fF]ile:(.*?)(\|[^\]\[]+?)*\|'),
        re.compile('\[\[[iI]mage:(.*?)(\|[^\]\[]+?)*\|')
    ])

    # Inject links for B and BI in the first paragraph
    if title:
        orig_first_para, first_para = '', ''
        for i in re.sub(RE_P0, '', text).strip().split('\n'):
            if i and not re.match('\[\[.+\]\]$', i):
                orig_first_para, first_para = i, i
                break
        for i in re.finditer(RE_BI, first_para):
            i = i.group(1)
            if '[' in i or ']' in i or i == '':
                continue
            l = '[[%s|%s]]' % (title, i)
            first_para = first_para.replace("'''''%s'''''" % i, l)
        first_para = re.sub("'''''*?", '', first_para)
        for i in re.finditer(RE_B, first_para):
            i = i.group(1)
            if '[' in i or ']' in i or i == '':
                continue
            l = '[[%s|%s]]' % (title, i)
            first_para = first_para.replace("'''%s'''" % i, l)
        text = text.replace(orig_first_para, first_para, 1)

    iters = 0
    while True:
        old, iters = text, iters + 1
        text = re.sub(RE_P0, '', text)  # remove comments
        text = re.sub(RE_P1, '', text)  # remove footnotes
        text = re.sub(RE_P9, '', text)  # remove outside links
        text = re.sub(RE_P10, '', text)  # remove math content
        text = re.sub(RE_P11, '', text)  # remove all remaining tags
        text = re.sub(RE_P14, '', text)  # remove categories
        text = re.sub(RE_P5, '\\3', text)  # remove urls, keep description

        text = re.sub(RE_P6_ex, '[[\\1|\\1]]', text)

        # remove table markup
        text = text.replace('||', '\n|')  # each table cell on a separate line
        text = re.sub(RE_P12, '\n', text)  # remove formatting lines
        text = re.sub(RE_P13, '\n\\3', text)  # leave only cell content

        # remove empty mark-up
        text = text.replace('[]', '')

        # formatting
        text = re.sub(RE_BI, r"\1", text)
        text = re.sub(RE_B, r"\1", text)
        # text = re.sub(RE_IQ, r'&quot;\1&quot;', text)
        # text = re.sub(RE_I, r'&quot;\1&quot;', text)
        # text = re.sub(RE_QQ, r"\1", text)
        text = text.replace("''", '')

        if old == text or iters > 2:  # stop if nothing changed between two iterations or after a fixed number of iterations
            break

    text = re.sub(RE_EMPTY_PARENS, '', text) # remove empty parenthesis (usually left by stripped templates)
    # text = re.sub(RE_EMPTY_PARENS_PLUS, '', text)
    text = re.sub(RE_EMPTY_PARENS_ZH, '', text)
    # text = re.sub(RE_EMPTY_PARENS_PLUS_ZH, '', text)

    text = html_unescape(text.strip())
    return text


def remove_template(s):
    """Remove template wikimedia markup.

    Return a copy of `s` with all the wikimedia markup template removed. See
    http://meta.wikimedia.org/wiki/Help:Template for wikimedia templates
    details.

    Note: Since template can be nested, it is difficult remove them using
    regular expresssions.
    """

    # Find the start and end position of each template by finding the opening
    # '{{' and closing '}}'
    n_open, n_close = 0, 0
    starts, ends = [], []
    in_template = False
    prev_c = None
    for i, c in enumerate(iter(s)):
        if not in_template:
            if c == '{' and c == prev_c:
                starts.append(i - 1)
                in_template = True
                n_open = 1
        if in_template:
            if c == '{':
                n_open += 1
            elif c == '}':
                n_close += 1
            if n_open == n_close:
                ends.append(i)
                in_template = False
                n_open, n_close = 0, 0
        prev_c = c

    # Remove all the templates
    return ''.join([s[end + 1:start] for start, end in zip(starts + [None], [-1] + ends)])


def remove_file(s):
    """Remove the 'File:' and 'Image:' markup, keeping the file caption.

    Return a copy of `s` with all the 'File:' and 'Image:' markup replaced by
    their corresponding captions. See http://www.mediawiki.org/wiki/Help:Images
    for the markup details.
    """
    # The regex RE_P15 match a File: or Image: markup
    for match in re.finditer(RE_P15, s):
        m = match.group(0)
        caption = m[:-2].split('|')[-1]
        s = s.replace(m, caption, 1)
    return s


def extract_tag_content(s, tags, include_content=True):
    s = s.replace(u'\u2502', '|')
    for t in tags:
        parts = []
        matched_parts = []
        last_match_end = None
        for match in t.finditer(s):
            parts.append(slice(last_match_end, match.start()))

            i = match.end()
            while True:
                next_open = s.find('[[', i)
                next_close = s.find(']]', i)
                if next_open == -1 or next_open > next_close:
                    last_match_end = next_close
                    break
                elif next_close == -1:
                    # unbalanced tags in wikimarkup, bail!
                    last_match_end = i
                    break
                i = next_close + 2
            if include_content and match.end() != last_match_end:
                content = s[match.end():last_match_end].strip('] ')
                if content:
                    matched_parts.append(slice(match.end(), last_match_end))
                    if not content.endswith('.'):
                        matched_parts.append('.')
                    matched_parts.append('\n')
            last_match_end += 2
        parts.append(slice(last_match_end, None))
        s = ''.join([s[p] for p in parts] + ['\n'] + \
                    [s[p] if type(p) is slice else p for p in matched_parts])

    return s


def html_unescape(text):
    def replace(m):
        span, code = m.group(0), m.group(1)
        try:
            if span[1] == "#":
                return chr(int(code[1:], 16)) if span[2] == "x" else chr(int(code))
            else:
                return chr(name2codepoint[code])
        except:
            return span
        return span
    return re.sub(RE_HTML_ENT, replace, text)


def normalise_wikilink(s):
    s = s.replace(' ', '_').strip('_').strip()
    s = s.replace('_', ' ')
    if s and s[0].islower():
        s = s[0].upper() + s[1:]
    return s


def extract_links(text): # TO-DO: nested links
    orig_text = text
    links = []
    shift = 0
    for i in re.finditer(RE_P6, text):
        target = normalise_wikilink(i.group(1))
        anchor = i.group(2).strip()
        if not anchor:
            anchor = target
        text = text[:i.start()-shift] + anchor + text[i.end()-shift:]
        beg = i.start() - shift
        shift += len(i.group())-len(anchor)
        if not target:
            continue
        links.append(
            {
                'title': target,
                'text': anchor,
                'offset': (beg, beg+len(anchor)),
            }
        )
    for i in links:
        if text[i['offset'][0]:i['offset'][1]] != i['text']:
            raise Exception('Unmatched link offset')
    return text, links


def extract_cats(text):
    re_cat = '\[\[Category:([^\|\]]+)'
    cats = []
    count = 0
    for i in re.finditer(RE_P14, text):
        try:
            cats.append(re.match(re_cat, i.group()).group(1).strip())
        except AttributeError:
            count += 1
    return cats


def extract_sects(text):
    sects = []
    for i in re.finditer(RE_SECT, text):
        sects.append((i.group(), (i.start(), i.end())))
    return sects
