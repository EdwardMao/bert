import re


def noun_phrase_generator(token_list):
    np_labels = [
        'n', # general noun	苹果
        'nh', # person name	杜甫, 汤姆
        'ni', # organization name	保险公司
        'nl', # location noun	城郊
        'ns', # geographical name	北京
        'nz', # other proper noun	诺贝尔奖
        'ws', # foreign words	CPU
        'j',  # abbreviation	公检法
    ]
    seen = set()
    for i in range(0, len(token_list)):
        tok = token_list[i]
        if tok.pos not in np_labels:
            continue
        if i in seen:
            continue
        boundary = []
        for j in range(i, len(token_list)):
            if tok.pos == token_list[j].pos:
                boundary.append(j)
            elif tok.pos == 'ws' and token_list[j].pos in np_labels: # e.g., c罗
                boundary.append(j)
            else:
                break
        if any(x in seen for x in boundary):
            continue
        seen.update(boundary)
        yield [token_list[x] for x in boundary]


def _rule_guillemet(text):
    forcible_offsets = []
    guillemets = re.finditer('《(.*?)》', text)
    for i in guillemets:
        forcible_offsets.append((i.start()+1, i.end()-1))
    return forcible_offsets


def _rule_white_list(text, lexicon=None, trie_tree=None):
    forcible_offsets = []
    char_text = list(text)
    pos = 0
    for i, ch in enumerate(char_text):
        if i < pos:
            continue
        pos = i
        if ch in trie_tree:
            tree = trie_tree[ch]
            mention = [ch]
            for j, next_ch in enumerate(char_text[i+1:]):
                if next_ch in tree:
                    tree = tree[next_ch]
                    mention.append(next_ch)
                else:
                    break
            mention = ''.join(mention)
            if mention in lexicon:
                forcible_offsets.append((i, i+len(mention)))
                pos = i + len(mention)
    return forcible_offsets


def adjust_offsets(offset, offsets_table, text):
    for i in range(offset[0], offset[1]):
        for j in range(offsets_table[i][0], i):
            offsets_table[j] = (offsets_table[i][0], i)
        for j in range(i, offsets_table[i][1]):
            offsets_table[j] = (i+1, offsets_table[i][1])
        offsets_table[i] = offset


def segmentor_plus(tokens, rules=['guillemet', 'white_list'],
                   lexicon=None, trie_tree=None):
    offsets = []
    offsets_table = {}
    text = ''.join(tokens)
    pos = 0
    for tok in tokens:
        beg = text.index(tok, pos)
        end = beg + len(tok)
        offsets.append((beg, end))
        for i in range(beg, end):
            offsets_table[i] = (beg, end)
        pos = end

    if 'guillemet' in rules:
        forcible_offsets = _rule_guillemet(text)
        for i in forcible_offsets:
            adjust_offsets(i, offsets_table, text)

    if 'white_list' in rules and lexicon and trie_tree:
        forcible_offsets = _rule_white_list(text,
                                            lexicon=lexicon,
                                            trie_tree=trie_tree)
        for i in forcible_offsets:
            adjust_offsets(i, offsets_table, text)

    offsets = list(sorted(set([offsets_table[i] for i in offsets_table]),
                          key=lambda x: x[0]))
    return [''.join(list(text)[i[0]:i[1]]) for i in offsets]
