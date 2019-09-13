import functools
import globals
import json
import logging
import re

from commons.entity.linking.models.text import EntityMention, Entity
from copy import deepcopy

logger = logging.getLogger()


class Linker(object):
    def __init__(self):
        self.entity_warehouse = globals.entity_warehouse_server

    def strip_mention(self, text):
        RE_STRIP = r' \([^)]*\)|\<[^)]*\>|,|"|\.|\'|:|-|@|#|…'
        text = text.replace('\t', ' ').replace('\n', ' ').replace('\r', ' ')
        text = text.lower().strip()
        text = text.replace('\\', '')
        text = ' '.join(text.split())
        text = ' '.join(re.sub(RE_STRIP, '', text).strip().split())
        return text

    @functools.lru_cache(maxsize=None)
    def linking(self, text):
        em = EntityMention(text)
        self.add_candidate_entities(em)
        self.add_features(em, feats=['salience'])
        self.rank_candidate_entities(em)
        return em

    @functools.lru_cache(maxsize=None)
    def get_candidate_entities(self, mentions, n):
        res = []
        merged = {}
        for mention in mentions:
            query = {'mention': mention.lower()}
            response = self.entity_warehouse.get_response_by_query(json.dumps(query))
            if not response:
                query = {'mention': self.strip_mention(mention)}
                response = self.entity_warehouse.get_response_by_query(json.dumps(query))
            if response:
                for kbid, score in response['entities'][:n+1]:
                    if kbid not in merged:
                        ce = Entity(kbid, etype=None, name=kbid)
                        ce.features = {'commonness': score}
                        merged[kbid] = ce
                    else:
                        merged[kbid].features['commonness'] += score
        tol = sum([merged[kbid].features['commonness'] for kbid in merged])
        for kbid in merged:
            merged[kbid].features['commonness'] /= tol
            res.append(merged[kbid])
        return res

    def add_candidate_entities(self, entitymention, n=10):
        em = entitymention
        em.candidates = self.get_candidate_entities(tuple([em.text]), n)
        em.candidates = deepcopy(em.candidates)

    # ========== features ==========
    def add_salience(self, entitymention, etype=None):
        em = entitymention
        for ce in em.candidates:
            ce.features['SALIENCE'] = ce.features['commonness']

    # def add_context_similarity(entitymention, softmax=False):
    #     # from scipy.spatial.distance import cosine
    #     em = entitymention
    #     context = tuple(sorted(set(em.context)-set(em.toked_text)))
    #     em.vectors['context'] = vector.get_text_vector(context) if context else None
    #     for ce in em.candidates:
    #         ce.vectors['entity'] = vector.get_entity_vector(kbid)
    #         if em.vectors['context'] is not None and \
    #            ce.vectors['entity'] is not None:
    #             cs = max(1-cosine(em.vectors['context'], ce.vectors['entity']), 0)
    #             ce.features['CONTEXT_SIMILARITY'] = cs
    #         else:
    #             ce.features['CONTEXT_SIMILARITY'] = 0
    #     if softmax:
    #         feature_softmax(em, 'CONTEXT_SIMILARITY')

    def feature_softmax(self, entitymention, feat, normalize=None):
        em = entitymention
        if normalize == 'reciprocal':
            for ce in em.candidates:
                if ce.features[feat]:
                    ce.features[feat] = 1 / ce.features[feat]
        tol = sum([ce.features[feat] for ce in em.candidates])
        if tol:
            for ce in em.candidates:
                ce.features[feat] /= tol

    def add_features(self, entitymention, feats=['salience']):
        em = entitymention
        if 'salience' in feats:
            self.add_salience(em)
        if 'context_similarity' in feats:
            self.add_context_similarity(em)

    # ========== ranking ==========
    def rank_candidate_entities(self, entitymention, rankings={'SALIENCE': 1.0},
                                underline=True, softmax=True):
        em = entitymention
        for ce in em.candidates:
            for r in rankings:
                w = rankings[r]
                ce.confidence += ce.features[r] * w

        if softmax:
            tol = sum([ce.confidence for ce in em.candidates])
            if tol:
                for ce in em.candidates:
                    ce.confidence /= tol

        if underline:
            for ce in em.candidates:
                ce.kbid = ce.kbid.replace(' ', '_')

        em.candidates = sorted(em.candidates,
                               key=lambda x: x.confidence,
                               reverse=True)
        if em.candidates:
            em.entity = deepcopy(em.candidates[0])
