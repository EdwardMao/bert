import globals
import logging

from commons.nlu.classifier.classifier import BaseClassifier
from commons.utils import confirm_negation
from commons.utils.items import ScoredItem
from collections import defaultdict


class IntentClassifier(BaseClassifier):

    def __init__(self, intent_classifier_configure):
        super().__init__()

        self.system_logger = logging.getLogger("system_log")
        self.dialog_graph = globals.dialog_graph
        self.bm25_sentence_similarity_server = globals.bm25_sentence_similarity_server

        self.threadhold = intent_classifier_configure.threadhold
        self.intent_knn = intent_classifier_configure.intent_knn
        self.intent_to_processed_sample_queries = {}
        self.raw_sample_queries_to_intent = {}
        self._initialize()

    def classify(self, user_query):

        ranked_sample_queries = defaultdict()
        for intent_id, intent_obj in self.dialog_graph.intent_dict.items():
            for sample_query in self.intent_to_processed_sample_queries[intent_id]:
                if sample_query.normalized_text == user_query.normalized_text:
                    # exact match
                    return_item = ScoredItem(intent_id, sample_query.normalized_text, 100.0)
                    return [], return_item, [return_item.to_json()]

                score, _, _ = self.bm25_sentence_similarity_server.get_similarity(user_query, sample_query)
                ranked_sample_queries[sample_query.raw_query] = score

        ranked_intents = []
        ranked_samples = sorted(ranked_sample_queries.items(), key=lambda x: x[1], reverse=True)
        for sample, score in ranked_samples:
            intent_id = self.raw_sample_queries_to_intent[sample]
            ranked_intents.append(ScoredItem(intent_id, sample, score))

        decision, decision_log = self._intent_knn_decision(ranked_intents, user_query)
        return ranked_intents, decision, decision_log

    def _initialize(self):

        for intent_id, intent_obj in self.dialog_graph.intent_dict.items():
            # handle raw queries to make raw_queries_to_intent dictionary
            for raw_query in intent_obj.sample_queries:
                if raw_query in self.raw_sample_queries_to_intent:
                        log_str = "Sample query [%s] has been assigned to topic [%s]. "\
                                  "Currently it also belongs to [%s]" % \
                                  (raw_query, self.raw_sample_queries_to_intent[raw_query], intent_id)
                        self.system_logger.info(log_str)
                        print(log_str)
                        continue
                self.raw_sample_queries_to_intent[raw_query] = intent_id

            # then handle processed queries
            self.intent_to_processed_sample_queries[intent_id] = intent_obj.processed_sample_queries

    def _intent_knn_decision(self, ranked_intents, user_query):

        decision_log = []

        if ranked_intents[0].item_score == 100.0:
            decision_log.append(ScoredItem(ranked_intents[0].item_id,
                                           ranked_intents[0].item_type,
                                           ranked_intents[0].item_score))
            return decision_log[0], [item.to_json() for item in decision_log]

        intent_score_list = defaultdict(list)
        for index, score_item in enumerate(ranked_intents):
            if index >= self.intent_knn:
                break
            intent_score_list[score_item.item_id].append(score_item.item_score)

        intent_sorted_by_trigger_queries = sorted(intent_score_list.items(), key=lambda x: len(x[1]), reverse=True)
        trigger_intent_candidate, trigger_intent_query_list = intent_sorted_by_trigger_queries[0]

        if len(trigger_intent_query_list) <= 1:
            decision_log.append(ScoredItem(trigger_intent_candidate,
                                           ranked_intents[0].item_type,
                                           ranked_intents[0].item_score))
            return None, [item.to_json() for item in decision_log]

        decision_ranking = {}
        for intent_candidate, query_list in intent_sorted_by_trigger_queries:
            if len(query_list) == 1:
                break
            decision_ranking[intent_candidate] = sum(query_list) / len(query_list)

        sorted_decision_ranking = sorted(decision_ranking.items(), key=lambda x: x[1], reverse=True)
        for intent_candidate, final_score in sorted_decision_ranking:
            decision_log.append(ScoredItem(intent_candidate,
                                           ranked_intents[0].item_type,
                                           final_score))

        index = 0
        for intent_id, rank_score in sorted_decision_ranking:
            if rank_score < self.threadhold:
                break

            if confirm_negation(intent_id, user_query.raw_query):
                return decision_log[index], [item.to_json() for item in decision_log]

            index += 1

        return None, [item.to_json() for item in decision_log]
