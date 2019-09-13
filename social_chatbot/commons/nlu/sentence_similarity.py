import codecs
import logging
import math
import re

from collections import defaultdict
from commons.utils import l2_norm


class BM25SentenceSimilarity(object):

    def __init__(self, bm25_sentence_similarity_configure):

        self.system_logger = logging.getLogger("system_log")

        self.idf_dict = bm25_sentence_similarity_configure.idf_dict
        self.bm25_avg_len = bm25_sentence_similarity_configure.bm25_avg_len
        self.bm25_b = bm25_sentence_similarity_configure.bm25_b
        self.bm25_k1 = bm25_sentence_similarity_configure.bm25_k1

        self.character = re.compile("([\u4E00-\u9FD5a-zA-Z]+)", re.U)
        self.number = re.compile("([0-9]+)", re.U)

    def get_similarity(self, query_a, query_b):

        def get_idf_vector(q):
            vector = {}
            for sentence in q.sentence_list:
                for token in sentence.normalized_tokens:
                    if token in self.idf_dict:
                        vector[token] = self.idf_dict[token]
                    else:
                        vector[token] = self.idf_dict["<UNKNOWN>"]
            return vector

        def get_tf_vector(q):
            vector = defaultdict(int)
            q_length = 0
            for sentence in q.sentence_list:
                for token in sentence.normalized_tokens:
                    vector[token] += 1
                    q_length += 1
            return vector, q_length

        def cal(qv, dv, k1, k):

            score = 0
            for item in qv:
                if item in dv:
                    score += qv[item] * (1 + k1) * dv[item] / (k + dv[item])
            return score

        a_vector = get_idf_vector(query_a)
        if len(a_vector) == 0:
            return 0.0, {}, {}
        b_vector, doc_length = get_tf_vector(query_b)

        a_l2_norm = l2_norm(a_vector)

        bm25k = self.bm25_k1 * (1 - self.bm25_b + self.bm25_b * doc_length / self.bm25_avg_len)
        sim_score = cal(a_vector, b_vector, self.bm25_k1, bm25k) / a_l2_norm

        return sim_score, a_vector, b_vector


