import globals

from collections import defaultdict
from collections import OrderedDict


class Query(object):

    def __init__(self, raw_query, splitted_sentences, sentence_list):

        self.raw_query = raw_query
        self.splitted_sentences = splitted_sentences
        self.sentence_list = sentence_list
        # uniq entity ids
        self.full_entity_ids = []
        self.topic_entity_ids = []
        # entity type to entity id mapping
        self.type2entity = defaultdict(list)
        # replace the entity with the entity replacement
        self.normalized_text = ""
        # whether this query consists of only one entity
        self.single_entity = False
        # whether this query has intent
        self.has_intent = False
        # dialog_result
        self.dialog_act_to_sentence_index = defaultdict(list)

    def update_type2entity(self, entity_id):

        entity_types = globals.entity_warehouse_server.get_type_by_kbid(entity_id)
        for one_type in entity_types:
            if one_type not in self.type2entity:
                self.type2entity[one_type] = []
            self.type2entity[one_type].append(entity_id)

    def map_dialog_act_to_sentence_index(self):

        for sentence in self.sentence_list:
            if sentence.dialog_act_result_with_confidence is not None:
                self.dialog_act_to_sentence_index[sentence.dialog_act_result_with_confidence].append(
                    sentence.sentence_index)

    def to_json(self):

        return_dict = {}

        for index, sentence in enumerate(self.sentence_list):
            key1 = index + 1
            return_dict[key1] = {}

            segment_pos = []
            dependency = []
            semantic_roles = []
            for token in sentence.token_list:
                segment_pos.append(token.original_text + "/" +
                                   str(token.pos) + "/" +
                                   str(token.ner) + "/" +
                                   str(token.is_stop_word))
                if token.arc_head == 0:
                    dependency.append("root ->" + token.original_text + ":" +
                                      str(token.arc_relation))
                else:
                    try:
                        dependency.append(sentence.token_list[token.arc_head - 1].original_text +
                                          "->" +
                                          token.original_text +
                                          ":" +
                                          str(token.arc_relation))
                    except TypeError:
                        pass
                if len(token.semantic_roles) != 0:
                    for one_role in token.semantic_roles:
                        arg_str = []
                        for i in range(one_role[1], one_role[2] + 1):
                            arg_str.append(sentence.token_list[i].original_text)
                        semantic_roles.append({"predicate": token.original_text,
                                               "role_type": one_role[0],
                                               "role_object": " ".join(arg_str)})

            return_dict[key1]["raw_sentence"] = sentence.raw_sentence
            return_dict[key1]["sentence_start"] = sentence.sentence_start
            return_dict[key1]["sentence_length"] = sentence.sentence_length
            return_dict[key1]["分词词性"] = segment_pos
            return_dict[key1]["依存句法"] = dependency
            return_dict[key1]["语义角色"] = semantic_roles
            return_dict[key1]["normalized_tokens"] = sentence.normalized_tokens
            return_dict[key1]["normalized_text"] = sentence.normalized_text
            return_dict[key1]["type2entity"] = sentence.type2entity

            yesno_probability = {}
            try:
                for key, value in sentence.yesno_probability.items():
                    yesno_probability[key.name] = value
            except AttributeError:
                pass
            return_dict[key1]["是否分类"] = yesno_probability

            like_probability = {}
            try:
                for key, value in sentence.like_probability.items():
                    like_probability[key.name] = value
            except AttributeError:
                pass
            return_dict[key1]["喜恶分类"] = like_probability

            dialog_act_probability = {}
            try:
                for key, value in sentence.dialog_act_probability.items():
                    dialog_act_probability[key.name] = value
            except AttributeError:
                pass
            return_dict[key1]["对话ACT"] = dialog_act_probability

            emotion = {}
            emotion["情感检测关键词"] = {}
            try:
                for i in sentence.emotion_keywords:
                    emotion["情感检测关键词"][i] = 1
                for i in range(len(sentence.emotion)):
                    emotion[sentence.emotion[i].name] = {"一级情感": sentence.coarse_emotion[i].name, "degree": sentence.emotion_degree[i], "polarity": sentence.emotion_polarity[i]}
            except:
                pass
            return_dict[key1]["情感检测"] = emotion

            question_type_probability = {}
            try:
                for key, value in sentence.question_type_probability.items():
                    question_type_probability[key.name] = value
            except AttributeError:
                pass
            return_dict[key1]["问题类型"] = question_type_probability

            entities = []
            try:
                entities = [i.to_json() for i in sentence.entity_list]
            except AttributeError:
                pass
            return_dict[key1]["实体链接"] = entities

            try:
                return_dict[key1]["问题答复"] = sentence.question_response
            except AttributeError:
                pass

        return_dict = OrderedDict(sorted(return_dict.items(), key=lambda x: x[0]))

        return return_dict

    def to_api(self):

        return_dict = self.to_json()
        return_dict[0] = {}
        return_dict[0]["query_topic_entity_ids"] = self.topic_entity_ids
        return_dict[0]["query_full_entity_ids"] = self.full_entity_ids
        return_dict[0]["normalized_text"] = self.normalized_text
        return_dict[0]["type2entity"] = self.type2entity
        return return_dict
