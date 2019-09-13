class EntityMention(object):
    '''
    Entity Mention Class
    '''

    def __init__(self, text, beg=0, end=0, toked_text=None, docid=None,
                 context=None, vectors=None, etype=None, mtype='NAM',
                 entity=None, entity_gold=None,
                 candidates=None, translations=None,
                 coref_mention=None, nominal_mentions=None):
        self.text = text
        self.beg = int(beg)
        self.end = int(end)
        self.toked_text = toked_text or []
        self.docid = docid
        self.context = context or []
        self.vectors = vectors or {}
        self.etype = etype
        self.mtype = mtype
        self.entity = entity
        self.entity_gold = entity_gold
        self.candidates = candidates or []
        self.translations = translations or []
        self.coref_mention = coref_mention
        self.nominal_mentions = nominal_mentions or []

    def __str__(self):
        res = ''
        res += '%s\n' % (self.context)
        res += 'M: %s\n' % (self.text)
        if self.translations:
            res += 'T: %s\n' % self.translations
        if self.nominal_mentions:
            res += 'N: %s\n' % ([i.text for i in self.nominal_mentions])
        res += '%s\n' % (self.etype)
        if self.entity_gold:
            res += 'G: %s\n' % (self.entity_gold.kbid)
        if self.entity:
            res += 'E: %s\n' % (self.entity.kbid)
        for c in self.candidates:
            res += '%s\n'  % str(c)
        return res

    def to_tac_tab_format(self, add_trans=False, add_name=False,
                          kbid_format=None):
        mention = self.text.replace('\t', ' ') \
                           .replace('\n', ' ') \
                           .replace('\r', ' ')
        offset = '%s:%s-%s' % (self.docid, self.beg, self.end)
        etype = str(self.etype)
        mtype = self.mtype
        if mtype in ['NOM', 'PRO']:
            entity = self.coref_mention.entity
        else:
            entity = self.entity
        if not entity:
            kbid = 'NIL'
            conf = '1.0'
        else:
            if kbid_format in entity._kbids:
                kbid = str(entity._kbids[kbid_format])
            else:
                kbid = entity.kbid
            conf = '{0:.3f}'.format(entity.confidence)
        res = [mention, offset, kbid, etype, mtype, conf]
        if add_name:
            res[2] = '%s|%s' % (res[2], str(entity.name))
        if add_trans:
            trans = '|'.join(self.translations)
            res.append(trans)
        return res

    def to_json(self):
        res = {}
        res['entity_mention'] = self.text
        res['beg'] = self.beg
        res['end'] = self.end
        res['entity'] = self.entity.to_json() if self.entity else None
        res['candidate_entities'] = [i.to_json() for i in self.candidates if i]
        return res


class Entity(object):
    '''
    Entity Class
    '''

    def __init__(self, kbid, name=None, etype=None, etypes=None,
                 vectors=None, features=None, misc=None):
        self.kbid = kbid
        self._kbids = {}
        self.name = name
        self.etype = etype
        self.etypes = etypes or []
        self.vectors = vectors or {}
        self.features = features or {}
        self.confidence = 1.0
        self.misc = misc or {}

    def __str__(self):
        res = '%s %s %s %s\n%s' % (self.kbid, self.etype, self.name,
                                   self.confidence, self.features)
        return res

    def to_json(self):
        res = {}
        res['kbid'] = self.kbid
        res['confidence'] = self.confidence
        return res
