import codecs
import copy
import globals
import json
import logging
import math
import random

from collections import defaultdict
from commons.utils import l2_norm, get_date_str
from operator import attrgetter


class SearchResult(object):

    def __init__(self, ranked_sentence, search_query_dict):

        self.ranked_sentence = ranked_sentence
        self.search_query_dict = search_query_dict

    def get_random_sentence_from_topk(self, top_k, exist_sentence_index=set()):

        if len(self.ranked_sentence) == 0:
            return None

        tried_sentence_index = set()
        while True:
            if len(tried_sentence_index) == len(self.ranked_sentence):
                break

            if len(tried_sentence_index) == top_k:
                top_k += top_k

            return_sentence = random.choice(self.ranked_sentence[:min(top_k, len(self.ranked_sentence))])
            if return_sentence.sentence_index in exist_sentence_index:
                tried_sentence_index.add(return_sentence.sentence_index)
                continue

            return return_sentence

        return random.choice(self.ranked_sentence[:min(top_k, len(self.ranked_sentence))])

    def to_json(self):

        json_dict = defaultdict()
        json_dict["ranked_sentences"] = []
        for sentence in self.ranked_sentence:
            json_dict["ranked_sentences"].append(sentence.to_json())

        json_dict["search_query"] = self.search_query_dict

        return json_dict


class SearchSentence(object):

    def __init__(self, one_sentence_index, sentence_info):

        self.sentence_index = one_sentence_index
        self.sentence_length = sentence_info["sentence_length"]
        self.raw_sentence = sentence_info["raw_sentence"]
        self.title = sentence_info["title"]
        self.score = sentence_info["score"]
        self.news_date = sentence_info["news_date"]
        self.docid = sentence_info["docid"]

    def to_json(self):
        return {
            "sentence_index": self.sentence_index,
            "sentence_length": self.sentence_length,
            "raw_sentence": self.raw_sentence,
            "title": self.title,
            "score": self.score,
            "news_date": self.news_date,
            "docid": self.docid
        }


class SentenceSearchConstraint(object):

    def __init__(self,
                 source,
                 category,
                 days_ago,
                 entity_list,
                 topic_category,
                 entity_number,
                 sentence_length_max,
                 sentence_length_min,
                 sentence_position):

        self.source = source
        self.category = category
        self.entity_list = entity_list
        self.topic_category = topic_category
        self.days_ago = int(days_ago)
        self.entity_number = int(entity_number)
        self.sentence_length_max = int(sentence_length_max)
        self.sentence_length_min = int(sentence_length_min)
        self.sentence_position = int(sentence_position)

    def get_search_query(self):

        search_query = {}
        if self.source != "":
            search_query["source"] = self.source

        if self.category != "":
            search_query["category"] = self.category

        if len(self.entity_list) > 0:
            search_query["entity_set"] = {"$in": self.entity_list}

        if len(self.topic_category) > 0:
            search_query["topic_category"] = self.topic_category

        if self.days_ago > 0:
            search_query["news_date"] = {"$gte": int(get_date_str(24 * int(math.fabs(self.days_ago))))}

        if self.entity_number > 0:
            search_query["entity_len"] = {"$gte": self.entity_number}

        if self.sentence_length_max > 0 and self.sentence_length_min > 0:
            search_query["sentence_length"] = {"$lte": self.sentence_length_max, "$gte": self.sentence_length_min}

        if self.sentence_position > 0:
            search_query["sentence_position"] = {"$lte": self.sentence_position}

        if len(search_query) == 0:
            log_str = "Not valid search query! No constraint in search sentences!"
            logging.getLogger("system_log").error(log_str)
            print(log_str)
            return ""

        return json.dumps(search_query)

    def to_json(self):

        return {
            "source": self.source,
            "category": self.category,
            "entity_list": self.entity_list,
            "topic_category": self.topic_category,
            "days_ago": self.days_ago,
            "entity_number": self.entity_number,
            "sentence_length_max": self.sentence_length_max,
            "sentence_length_min": self.sentence_length_min,
            "sentence_position": self.sentence_position
        }


class ShortSentenceSearch(object):

    def __init__(self, search_configure):

        self.system_logger = logging.getLogger("system_log")
        self.search_configure = search_configure

        self.idf_dict = search_configure.idf_dict
        self.token2id = search_configure.token2id
        self.id2token = search_configure.id2token
        self.max_sentence_number = search_configure.max_sentence_number
        self.search_warehouse_server = globals.search_warehouse_server

        return

    def search_sentence(self, user_qury, sentence_search_constraint):

        search_query_str = sentence_search_constraint.get_search_query()
        if search_query_str == "":
            return SearchResult([], search_query_str)

        if sentence_search_constraint.days_ago > 30:
            related_sentences, actual_search_query_dict = self._get_category_related_sentences(search_query_str)
        else:
            related_sentences, actual_search_query_dict = self._get_related_sentences(search_query_str)

        if len(related_sentences) == 0:
            return SearchResult([], actual_search_query_dict)

        tf_vector, idf_vector = self._get_query_vector(user_qury)

        ranked_sentences = []
        for one_sentence_index in related_sentences:
            sentence_info = self._calculate_bm25_score(tf_vector, idf_vector, one_sentence_index)
            if sentence_info is None:
                continue
            ranked_sentences.append(SearchSentence(one_sentence_index, sentence_info))
        ranked_sentences = sorted(ranked_sentences,
                                  key=attrgetter('score', 'news_date', 'sentence_length'),
                                  reverse=True)

        return SearchResult(ranked_sentences, actual_search_query_dict)

    def _get_category_related_sentences(self, sentence_selection_constraint_str):

        sentence_selection_constraint_obj = json.loads(sentence_selection_constraint_str)
        related_sentences = self.search_warehouse_server.request_sentences_by_query_orderby_date(
            json.dumps(sentence_selection_constraint_obj))
        return related_sentences, sentence_selection_constraint_obj

    def _get_related_sentences(self, sentence_selection_constraint_str):

        sentence_selection_constraint_obj = json.loads(sentence_selection_constraint_str)
        previous_list = list()
        today_int = int(get_date_str(0))
        while True:

            related_sentences = \
                self.search_warehouse_server.request_sentences_by_query(json.dumps(sentence_selection_constraint_obj))

            if len(related_sentences) == 0:
                related_sentences = previous_list
                break

            if len(related_sentences) <= self.max_sentence_number:
                break

            if len(related_sentences) == len(previous_list):
                sentence_selection_constraint_obj["entity_len"]["$gte"] += 1

            previous_list = related_sentences

            if sentence_selection_constraint_obj["news_date"]["$gte"] < today_int:
                sentence_selection_constraint_obj["news_date"]["$gte"] += 1

            if sentence_selection_constraint_obj["sentence_position"]["$lte"] > 1:
                sentence_selection_constraint_obj["sentence_position"]["$lte"] -= 1

        if len(related_sentences) == 0 and len(sentence_selection_constraint_obj["entity_set"]["$in"]) <= 1:
            return related_sentences, sentence_selection_constraint_obj

        if len(related_sentences) == 0 and len(sentence_selection_constraint_obj["entity_set"]["$in"]) > 1:
            # we assume the entity element in the entity_set:$in is ranked by popularity
            # so we remove it one by one from the end
            update_sentence_selection_constraint_obj = json.loads(sentence_selection_constraint_str)
            update_sentence_selection_constraint_obj["entity_set"]["$in"] = \
                update_sentence_selection_constraint_obj["entity_set"]["$in"][:-1]
            return self._get_related_sentences(json.dumps(update_sentence_selection_constraint_obj))

        return related_sentences, sentence_selection_constraint_obj

    def _get_query_vector(self, user_query):

        idf_vector = {}
        tf_vector = {}
        query_json = user_query.to_json()
        for key in query_json:
            sentence = query_json[key]
            for token in sentence["分词词性"]:
                elems = token.split("/")
                word = elems[0].strip()
                if len(word) == 0 or word not in self.token2id or elems[-1].strip() == "True":
                    continue
                word_id = self.token2id[word]
                sentence_tf = self.search_warehouse_server.request_token_by_index(word_id)
                if len(sentence_tf) == 0:
                    log_str = "Word [%s] (Id is [%d]) is not found in db!\n" % (word, word_id)
                    self.system_logger.error(log_str)
                    print(log_str.strip())
                    continue

                idf = self.idf_dict[word]
                idf_vector[word] = idf
                tf_vector[word] = sentence_tf

        return tf_vector, idf_vector

    def _calculate_bm25_score(self, tf_vector, idf_vector, one_sentence_index):

        sentence_entry = globals.search_warehouse_server.request_sentence_by_index(one_sentence_index)
        if len(sentence_entry) != 1:
            log_str = "Sentence Index [%s] is not found in db!\n" % one_sentence_index
            self.system_logger.error(log_str)
            print(log_str.strip())
            return None

        sentence_info = {"sentence_length": sentence_entry[0]["sentence_length"],
                         "raw_sentence": sentence_entry[0]["raw_sentence"],
                         "title": sentence_entry[0]["docid"].split("_")[-1],
                         "news_date": sentence_entry[0]["news_date"],
                         "docid": sentence_entry[0]["docid"]}

        if sentence_info is None:
            return None

        if len(tf_vector) == 0 or len(idf_vector) == 0:
            sentence_info["score"] = 0
            return sentence_info

        bm25k = self.search_configure.bm25_k1 * \
                (1 - self.search_configure.bm25_b +
                 self.search_configure.bm25_b * sentence_info["sentence_length"] / self.search_configure.bm25_avg_len)
        normed_idf_vector = l2_norm(idf_vector)

        score = 0
        for word, word_idf in idf_vector.items():
            sentence_tf = tf_vector[word]
            if one_sentence_index not in sentence_tf:
                continue
            word_tf = sentence_tf[one_sentence_index]
            score = score + (word_tf * (1 + self.search_configure.bm25_k1) * word_idf) / (bm25k + word_tf)

        sentence_info["score"] = score / normed_idf_vector
        return sentence_info

