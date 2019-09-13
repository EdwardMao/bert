import codecs
import globals
import logging
import random
import re
import sys

from collections import defaultdict
from enum import Enum

from abc import ABCMeta, abstractmethod


class PolicyConditions(Enum):

    Yes = 1
    No = 2
    YNUnclear = 3
    HasEntity = 4
    NoEntity = 5
    POS = 6
    NEG = 7


class QuestionCondition(Enum):

    SingleEntity = 1
    MultipleEntity = 2
    NoEntity = 3
    RandomSelection = 4


class GraphBaseObj(object):

    def __init__(self, id, kind):

        self.system_logger = logging.getLogger("system_log")
        self.id = id
        self.kind = kind
        self.entity_slot_pattern = re.compile(r"\[[0-9]*[_]{0,1}object\]")
        self.entity_slot_base = '[object]'
        self.pattern = re.compile(r'<.*?>')
        self.samples_with_entity_slot = []
        self.samples_without_entity_slot = []
        self.entity_type = []
        self.do_not_know_id = "系统_不知道"
        self.do_not_know_prefix_id = "系统_不知道_前缀"

    @abstractmethod
    def execute(self, exe_parameter):
        pass

    def initialize(self, templates):

        for one_template in templates:
            queue = [one_template]
            while len(queue) > 0:
                current_template = queue[0]
                queue.pop(0)
                search_results = self.pattern.search(current_template)
                if search_results is None:
                    if re.search(self.entity_slot_pattern, current_template) is not None:
                        self.samples_with_entity_slot.append(current_template)
                    else:
                        self.samples_without_entity_slot.append(current_template)
                    continue
                multiple_choice = \
                    current_template[search_results.regs[0][0] + 1: search_results.regs[0][1] - 1].split("|")
                for one_choice in multiple_choice:
                    queue.append(current_template[:search_results.regs[0][0]] +
                                 one_choice +
                                 current_template[search_results.regs[0][1]:])

    def _random_select_execute_entity_candidate(self, user_query, entity_type=None):

        if entity_type is None:
            entity_type = self.entity_type

        entity_candidate = self.generate_entity_candidate(user_query, entity_type)
        if len(entity_candidate) == 0:
            return None, "", ""

        random_entity_type = random.choice(list(entity_candidate.keys()))
        random_entity_id = random.choice(entity_candidate[random_entity_type])
        entity_random_name = globals.entity_warehouse_server.get_random_name_by_kbid(random_entity_id)

        return random_entity_id, random_entity_type, entity_random_name

    def generate_entity_candidate(self, user_query, entity_type=None):

        if entity_type is None:
            entity_type = self.entity_type

        entity_candidate = defaultdict(list)
        for one_entity_type in entity_type:
            if one_entity_type in user_query.type2entity:
                entity_candidate[one_entity_type] = user_query.type2entity[one_entity_type]

        return entity_candidate
