import codecs
import json
import logging
import sys
import globals

from collections import defaultdict
from dialog.annotated_intent import AnnotatedIntent
from dialog.intent_grounding import IntentGrounding
from dialog.question import AnnotatedQuestion
from dialog.question_grounding import QuestionGrounding
from dialog.schema import QuestionCondition


class DialogGraph(object):

    def __init__(self, configure):

        self.system_logger = logging.getLogger("system_log")

        self.intent_file = configure.intent_json_file
        self.grounding_file = configure.grounding_json_file
        self.question_file = configure.question_json_file
        self.language_process = globals.nlp_processor

        self.intent_dict = defaultdict()
        self.grounding_dict = defaultdict()
        self.question_dict = defaultdict()
        self.search_ids = set()

        self._load_data()
        self._check()
        self._validation()

    def _load_data(self):

        intent_obj = json.loads(codecs.open(self.intent_file, 'r', 'utf-8').read())
        for intent_type, intent_list in intent_obj.items():

            if intent_type == "AnnotatedIntent":
                for one_intent in intent_list:
                    annotated_intent = AnnotatedIntent(**one_intent)
                    if annotated_intent.id in self.intent_dict:
                        log_str = "Intent id [%s] has been exist!!!\n"%annotated_intent.id
                        self.system_logger.error(log_str)
                        sys.stderr.write(log_str)
                        continue
                    annotated_intent.replace_entity_slot_with_id(self.language_process.entity_type_mapping)
                    annotated_intent.process_sample_queries()
                    self.search_ids.add(annotated_intent.search_id)
                    self.intent_dict[annotated_intent.id] = annotated_intent
            else:
                log_str = "Not support for intent type [%s] !!!\n" % intent_type
                self.system_logger.info(log_str)
                sys.stderr.write(log_str)

        grounding_obj = json.loads(codecs.open(self.grounding_file, 'r', 'utf-8').read())
        for grounding_type, grounding_list in grounding_obj.items():
            if grounding_type == "IntentGrounding":
                for one_grounding in grounding_list:
                    grounding = IntentGrounding(**one_grounding)
                    if grounding.id in self.grounding_dict:
                        log_str = "Grounding id [%s] has been exist!!!\n" % grounding.id
                        self.system_logger.error(log_str)
                        sys.stderr.write(log_str)
                        continue
                    self.grounding_dict[grounding.id] = grounding
            elif grounding_type == "QuestionGrounding":
                for one_grounding in grounding_list:
                    grounding = QuestionGrounding(**one_grounding)
                    if grounding.id in self.grounding_dict:
                        log_str = "Grounding id [%s] has been exist!!!\n" % grounding.id
                        self.system_logger.error(log_str)
                        sys.stderr.write(log_str)
                        continue
                    self.grounding_dict[grounding.id] = grounding
            else:
                log_str = "Not support for grounding type [%s] !!!\n" % grounding_type
                self.system_logger.info(log_str)
                sys.stderr.write(log_str)

        question_obj = json.loads(codecs.open(self.question_file, 'r', 'utf-8').read())
        for one_question in question_obj:
            question = AnnotatedQuestion(**one_question)
            if question.id in self.question_dict:
                log_str = "Question id [%s] has been exist!!!\n" % question.id
                self.system_logger.error(log_str)
                sys.stderr.write(log_str)
                continue
            self.question_dict[question.id] = question

    def _check(self):

        for id, one_intent in self.intent_dict.items():
            for one_grounding in one_intent.grounding_id:
                if one_grounding not in self.grounding_dict:
                    log_str = "Grounding id [%s] from intent [%s] does not exist in global grounding dictionary!!!\n" \
                             % (one_grounding, id)
                    self.system_logger.error(log_str)
                    sys.stderr.write(log_str)
                    sys.exit()

                for question_condition, question_id in one_intent.questions.items():
                    for one_question_id in question_id:
                        if one_question_id not in self.question_dict:
                            log_str = \
                                "Question id [%s] from intent [%s] does not exist in global question dictionary!!!\n" \
                                % (one_question_id, id)
                            self.system_logger.error(log_str)
                            sys.stderr.write(log_str)
                            sys.exit()

        for id, one_question in self.question_dict.items():
            for policy_condition, intent_id in one_question.policy_dict.items():
                if intent_id not in self.intent_dict:
                    log_str = "Intent id [%s] from question [%s] does not exist in global intent dictionary!!!\n" \
                              % (intent_id, id)
                    self.system_logger.error(log_str)
                    sys.stderr.write(log_str)
                    sys.exit()

    def _validation(self):

        for id, intent_obj in self.intent_dict.items():
            for grounding_id in intent_obj.grounding_id:
                if len(self.get_grounding(grounding_id).entity_type) > 0:
                    if len(set(self.get_grounding(grounding_id).entity_type).intersection(set(intent_obj.entity_type))) == 0:
                        log_str = "Intent[%s]'s entity has no interaction with one of its grounding[%s]. The entity " \
                                  "defined in intent is [%s] and in grounding is [%s]" \
                                  % (id, grounding_id, self.get_grounding(grounding_id).entity_type,
                                     intent_obj.entity_type)
                        self.system_logger.warning(log_str)
                        print(log_str)

            for question_condition, question_list in intent_obj.questions.items():
                if question_condition == QuestionCondition.SingleEntity:
                    for question_id in question_list:
                        if len(self.get_question(question_id).samples_with_entity_slot) == 0:
                            log_str = "Question[%s] is used to accept SingleEntity Condition. " \
                                      "But its samples_with_entity_slot is empty" % question_id
                            self.system_logger.warning(log_str)
                            print(log_str)

    def get_intent(self, intent_id):

        if intent_id in self.intent_dict:
            return self.intent_dict[intent_id]
        else:
            log_str = "Invalid intent id [%s]" % intent_id
            self.system_logger.error(log_str)
            sys.stderr.write(log_str)
            return None

    def get_grounding(self, grounding_id):

        if grounding_id in self.grounding_dict:
            return self.grounding_dict[grounding_id]
        else:
            log_str = "Invalid grounding id [%s]" % grounding_id
            self.system_logger.error(log_str)
            sys.stderr.write(log_str)
            return None

    def get_question(self, question_id):

        if question_id in self.question_dict:
            return self.question_dict[question_id]
        else:
            log_str = "Invalid question id [%s]" % question_id
            self.system_logger.error(log_str)
            sys.stderr.write(log_str)
            return None

