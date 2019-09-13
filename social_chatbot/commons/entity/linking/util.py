import re
import ujson as json
import logging

from .models.text import EntityMention, Entity


logger = logging.getLogger()


def read_tac_bio_format(data, kbid_idx=None, mtype='NAM'):
    res = []
    data = re.split('\n\s*\n', data)
    for d in data:
        sent_mentions = []
        sent_context = []
        sent = d.split('\n')
        curr_mention = []
        for i, line in enumerate(sent):
            if not line:
                continue

            ann = line.split()
            assert len(ann) >= 3
            tok = ann[0]
            offset = ann[1]
            if ann[-1] == 'O':
                tag, etype = ('O', None)
            else:
                tag, etype = ann[-1].split('-')
            if kbid_idx:
                kbid = ann[kbid_idx]
            else:
                kbid = None

            if tag == 'O':
                if curr_mention:
                    sent_mentions.append(curr_mention)
                    curr_mention = []
            elif tag ==  'B':
                if curr_mention:
                    sent_mentions.append(curr_mention)
                curr_mention = [(tok, offset, etype, kbid)]
            elif tag == 'I':
                try:
                    assert curr_mention != []
                except AssertionError:
                    msg = 'No B-tag: %s, skip this tag' % line
                    logger.warning(msg)
                curr_mention.append((tok, offset, etype, kbid))
            if i == len(sent) - 1 and curr_mention:
                sent_mentions.append(curr_mention)

            sent_context.append(tok)

        for i, mention in enumerate(sent_mentions):
            mention_text = ''
            mention_text_tok = []
            mention_etype = None
            mention_kbid = None
            mention_beg_char = 0
            mention_end_char = 0
            mention_docid = None
            for j, (text, offset, etype, kbid) in enumerate(mention):
                m = re.match('(.+):(\d+)-(\d+)', offset)
                docid = m.group(1)
                tok_beg_char = int(m.group(2))
                tok_end_char = int(m.group(3))
                if j == 0:
                    mention_text += text
                    mention_text_tok.append(text)
                    mention_beg_char = int(tok_beg_char)
                else:
                    space = ' ' * (int(tok_beg_char)-int(mention_end_char)-1)
                    mention_text += space + text
                    mention_text_tok.append(text)
                mention_end_char = int(tok_end_char)
                if mention_etype:
                    try:
                        assert mention_etype == etype
                    except AssertionError:
                        msg = 'Unconsistent entity type: %s %s %s, ' \
                              'using the latest one' % (text, offset, etype)
                        logger.warning(msg)
                mention_etype = etype
                if mention_kbid:
                    try:
                        assert mention_kbid == kbid
                    except AssertionError:
                        msg = 'Unconsistent kbid: %s %s %s, ' \
                              'using the latest one' % (text, offset, kbid)
                        logger.warning(msg)
                mention_kbid = kbid
                if mention_kbid:
                    entity_gold = Entity(mention_kbid)
                else:
                    entity_gold = None
                if mention_docid:
                    assert mention_docid == docid
                mention_docid = docid
            assert len(mention_text) == (mention_end_char -
                                         mention_beg_char) + 1

            res.append(EntityMention(mention_text,
                                     beg=mention_beg_char,
                                     end=mention_end_char,
                                     toked_text=mention_text_tok,
                                     docid=mention_docid,
                                     context=sent_context,
                                     etype=mention_etype,
                                     mtype=mtype,
                                     entity_gold=entity_gold))
    return res


def read_tac_tab_format(data, trans_idx=None):
    res = []
    data = data.split('\n')
    for line in data:
        if not line:
            continue
        tmp = line.rstrip('\n').split('\t')
        try:
            mention = tmp[2]
            offset = tmp[3]
            docid = re.match('(.+):(\d+)-(\d+)', offset).group(1)
            beg = int(re.match('(.+):(\d+)-(\d+)', offset).group(2))
            end = int(re.match('(.+):(\d+)-(\d+)', offset).group(3))
            kbid = tmp[4]
            etype = tmp[5]
            mtype = tmp[6]
            conf = float(tmp[7])
        except IndexError:
            logger.error(tmp)
            exit()

        if kbid != 'NIL' and kbid != '-1':
            entity_gold = Entity(kbid)
        else:
            entity_gold = None

        if trans_idx and \
           tmp[trans_idx] != 'NULL' and tmp[trans_idx] != '':
            trans = tmp[trans_idx].strip().split('|')
        else:
            trans = None

        res.append(EntityMention(mention,
                                 beg=beg,
                                 end=end,
                                 docid=docid,
                                 etype=etype,
                                 mtype=mtype,
                                 entity_gold=entity_gold,
                                 translations=trans))

    return res


# ========== output ==========
def get_tac_tab_format(entitymentions, add_trans=False, add_name=False,
                       kbid_format=None):
    res = []
    for em in entitymentions:
        res.append(em.to_tac_tab_format(add_trans=add_trans,
                                        add_name=add_name,
                                        kbid_format=kbid_format))
        for nm in em.nominal_mentions:
            assert nm.mtype in ['NOM', 'PRO']
            res.append(nm.to_tac_tab_format(add_trans=add_trans,
                                            add_name=add_name,
                                            kbid_format=kbid_format))
    return res


def get_tac_tab_format_corpus(corpus, add_trans=False, add_name=False,
                              kbid_format=None):
    res = []
    for docid in sorted(corpus):
        res += get_tac_tab_format(corpus[docid],
                                  add_trans=add_trans,
                                  add_name=add_name,
                                  kbid_format=kbid_format)
    return res


def add_tac_runid_and_mid(tab, runid, mid_prefix):
    count = 0
    for n in range(len(tab)):
        mid_prefix = mid_prefix.replace(' ', '_').upper()
        menid = '{}_MENTION_'.format(mid_prefix) + \
                '{number:0{width}d}'.format(width=7, number=count)
        tab[n] = [runid, menid] + tab[n]
        count += 1


# ========== corenlp ==========
def read_corenlp_json_format(pdata, docid=None, lang='en'):
    if lang == 'en':
        ETYPES = {
            'PERSON': 'PER',
            'ORGANIZATION': 'ORG',
            'LOCATION': 'GPE',
            'MISC': 'MISC'
        }
    elif lang == 'zh':
        ETYPES = {
            'PERSON': 'PER',
            'ORGANIZATION': 'ORG',
            'LOCATION': 'LOC',
            'FACILITY': 'FAC',
            'GPE': 'GPE',
            'MISC': 'MISC'
        }

    res = []
    data = json.load(open(pdata))
    if 'docId' in data:
        docid = data['docId']
    for sent in data['sentences']:
        sent_context = [i['word'] for i in sent['tokens']]
        for em in sent['entitymentions']:
            if em['ner'] not in ETYPES:
                continue
            # TO-DO: add toked_text
            res.append(EntityMention(em['text'],
                                     beg=em['characterOffsetBegin'],
                                     end=em['characterOffsetEnd']-1,
                                     docid=docid,
                                     context=sent_context,
                                     etype=ETYPES[em['ner']]))
    return data, res


def get_entitymention_offset_table(entitymentions):
    res = {}
    for em in entitymentions:
        assert (em.beg, em.end) not in res
        res[(em.beg, em.end)] = em
    return res


def align_corenlp_coref_with_entitymention(coref, em_offset_table, sentences):
    for c in coref:
        sent_num = c['sentNum'] - 1
        tok_beg = c['startIndex'] - 1
        tok_end = c['endIndex'] - 1
        toks = sentences[sent_num]['tokens'][tok_beg:tok_end]
        char_beg = toks[0]['characterOffsetBegin']
        char_end = toks[-1]['characterOffsetEnd'] - 1
        if (char_beg, char_end) in em_offset_table:
            return em_offset_table[(char_beg, char_end)]
    return False


def find_valid_corenlp_coref(coref, em_offset_table, sentences):
    '''
      1. coref should not be entitymention
      2. coref shoudl not overlap with entitymention
    '''

    MTYPES = {
        'PROPER': 'NOM',
        'NOMINAL': 'NOM',
        'PRONOMINAL': 'PRO'
    }
    res = []
    for c in coref:
        sent_num = c['sentNum'] - 1
        tok_beg = c['startIndex'] - 1
        tok_end = c['endIndex'] - 1
        toks = sentences[sent_num]['tokens'][tok_beg:tok_end]
        char_beg = toks[0]['characterOffsetBegin']
        char_end = toks[-1]['characterOffsetEnd'] - 1
        if (char_beg, char_end) in em_offset_table:
            continue
        if any(beg <= char_beg <= end for (beg, end) in em_offset_table.keys()):
            continue
        if c['type'] not in MTYPES:
            continue
        res.append(EntityMention(c['text'],
                                  beg=char_beg, end=char_end,
                                  mtype=MTYPES[c['type']]))
    return res


def add_corenlp_nominal_mentions(entitymentions, corenlp_res):
    count = {
        'entitymention': 0,
        'nominalmention': 0
    }
    em_offset_table = get_entitymention_offset_table(entitymentions)
    sentences = corenlp_res['sentences']
    corefs = corenlp_res['corefs'] if 'corefs' in corenlp_res else []
    for i in corefs:
        aligned_em = align_corenlp_coref_with_entitymention(corefs[i],
                                                            em_offset_table,
                                                            sentences)
        if aligned_em:
            nominal_mentions = find_valid_corenlp_coref(corefs[i],
                                                       em_offset_table,
                                                       sentences)
            if nominal_mentions:
                count['entitymention'] += 1

            for nm in nominal_mentions:
                nm.coref_mention = aligned_em
                nm.docid = aligned_em.docid
                nm.etype = aligned_em.etype
                aligned_em.nominal_mentions.append(nm)
                count['nominalmention'] += 1

