import codecs
import globals
import logging
import sys
import re

from collections import defaultdict
from commons.nlu.schema.query import Query
from commons.nlu.classifier.attitude_classifier import YesNoClassifier, LikeDislikeClassifier
from commons.nlu.classifier.dialog_act_classifier import DialogActClassifier
from commons.nlu.classifier.emotion_classifier import EmotionClassifier
from commons.nlu.classifier.question_type_classifier import QuestionClassifier
from commons.nlu.np_generator import noun_phrase_generator, segmentor_plus
from commons.nlu.entity_linker import EntityLinker
from commons.utils import generate_trie_tree
from pyltp import NamedEntityRecognizer
from pyltp import Postagger
from pyltp import Segmentor
from pyltp import SentenceSplitter
from pyltp import Parser
from pyltp import SementicRoleLabeller


class Token(object):

    def __init__(self,
                 index,
                 word,
                 original_text,
                 word_start,
                 word_end,
                 pos,
                 ner,
                 arc_head,
                 arc_relation,
                 pos_start,
                 pos_end,
                 synonym_list,
                 is_stop_word):

        self.index = index
        self.word = word
        self.original_text = original_text
        self.word_start = word_start
        self.word_end = word_end
        self.pos = pos
        self.ner = ner
        self.arc_head = arc_head
        self.arc_relation = arc_relation
        self.pos_start = pos_start
        self.pos_end = pos_end
        self.synonym_list = synonym_list
        self.is_stop_word = is_stop_word
        self.semantic_roles = []
        pass


class Sentence(object):

    def __init__(self, raw_sentence, sentence_start, sentence_index, sentence_length, token_list, np_chunks):

        self.raw_sentence = raw_sentence
        self.sentence_start = sentence_start
        self.sentence_index = sentence_index
        self.sentence_length = sentence_length
        self.token_list = token_list
        self.np_chunks = np_chunks
        self.entity_list = []
        self.topic_entity_ids = []
        self.full_entity_ids = []
        self.type2entity = defaultdict(list)

        self.dialog_act_probability = None
        self.dialog_act_result = None
        self.dialog_act_result_with_confidence = None

        self.emotion_keywords = None
        self.emotion = []
        self.coarse_emotion = []
        self.emotion_degree = []
        self.emotion_polarity = []

        self.question_type_probability = None
        self.question_type_result = None

        self.polarity_probability = None
        self.polarity_result = None

        self.yesno_probability = None
        self.yesno_result = None
        self.yesno_result_with_confidence = None

        self.like_probability = None
        self.like_result = None
        self.like_result_with_confidence = None

        self.is_normalized = False
        self.normalized_tokens = []
        self.normalized_text = ""
        pass

    def update_entity(self, entity_mentions, entity_mapping, entity_type_exclusion_set):

        entity_ids = set()
        for entity_mention in entity_mentions:
            if entity_mention.entity is not None:
                self.entity_list.append(entity_mention)
                entity_ids.add(entity_mention.entity.kbid)
        self.full_entity_ids = list(entity_ids)

        entity_ids = set()
        for eid in self.full_entity_ids:
            entity_types = set(globals.entity_warehouse_server.get_type_by_kbid(eid))
            # the entity type only contains the type from exclusion, throw it away
            intersection_set = entity_types.intersection(entity_type_exclusion_set)
            if len(intersection_set) > 0 and len(intersection_set) == len(entity_types):
                continue
            for one_type in entity_types:
                self.type2entity[one_type].append(eid)
                if one_type in entity_mapping:
                    entity_ids.add(eid)
        self.topic_entity_ids = list(entity_ids)

        for eid in self.type2entity:
            self.type2entity[eid] = list(set(self.type2entity[eid]))

    def normalize(self, entity_mapping):

        start_index = 0
        for entity_mention in self.entity_list:

            found = False
            template_str = ""
            if entity_mention.entity.kbid in self.topic_entity_ids:
                entity_types = globals.entity_warehouse_server.get_type_by_kbid(entity_mention.entity.kbid)
                for type_id, type_str in entity_mapping.items():
                    if type_id in entity_types:
                        template_str = type_str
                        found = True
                        break

            if not found:
                tokens, text = self.get_token_and_text(start_index, entity_mention.end)
                self.normalized_tokens.extend(tokens)
                self.normalized_text += text
            else:
                if entity_mention.beg != start_index:
                    tokens, text = self.get_token_and_text(start_index, entity_mention.beg)
                    self.normalized_tokens.extend(tokens)
                    self.normalized_text += text

                self.normalized_tokens.append(template_str)
                self.normalized_tokens.append(entity_mention.text)
                self.normalized_text += template_str

            start_index = entity_mention.end

        if start_index != len(self.raw_sentence):
            tokens, text = self.get_token_and_text(start_index, len(self.raw_sentence))
            self.normalized_tokens.extend(tokens)
            self.normalized_text += text

        self.is_normalized = True
        pass

    def get_token_and_text(self, start, end):

        return_token = []
        return_text = ""
        hit = False
        for token in self.token_list:
            if hit:
                if token.word_start >= end:
                    break
                else:
                    if (token.pos != 'wp' or (token.pos == 'wp' and len(token.word) > 1))and not token.is_stop_word:
                        return_token.append(token.word)
                    return_text += token.word
            else:
                if token.word_start == start:
                    hit = True
                    if (token.pos != 'wp' or (token.pos == 'wp' and len(token.word) > 1))and not token.is_stop_word:
                        return_token.append(token.word)
                    return_text += token.word

        return return_token, return_text


class LanguageProcessor(object):

    def __init__(self, configure):

        self.system_logger = logging.getLogger("system_log")

        self._sentence_splitter = SentenceSplitter

        self._segmentor = Segmentor()
        self._segmentor.load_with_lexicon(configure.nlp_data_root + "/cws.model", configure.nlp_data_root + "/cws.tsv")

        self._segmentor_without_dictionary = Segmentor()
        self._segmentor_without_dictionary.load(configure.nlp_data_root + "/cws.model")

        self._postagger = Postagger()
        self._postagger.load(configure.nlp_data_root + "/pos.model")

        self._ner_recognizer = NamedEntityRecognizer()
        self._ner_recognizer.load(configure.nlp_data_root + "/ner.model")

        self._dependency_parser = Parser()
        self._dependency_parser.load(configure.nlp_data_root + "/parser.model")

        self._srl = SementicRoleLabeller()
        self._srl.load(configure.nlp_data_root + "/pisrl.model")

        self._stopwords_file = configure.nlp_data_root + "/stopwords.txt"
        self._stopwords_set = set([tk.strip() for tk in codecs.open(self._stopwords_file, 'r','utf-8').read().splitlines() if tk.strip() != "" ])

        self.entity_type_mapping_file = configure.entity_type_mapping_file
        self.entity_type_mapping = defaultdict()
        for line in codecs.open(self.entity_type_mapping_file, 'r', 'utf-8').read().splitlines():
            elems = line.split("\t")
            if len(elems) != 2:
                log_str = "Format error in file [%s] !!!\n" % self.entity_type_mapping_file
                self.system_logger.error(log_str)
                sys.stderr.write(log_str)
                continue
            self.entity_type_mapping[int(elems[0])] = "<" + str(elems[0]) + "_" + elems[1].strip() + ">"
        self.all_entity_replacements = list(self.entity_type_mapping.values())

        self.entity_type_exclusion_file = configure.entity_type_exclusion_file
        self.entity_type_exclusion_mapping = defaultdict()
        for line in codecs.open(self.entity_type_exclusion_file, 'r', 'utf-8').read().splitlines():
            elems = line.split("\t")
            if len(elems) != 2:
                log_str = "Format error in file [%s] !!!\n" % self.entity_type_exclusion_file
                self.system_logger.error(log_str)
                sys.stderr.write(log_str)
                continue
            self.entity_type_exclusion_mapping[int(elems[0])] = "<" + str(elems[0]) + "_" + elems[1].strip() + ">"
        self.entity_type_exclusion_set = set(self.entity_type_exclusion_mapping.keys())

        trie_tree, lexicon = generate_trie_tree(configure.nlp_data_root + "trust_list.tsv")
        self._lexicon = lexicon
        self._trie_tree = trie_tree

        self.entity_linker = EntityLinker()

        self.dialog_act_classifier = DialogActClassifier(configure.dialog_act_classifier_configure)

        self.emotion_classifier = EmotionClassifier(configure.emotion_classifier_configure)

        self.yes_no_classifier = YesNoClassifier(configure.attitude_classifier_configure)
        self.like_dislike_classifier = LikeDislikeClassifier(configure.attitude_classifier_configure)

        self.question_classifier = QuestionClassifier(configure.question_classifier_configure)
        self.question_response = ""

        self.noun_phrase_generator = noun_phrase_generator

        self.segmentor_plus = segmentor_plus

        self.turn_on = configure.turn_on

    def segment_chinese_sentence_without_dictionary(self, sentence):

        return list(self._segmentor_without_dictionary.segment(sentence))

    def generate_query(self, raw_sentence):

        # LTP cannot handle whitespace, it will remove whitespace automatically.
        # Therefore, we have to replace whitespace with some 'safe' tokens
        # e.g., comma
        original_raw_sentence = raw_sentence
        spaces = {}
        raw_sentence = list(raw_sentence)
        for s in re.finditer(' ', original_raw_sentence):
            spaces[s.start()] = s
            assert raw_sentence[s.start()] == ' '
            raw_sentence[s.start()] = '，'
        raw_sentence = ''.join(raw_sentence)

        splitted_sentences = list(SentenceSplitter.split(raw_sentence))
        structured_sentences = []
        sent_pos = 0
        sent_index = 0
        for one_sentence in splitted_sentences:
            sent_start = raw_sentence.index(one_sentence, sent_pos)
            sent_end = sent_start + len(one_sentence)
            sent_pos = sent_end

            tokens = list(self._segmentor.segment(one_sentence))
            tokens = list(self._resegment(tokens, lexicon=self._lexicon,
                                          trie_tree=self._trie_tree))

            postags = [None] * len(tokens)
            if "POS" in self.turn_on:
                postags = list(self._postagger.postag(tokens))

            ners = [None] * len(tokens)
            if "POS" in self.turn_on and "NER" in self.turn_on:
                ners = list(self._ner_recognizer.recognize(tokens, postags))

            arcs = [None] * len(tokens)
            if "POS" in self.turn_on and "DEP" in self.turn_on:
                arcs = self._dependency_parser.parse(tokens, postags)

            roles = [None] * len(tokens)
            if "POS" in self.turn_on and "DEP" in self.turn_on and "SRL" in self.turn_on:
                roles = list(self._srl.label(tokens, postags, arcs))

            arcs = list(arcs)

            token_list = []
            word_pos = 0
            sentence_length = 0
            for index, tk in enumerate(tokens):
                word_start = one_sentence.index(tk[0], word_pos)
                word_end = word_start + len(tk)
                word_pos = word_end

                # Recover token
                if tk == '，' and word_start+sent_start in spaces:
                    tk = ' '

                token = Token(index,
                              tk,
                              tk,
                              word_start,
                              word_end,
                              postags[index],
                              ners[index],
                              arcs[index].head if arcs[index] is not None else None,
                              arcs[index].relation if arcs[index] is not None else None,
                              word_start+sent_start,
                              word_end+sent_start,
                              [],
                              self._detect_stop_words(tk))

                token_list.append(token)
                if token.pos == "wp" or len(tk.strip()) == 0:
                    continue

                sentence_length += len(tk)

            if len(token_list) == 0:
                continue

            if roles != [None] * len(tokens):
                for role in roles:
                    token = token_list[role.index]
                    for arg in role.arguments:
                        token.semantic_roles.append((arg.name, arg.range.start, arg.range.end))

            np_chunks = self._generate_np_chunks(token_list)

            # Recover sentence
            one_sentence = list(one_sentence)
            for s in spaces:
                if s >= sent_start and s < sent_end:
                    n = s - sent_start
                    assert one_sentence[n] == '，'
                    one_sentence[n] = ' '
            one_sentence = ''.join(one_sentence)

            sentence = Sentence(one_sentence, sent_start, sent_index, sentence_length, token_list, np_chunks)
            sent_index += 1
            structured_sentences.append(sentence)

        return_query = Query(raw_sentence, splitted_sentences, structured_sentences)

        if "POS" in self.turn_on and "ATT" in self.turn_on:
            self._detect_attitude(return_query)

        if "POS" in self.turn_on and "QTY" in self.turn_on:
            self._detect_question_type(return_query)

        if "ACT" in self.turn_on:
            self._dialog_act_detector(return_query)

        if "EMO" in self.turn_on:
            self._detect_emotion_type(return_query)

        if "ENL" in self.turn_on:
            for sentence_index, sentence in enumerate(return_query.sentence_list):
                self._link_entity(sentence_index, return_query.sentence_list)
                return_query.full_entity_ids.extend(sentence.full_entity_ids)
                return_query.topic_entity_ids.extend(sentence.topic_entity_ids)
                return_query.normalized_text += sentence.normalized_text
                for entity_type, entity_list in sentence.type2entity.items():
                    return_query.type2entity[entity_type].extend(entity_list)

            if len(return_query.sentence_list) > 1:
                return_query.full_entity_ids = list(set(return_query.full_entity_ids))
                return_query.topic_entity_ids = list(set(return_query.topic_entity_ids))

                for entity_type in return_query.type2entity:
                    return_query.type2entity[entity_type] = list(set(return_query.type2entity[entity_type]))

            if return_query.normalized_text in self.all_entity_replacements:
                return_query.single_entity = True

        return return_query

    def _detect_stop_words(self, word):
        return word.strip() in self._stopwords_set

    def _generate_np_chunks(self, token_list):
        return list(noun_phrase_generator(token_list))

    def _dialog_act_detector(self, query):
        self.dialog_act_classifier.classify(query)
        query.map_dialog_act_to_sentence_index()

    def _detect_question_type(self, query):
        self.question_classifier.classify(query)

    def _detect_emotion_type(self, query):
        self.emotion_classifier.classify(query)

    def _detect_attitude(self, query):
        self.yes_no_classifier.classify(query)
        self.like_dislike_classifier.classify(query)

    def _link_entity(self, sentence_index, sentence_list):
        entity_mention = self.entity_linker.linking(sentence_index, sentence_list)
        sentence_list[sentence_index].update_entity(entity_mention,
                                                    self.entity_type_mapping,
                                                    self.entity_type_exclusion_set)
        sentence_list[sentence_index].normalize(self.entity_type_mapping)

    def _ploarity_detector(self, query):
        return []

    def _resegment(self, tokens, lexicon=None, trie_tree=None):
        return self.segmentor_plus(tokens, lexicon=lexicon, trie_tree=trie_tree)
