import json
import logging
import random
import re

import globals
from commons.nlu.classifier.question_type_classifier import QuestionLabel
from dialog.schema import GraphBaseObj
from enum import Enum

from collections import defaultdict


class QuestionGroundingType(Enum):

    General = 1
    Specific = 2


class QuestionGroundingResult(object):

    def __init__(self, question_grounding_type, grounding_str):
        self.question_grounding_type = question_grounding_type
        self.grounding_str = grounding_str

    def to_json(self):
        return {
            "question_grounding_type": self.question_grounding_type.name,
            "grounding_str": self.grounding_str
        }


class QuestionGrounding(GraphBaseObj):

    def __init__(self, id, key_words, template):
        super().__init__(id, self.__class__.__name__)
        self.system_logger = logging.getLogger("system_log")
        self.key_words = key_words
        self.sorted_key_words = sorted(list(key_words.keys()), key=lambda x:len(x), reverse=True)
        self.template = template

    def execute(self, exe_parameter):

        return_str = ""
        if self.id == "YesNo":
            return_str = execute_yesno(exe_parameter,
                                       self.key_words,
                                       self.sorted_key_words,
                                       self.do_not_know_prefix_id,
                                       self.template)
        elif self.id == "What":
            return_str = execute_what(exe_parameter,
                                      self.key_words,
                                      self.sorted_key_words,
                                      self.do_not_know_prefix_id,
                                      self.template)
        elif self.id == "Who":
            return_str = execute_who(exe_parameter,
                                     self.key_words,
                                     self.sorted_key_words,
                                     self.do_not_know_prefix_id,
                                     self.template)
        elif self.id == "When":
            return_str = execute_when(exe_parameter,
                                      self.key_words,
                                      self.sorted_key_words,
                                      self.do_not_know_prefix_id,
                                      self.template)
        elif self.id == "Where":
            return_str = execute_where(exe_parameter,
                                       self.key_words,
                                       self.sorted_key_words,
                                       self.do_not_know_prefix_id,
                                       self.template)
        elif self.id == "Which":
            return_str = execute_which(exe_parameter,
                                       self.key_words,
                                       self.sorted_key_words,
                                       self.do_not_know_prefix_id,
                                       self.template)
        elif self.id == "How":
            return_str = execute_how(exe_parameter,
                                     self.key_words,
                                     self.sorted_key_words,
                                     self.do_not_know_prefix_id,
                                     self.template)
        elif self.id == "Why":
            return_str = execute_why(exe_parameter,
                                     self.key_words,
                                     self.sorted_key_words,
                                     self.do_not_know_prefix_id,
                                     self.template)
        elif self.id == "Howmany":
            return_str = execute_howmany(exe_parameter,
                                         self.key_words,
                                         self.sorted_key_words,
                                         self.do_not_know_prefix_id,
                                         self.template)
        elif self.id == "Rhetorical":
            return_str = execute_rhetorical(exe_parameter,
                                            self.key_words,
                                            self.sorted_key_words,
                                            self.do_not_know_prefix_id,
                                            self.template)
        elif self.id == "Choose":
            return_str = execute_choose(exe_parameter,
                                        self.key_words,
                                        self.sorted_key_words,
                                        self.do_not_know_prefix_id,
                                        self.template)
        else:
            log_str = "No supported QuestionGrounding id [%s]\n" % self.id
            self.system_logger.error(log_str)
            print(log_str)

        if return_str == "":
            do_not_know_grounding = exe_parameter.dialog_graph.get_grounding(self.do_not_know_id)
            grounding_str = do_not_know_grounding.execute(exe_parameter)
            grounding_type = QuestionGroundingType.General
            return QuestionGroundingResult(grounding_type, grounding_str)

        return QuestionGroundingResult(QuestionGroundingType.Specific, return_str)


def execute_yesno(exe_parameter, key_words, sorted_key_words, do_not_know_prefix_id, template):

    dialog_graph = exe_parameter.dialog_graph
    sentence_index = exe_parameter.index_of_current_question_sentence
    sentence = exe_parameter.user_query.sentence_list[sentence_index]
    if sentence.question_type_result != QuestionLabel.YesNo:
        return ""

    search_result = re.search(r'(.)[不|没|木](.)', sentence.raw_sentence, re.M | re.I)
    if search_result is not None:
        search_str = search_result.group()
        do_not_know_prefix_grounding = dialog_graph.get_grounding(do_not_know_prefix_id)
        prefix_str = do_not_know_prefix_grounding.execute(exe_parameter)
        return prefix_str + search_str

    return ""


def execute_what(exe_parameter, key_words, sorted_key_words, do_not_know_prefix_id, template):

    def analyze_syntax():

        for token in sentence.token_list:
            if len(token.semantic_roles) != 0:
                for one_role in token.semantic_roles:
                    if one_role[0] in ["A1", "ADV"]:
                        arg_str = []
                        for i in range(one_role[1], one_role[2] + 1):
                            arg_str.append(sentence.token_list[i].original_text)
                        role_object = "".join(arg_str)
                        if role_object.find(kword) >= 0:
                            return prefix_str + token.original_text + role_object

        for token in sentence.token_list:
            if token.arc_head == 0:
                continue
            else:
                try:
                    if str(token.arc_relation) == "ATT" and token.original_text == kword:
                        return prefix_str + token.original_text + sentence.token_list[token.arc_head - 1].original_text
                except TypeError:
                    pass

        return ""

    dialog_graph = exe_parameter.dialog_graph
    do_not_know_prefix_grounding = dialog_graph.get_grounding(do_not_know_prefix_id)
    prefix_str = do_not_know_prefix_grounding.execute(exe_parameter)

    sentence_index = exe_parameter.index_of_current_question_sentence
    sentence = exe_parameter.user_query.sentence_list[sentence_index]

    if sentence.question_type_result != QuestionLabel.What:
        return ""

    for kword in sorted_key_words:
        if kword in sentence.raw_sentence:
            if key_words[kword][0] == "Dep":
                return_str = analyze_syntax()
                if return_str != "":
                    return return_str
            else:
                return prefix_str + random.choice(key_words[kword]) + kword

    return ""


def execute_who(exe_parameter, key_words, sorted_key_words, do_not_know_prefix_id, template):

    dialog_graph = exe_parameter.dialog_graph
    do_not_know_prefix_grounding = dialog_graph.get_grounding(do_not_know_prefix_id)
    prefix_str = do_not_know_prefix_grounding.execute(exe_parameter)

    sentence_index = exe_parameter.index_of_current_question_sentence
    sentence = exe_parameter.user_query.sentence_list[sentence_index]

    if sentence.question_type_result != QuestionLabel.Who:
        return ""

    for kword in sorted_key_words:
        if kword in sentence.raw_sentence:
            if key_words[kword][0] == "Dep":
                return ""
            else:
                return prefix_str + random.choice(key_words[kword]) + kword

    return ""


def execute_when(exe_parameter, key_words, sorted_key_words, do_not_know_prefix_id, template):

    dialog_graph = exe_parameter.dialog_graph
    do_not_know_prefix_grounding = dialog_graph.get_grounding(do_not_know_prefix_id)
    prefix_str = do_not_know_prefix_grounding.execute(exe_parameter)

    sentence_index = exe_parameter.index_of_current_question_sentence
    sentence = exe_parameter.user_query.sentence_list[sentence_index]

    if sentence.question_type_result != QuestionLabel.When:
        return ""

    for kword in sorted_key_words:
        if kword in sentence.raw_sentence:
            if key_words[kword][0] == "Dep":
                return ""
            else:
                return prefix_str + random.choice(key_words[kword]) + kword
    return ""


def execute_where(exe_parameter, key_words, sorted_key_words, do_not_know_prefix_id, template):

    def analyze_syntax():

        for token in sentence.token_list:
            if len(token.semantic_roles) != 0:
                for one_role in token.semantic_roles:
                    if one_role[0] in ["LOC"]:
                        arg_str = []
                        for i in range(one_role[1], one_role[2] + 1):
                            arg_str.append(sentence.token_list[i].original_text)
                        role_object = "".join(arg_str)
                        if role_object.find(kword) >= 0:
                            return prefix_str + token.original_text + role_object

        return ""

    dialog_graph = exe_parameter.dialog_graph
    do_not_know_prefix_grounding = dialog_graph.get_grounding(do_not_know_prefix_id)
    prefix_str = do_not_know_prefix_grounding.execute(exe_parameter)

    sentence_index = exe_parameter.index_of_current_question_sentence
    sentence = exe_parameter.user_query.sentence_list[sentence_index]

    if sentence.question_type_result != QuestionLabel.Where:
        return ""

    for kword in sorted_key_words:
        if kword in sentence.raw_sentence:
            if key_words[kword][0] == "Dep":
                return_str = analyze_syntax()
                if return_str != "":
                    return return_str
            else:
                return prefix_str + random.choice(key_words[kword]) + kword
    return ""


def execute_which(exe_parameter, key_words, sorted_key_words, do_not_know_prefix_id, template):

    def analyze_syntax():

        for token in sentence.token_list:
            if len(token.semantic_roles) != 0:
                for one_role in token.semantic_roles:
                    if one_role[0] in ["A2", "A1"]:
                        arg_str = []
                        for i in range(one_role[1], one_role[2] + 1):
                            arg_str.append(sentence.token_list[i].original_text)
                        role_object = "".join(arg_str)
                        if role_object.find(kword) >= 0:
                            return prefix_str + token.original_text + role_object
        return ""

    dialog_graph = exe_parameter.dialog_graph
    do_not_know_prefix_grounding = dialog_graph.get_grounding(do_not_know_prefix_id)
    prefix_str = do_not_know_prefix_grounding.execute(exe_parameter)

    sentence_index = exe_parameter.index_of_current_question_sentence
    sentence = exe_parameter.user_query.sentence_list[sentence_index]

    if sentence.question_type_result != QuestionLabel.Which:
        return ""

    for kword in sorted_key_words:
        if kword in sentence.raw_sentence:
            if key_words[kword][0] == "Dep":
                return_str = analyze_syntax()
                if return_str != "":
                    return return_str
            else:
                return prefix_str + random.choice(key_words[kword]) + kword

    return ""


def execute_how(exe_parameter, key_words, sorted_key_words, do_not_know_prefix_id, template):

    def analyze_syntax():
        for token in sentence.token_list:
            if len(token.semantic_roles) != 0:
                for one_role in token.semantic_roles:
                    if one_role[0] in ["ADV"]:
                        arg_str = []
                        for i in range(one_role[1], one_role[2] + 1):
                            arg_str.append(sentence.token_list[i].original_text)
                        role_object = "".join(arg_str)
                        if role_object == kword:
                            return prefix_str + role_object + token.original_text
        return ""

    dialog_graph = exe_parameter.dialog_graph
    do_not_know_prefix_grounding = dialog_graph.get_grounding(do_not_know_prefix_id)
    prefix_str = do_not_know_prefix_grounding.execute(exe_parameter)

    sentence_index = exe_parameter.index_of_current_question_sentence
    sentence = exe_parameter.user_query.sentence_list[sentence_index]

    if sentence.question_type_result != QuestionLabel.How:
        return ""

    for kword in sorted_key_words:
        if kword in sentence.raw_sentence:
            if key_words[kword][0] == "Dep":
                return_str = analyze_syntax()
                if return_str != "":
                    return return_str
            else:
                return prefix_str + random.choice(key_words[kword]) + kword

    return ""


def execute_why(exe_parameter, key_words, sorted_key_words, do_not_know_prefix_id, template):

    def analyze_syntax():

        for token in sentence.token_list:
            if len(token.semantic_roles) != 0:
                for one_role in token.semantic_roles:
                    if one_role[0] in ["ADV"]:
                        arg_str = []
                        for i in range(one_role[1], one_role[2] + 1):
                            arg_str.append(sentence.token_list[i].original_text)
                        role_object = "".join(arg_str)
                        if role_object == kword:
                            return prefix_str + token.original_text + role_object
        return ""

    dialog_graph = exe_parameter.dialog_graph
    do_not_know_prefix_grounding = dialog_graph.get_grounding(do_not_know_prefix_id)
    prefix_str = do_not_know_prefix_grounding.execute(exe_parameter)

    sentence_index = exe_parameter.index_of_current_question_sentence
    sentence = exe_parameter.user_query.sentence_list[sentence_index]

    if sentence.question_type_result != QuestionLabel.Why:
        return ""

    for kword in sorted_key_words:
        if kword in sentence.raw_sentence:
            if key_words[kword][0] == "Dep":
                return_str = analyze_syntax()
                if return_str != "":
                    return return_str
            else:
                return prefix_str + random.choice(key_words[kword]) + kword

    return ""


def execute_howmany(exe_parameter, key_words, sorted_key_words, do_not_know_prefix_id, template):

    def analyze_syntax():

        for token in sentence.token_list:
            if len(token.semantic_roles) != 0:
                for one_role in token.semantic_roles:
                    if one_role[0] in ["A0", "A1"]:
                        arg_str = []
                        for i in range(one_role[1], one_role[2] + 1):
                            arg_str.append(sentence.token_list[i].original_text)
                        role_object = "".join(arg_str)
                        if role_object.find(kword) >= 0:
                            return prefix_str + token.original_text + role_object
        return ""

    dialog_graph = exe_parameter.dialog_graph
    do_not_know_prefix_grounding = dialog_graph.get_grounding(do_not_know_prefix_id)
    prefix_str = do_not_know_prefix_grounding.execute(exe_parameter)

    sentence_index = exe_parameter.index_of_current_question_sentence
    sentence = exe_parameter.user_query.sentence_list[sentence_index]

    if sentence.question_type_result != QuestionLabel.Howmany:
        return ""

    for kword in sorted_key_words:
        if kword in sentence.raw_sentence:
            if key_words[kword][0] == "Dep":
                return_str = analyze_syntax()
                if return_str != "":
                    return return_str
            else:

                return prefix_str + random.choice(key_words[kword]) + kword
    return ""


def execute_rhetorical(exe_parameter, key_words, sorted_key_words, do_not_know_prefix_id, template):
    return random.choice(template)


def execute_choose(exe_parameter, key_words, sorted_key_words, do_not_know_prefix_id, template):
    return random.choice(template)


