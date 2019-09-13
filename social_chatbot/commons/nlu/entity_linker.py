import globals
import logging

from commons.entity.linking.linker import Linker
from commons.entity.linking.models.text import EntityMention


logger = logging.getLogger()


class EntityLinker(object):
    def __init__(self):
        self.linker = Linker()
        self.entity_warehouse = globals.entity_warehouse_server

    def linking(self, sentence_index, sentence_list, topic=None):

        sentence = sentence_list[sentence_index]
        entity_mentions = []
        for chunk in sentence.np_chunks:
            words = [c.word for c in chunk]
            em = EntityMention(''.join(words),
                               beg=chunk[0].pos_start,
                               end=chunk[-1].pos_end,
                               toked_text=words,
                               docid=None,
                               context=[i.word for i in sentence.token_list],
                               mtype='NP')
            entity_mentions.append(em)

            if len(chunk) > 1:
                for c in chunk:
                    em = EntityMention(c.word,
                                       beg=c.pos_start,
                                       end=c.pos_end,
                                       toked_text=words,
                                       docid=None,
                                       context=[i.word for i in sentence.token_list],
                                       mtype='NP')
                    entity_mentions.append(em)

        for em in entity_mentions:
            self.linker.add_candidate_entities(em)
            for ce in em.candidates:
                ce._kbids['Tencent_KG'] = ce.kbid
            self.linker.add_features(em, feats=['salience'])
            self.linker.rank_candidate_entities(em)

        # TODO: one big todo futher --- classify 体育明星 to 足球明星，篮球明星，其他
        self.run_post_processing(entity_mentions)
        return entity_mentions

    def run_post_processing(self, entitymentions, rules=['no_guillemet']):
        for em in entitymentions:
            if not em.entity:
                continue
            kg = self.entity_warehouse.get_entry_by_kbid(em.entity.kbid)

            # RULE no_guillemet:
            # If the type of a linked entity is
            # 39: '歌曲', 204: '电影', 205: '电视剧'
            # and the previous character is not '《', remvoe this entity
            if 'no_guillemet' in rules:
                types = set([x[0] for x in kg['types']])
                if types.intersection(set([39, 204, 205])):
                    context = ''.join(em.context)
                    beg = context.index(em.text)
                    if context[max(beg-1, 0)] != '《':
                        em.entity = None
