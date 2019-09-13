import globals
import json
import os

from commons.utils import load_df_file


class OnlineConfigure(object):

    def __init__(self,
                 data_root,
                 nlu_configure,
                 dialog_graph_configure,
                 qa_configure,
                 bm25_configure,
                 short_sentence_search_configure,
                 default_sentence_search_constraint,
                 entity_warehouse_configure,
                 search_warehouse_configure,
                 intent_classifier_configure,
                 entity_extension_configure,
                 topic_category_configure,
                 log_configure
                 ):

        self.data_root = data_root
        globals.data_root = data_root

        # default_sentence_search_constraint
        globals.default_sentence_search_constraint_str = json.dumps(dict(**default_sentence_search_constraint))

        # common and independent configure
        self.bm25_configure = BM25Configure(**bm25_configure)
        self.dialog_graph_configure = DialogGraphConfigure(**dialog_graph_configure)
        self.entity_warehouse_configure = EntityWarehouseConfigure(**entity_warehouse_configure)
        self.intent_classifier_configure = IntentClassifierConfigure(**intent_classifier_configure)
        self.log_configure = LogConfigure(**log_configure)
        self.nlu_configure = NLUConfigure(**nlu_configure)
        self.qa_configure = QAConfigure(**qa_configure)
        self.search_warehouse_configure = SearchWarehouseConfigure(**search_warehouse_configure)
        self.entity_extension_configure = EntityExtensionConfigure(**entity_extension_configure)
        self.topic_category_configure = TopicCategoryConfigure(**topic_category_configure)

        # dependent configure
        short_sentence_search_configure["bm25_configure"] = self.bm25_configure
        self.short_sentence_search_configure = ShortSentenceSearchConfigure(**short_sentence_search_configure)
        self.bm25ss_configure = BM25SentenceSimilarityConfigure(self.bm25_configure)


class TopicCategoryConfigure(object):

    def __init__(self, sports_topic_category_file):

        self.sports_topic_category_file = globals.data_root + sports_topic_category_file


class LogConfigure(object):

    def __init__(self, system_log_dir, component_log_dir, user_log_dir, loggers):

        self.system_log_dir = globals.data_root + "/" + system_log_dir
        self.component_log_dir = globals.data_root + "/" + component_log_dir
        self.user_log_dir = globals.data_root + "/" + user_log_dir
        self.loggers = loggers

        if not os.path.exists(self.system_log_dir):
            os.mkdir(self.system_log_dir)

        if not os.path.exists(self.component_log_dir):
            os.mkdir(self.component_log_dir)

        if not os.path.exists(self.user_log_dir):
            os.mkdir(self.user_log_dir)


class AttitudeClassifierConfigure(object):

    def __init__(self, data_root, confidence):
        self.data_root = globals.data_root + "/" + data_root
        self.confidence = confidence


class DialogActClassifierConfigure(object):

    def __init__(self, data_root, confidence):
        self.data_root = globals.data_root + "/" + data_root
        self.confidence = confidence


class EmotionClassifierConfigure(object):

    def __init__(self, data_root):
        self.data_root = globals.data_root + "/" + data_root


class QuestionClassifierConfigure(object):

    def __init__(self, data_root, surround_num, n_gram):
        self.data_root = globals.data_root + "/" + data_root
        self.surround_num = surround_num
        self.n_gram = n_gram


class NLUConfigure(object):

    def __init__(self,
                 nlp_data_root,
                 attitude_classifier_configure,
                 dialog_act_classifier_configure,
                 emotion_classifier_configure,
                 question_classifier_configure,
                 turn_on,
                 entity_type_mapping_file,
                 entity_type_exclusion_file):

        self.nlp_data_root = globals.data_root + "/" + nlp_data_root + "/"
        self.attitude_classifier_configure = AttitudeClassifierConfigure(**attitude_classifier_configure)
        self.question_classifier_configure = QuestionClassifierConfigure(**question_classifier_configure)
        self.dialog_act_classifier_configure = DialogActClassifierConfigure(**dialog_act_classifier_configure)
        self.emotion_classifier_configure = EmotionClassifierConfigure(**emotion_classifier_configure)
        self.turn_on = turn_on
        self.entity_type_mapping_file = self.nlp_data_root + entity_type_mapping_file
        self.entity_type_exclusion_file = self.nlp_data_root + entity_type_exclusion_file


class DialogGraphConfigure(object):

    def __init__(self,
                 dialog_graph_data_root,
                 intents,
                 groundings,
                 questions):

        self.dialog_graph_data_root = globals.data_root + "/" + dialog_graph_data_root
        self.intent_json_file = self.dialog_graph_data_root + intents
        self.grounding_json_file = self.dialog_graph_data_root + groundings
        self.question_json_file = self.dialog_graph_data_root + questions


class QAConfigure(object):

    def __init__(self, threshold_value, turn_on):

        self.threshold_value = threshold_value
        self.turn_on = bool(turn_on)


class BM25Configure(object):

    def __init__(self, idf_file, b, k1, avg_len, unknown_token_df):

        self.idf_file = globals.data_root + "/" + idf_file
        self.unknown_token_df = unknown_token_df
        self.bm25_b = b
        self.bm25_k1 = k1
        self.bm25_avg_len = avg_len
        self.idf_dict, self.token2id, self.id2token = load_df_file(self.idf_file, unknown_token_df)


class BM25SentenceSimilarityConfigure(object):

    def __init__(self, bm25_configure):

        self.idf_dict = bm25_configure.idf_dict
        self.bm25_b = bm25_configure.bm25_b
        self.bm25_k1 = bm25_configure.bm25_k1
        self.bm25_avg_len = bm25_configure.bm25_avg_len


class ShortSentenceSearchConfigure(object):

    def __init__(self,
                 bm25_configure,
                 max_sentece_number
                 ):

        self.idf_dict = bm25_configure.idf_dict
        self.token2id = bm25_configure.token2id
        self.id2token = bm25_configure.id2token
        self.bm25_b = bm25_configure.bm25_b
        self.bm25_k1 = bm25_configure.bm25_k1
        self.bm25_avg_len = bm25_configure.bm25_avg_len
        self.max_sentence_number = max_sentece_number


class SearchWarehouseConfigure(object):

    def __init__(self,
                 host,
                 port,
                 db_name,
                 user,
                 pwd,
                 sentence_collection_name,
                 index_dir,
                 memcache_ip_port
                 ):
        self.name = "SearchWarehouse"
        self.host = host
        self.port = int(port)
        self.db_name = db_name
        self.user = user
        self.pwd = pwd
        self.sentence_collection_name = sentence_collection_name
        self.index_dir = globals.data_root + "/" + index_dir + "/"
        self.memcache_ip_port = memcache_ip_port


class EntityWarehouseConfigure(object):

    def __init__(self,
                 host,
                 port,
                 db_name,
                 user,
                 pwd,
                 entity_collection_name,
                 entity_mentions_name,
                 memcache_ip_port
                 ):
        self.name = "EntityWarehouse"
        self.host = host
        self.port = int(port)
        self.db_name = db_name
        self.user = user
        self.pwd = pwd
        self.entity_collection_name = entity_collection_name
        self.entity_mentions_name = entity_mentions_name
        self.memcache_ip_port = memcache_ip_port


class IntentClassifierConfigure(object):

    def __init__(self, threadhold, intent_knn):

        self.threadhold = threadhold
        self.intent_knn = intent_knn


class EntityExtensionConfigure(object):

    def __init__(self,
                 local_data_root,
                 obj_placeholder,
                 sub_placeholder,
                 obj_a_placeholder,
                 obj_b_placeholder,
                 ana_sub_placeholder,
                 ana_obj_placeholder,
                 templates,
                 relations,
                 templates_2a,
                 relations_2a,
                 templates_analogy,
                 pred_synonym,
                 pred_mapping,
                 focus_type_list,
                 alias_top_k,
                 candidate_top_k):

        self.local_data_root = globals.data_root + "/" + local_data_root
        self.obj_placeholder = obj_placeholder
        self.sub_placeholder = sub_placeholder
        self.obj_a_placeholder = obj_a_placeholder
        self.obj_b_placeholder = obj_b_placeholder
        self.ana_sub_placeholder = ana_sub_placeholder
        self.ana_obj_placeholder = ana_obj_placeholder
        self.templates_json_file = self.local_data_root + templates
        self.relations_json_file = self.local_data_root + relations
        self.templates_2a_json_file = self.local_data_root + templates_2a
        self.relations_2a_json_file = self.local_data_root + relations_2a
        self.templates_analogy_json_file = self.local_data_root + templates_analogy
        self.pred_synonym_json_file = self.local_data_root + pred_synonym
        self.pred_mapping_json_file = self.local_data_root + pred_mapping
        self.type_list_json_file = self.local_data_root + focus_type_list
        self.alias_top_k = alias_top_k
        self.candidate_top_k = candidate_top_k
