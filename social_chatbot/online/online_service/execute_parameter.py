import globals
import logging
import random

from collections import defaultdict
from enum import Enum


class EntityStatusForSearch(Enum):

    AllExistEntity = 1
    AllNewEntity = 2
    ExistAndNewEntity = 3
    NoEntity = 4


class DialogExecuteParameter(object):

    def __init__(self, current_turn, dialog_state, user_query):

        self.system_logger = logging.getLogger("system_log")

        self.current_turn = current_turn
        self.dialog_state = dialog_state
        self.user_query = user_query
        self.dialog_graph = globals.dialog_graph
        self.logger_dict = defaultdict()

        self.previous_intent_id = ""
        self.previous_grounding_id = ""
        self.previous_search_constraint = ""
        self.previous_search_result = None
        self.previous_question_id = ""
        self.previous_entity_id = []
        self.previous_qa_result = None
        self.previous_grounding_entity_id = ""
        self.previous_intent_entity_id = ""
        self.previous_question_entity_id = ""
        self.previous_entity_status_for_search = None
        self.exist_entity_from_previous_query = list()
        self.new_entity_from_previous_query = list()
        self.entity_from_previous_response = list()

        if current_turn > 1:
            self.previous_intent_id = dialog_state.execute_intent(current_turn - 1)
            self.previous_grounding_id = dialog_state.execute_grounding(current_turn - 1)
            self.previous_search_constraint = dialog_state.execute_search_constraint(current_turn - 1)
            self.previous_search_result = dialog_state.execute_search_result(current_turn - 1)
            self.previous_question_id = dialog_state.execute_question(current_turn - 1)
            self.previous_entity_id = dialog_state.execute_entity(current_turn - 1)
            self.previous_qa_result = dialog_state.execute_qa(current_turn - 1)
            self.previous_grounding_entity_id = dialog_state.execute_grounding_entity(current_turn - 1)
            self.previous_intent_entity_id = dialog_state.execute_intent_entity(current_turn - 1)
            self.previous_question_entity_id = dialog_state.execute_question_entity(current_turn - 1)
            self.previous_entity_status_for_search = dialog_state.execute_entity_status(current_turn - 1)
            self.exist_entity_from_previous_query = dialog_state.execute_exist_entity(current_turn - 1)
            self.new_entity_from_previous_query = dialog_state.execute_new_entity(current_turn - 1)
            self.entity_from_previous_response = dialog_state.execute_response_entity(current_turn - 1)

        self._current_intent_id = ""
        self._current_grounding_id = ""
        self._current_search_constraint = ""
        self._current_search_result = None
        self._current_question_id = ""
        self._current_entity_id = user_query.topic_entity_ids if user_query is not None else list()
        self._current_qa_result = None
        self._current_grounding_entity_id = ""
        self._current_intent_entity_id = ""
        self._current_question_entity_id = ""
        self._current_entity_status_for_search = None
        self._exist_entity_from_current_query = list()
        self._new_entity_from_current_query = list()
        self._entity_from_current_response = list()

        self.response_str_list = list()
        self.current_turn_search_index = set()
        self.current_turn_extension_index = set()
        self.current_turn_topic = set()
        self.index_of_current_question_sentence = -1

    def add_to_log(self, key, value):
        self.logger_dict[key] = value

    def decide_entity_status_for_search(self):

        if len(self.user_query.topic_entity_ids) > 0:

            entity_until_now = set()
            start_turn = self.current_turn - 1
            while start_turn > 1:
                entity_until_now.update(self.dialog_state.execute_entity(start_turn))
                start_turn -= 1

            for one_entity_id in self.user_query.topic_entity_ids:
                if one_entity_id in entity_until_now:
                    self._exist_entity_from_current_query.append(one_entity_id)
                else:
                    self._new_entity_from_current_query.append(one_entity_id)

            if len(self._new_entity_from_current_query) == 0:
                self._current_entity_status_for_search = EntityStatusForSearch.AllExistEntity
            elif len(self.exist_entity_from_current_query) == 0:
                self._current_entity_status_for_search = EntityStatusForSearch.AllNewEntity
            else:
                self._current_entity_status_for_search = EntityStatusForSearch.ExistAndNewEntity
        else:
            self._current_entity_status_for_search = EntityStatusForSearch.NoEntity

        self._exist_entity_from_current_query = list(set(self._exist_entity_from_current_query))
        self._new_entity_from_current_query = list(set(self._new_entity_from_current_query))

    @property
    def current_intent_id(self):
        return self._current_intent_id

    # Setter function
    @current_intent_id.setter
    def current_intent_id(self, value):
        if self.dialog_graph.get_intent(value) is None and value != "":
            self.system_logger.error("Invalid intent id[%s] in DialogExecuteParameter" % value)
            raise TypeError("Invalid intent id[%s] in DialogExecuteParameter" % value)
        self._current_intent_id = value

    @property
    def current_grounding_id(self):
        return self._current_grounding_id

    # Setter function
    @current_grounding_id.setter
    def current_grounding_id(self, value):
        if self.dialog_graph.get_grounding(value) is None and value != "":
            self.system_logger.error("Invalid grounding id[%s] in DialogExecuteParameter" % value)
            raise TypeError("Invalid node grounding[%s] in DialogExecuteParameter" % value)
        self._current_grounding_id = value

    @property
    def current_question_id(self):
        return self._current_question_id

    # Setter function
    @current_question_id.setter
    def current_question_id(self, value):
        if self.dialog_graph.get_question(value) is None and value != "":
            self.system_logger.error("Invalid question id[%s] in DialogExecuteParameter" % value)
            raise TypeError("Invalid node question[%s] in DialogExecuteParameter" % value)
        self._current_question_id = value

    @property
    def current_search_constraint(self):
        return self._current_search_constraint

    # Setter function
    @current_search_constraint.setter
    def current_search_constraint(self, value):
        if value not in self.dialog_graph.search_ids and value != "":
            self.system_logger.error("Invalid question id[%s] in DialogExecuteParameter" % value)
            raise TypeError("Invalid node question[%s] in DialogExecuteParameter" % value)
        self._current_search_constraint = value

    @property
    def current_entity_id(self):
        return self._current_entity_id

    # Setter function
    @current_entity_id.setter
    def current_entity_id(self, value):
        self._current_entity_id = value

    @property
    def current_qa_result(self):
        return self._current_qa_result

    # Setter function
    @current_qa_result.setter
    def current_qa_result(self, value):
        self._current_qa_result = value

    @property
    def current_question_entity_id(self):
        return self._current_question_entity_id

    # Setter function
    @current_question_entity_id.setter
    def current_question_entity_id(self, value):
        self._current_question_entity_id = value

    @property
    def current_intent_entity_id(self):
        return self._current_intent_entity_id

    # Setter function
    @current_intent_entity_id.setter
    def current_intent_entity_id(self, value):
        self._current_intent_entity_id = value

    @property
    def current_grounding_entity_id(self):
        return self._current_grounding_entity_id

    # Setter function
    @current_grounding_entity_id.setter
    def current_grounding_entity_id(self, value):
        self._current_grounding_entity_id = value

    @property
    def current_search_result(self):
        return self._current_search_result

    # Setter function
    @current_search_result.setter
    def current_search_result(self, value):
        self._current_search_result = value

    @property
    def current_entity_status_for_search(self):
        return self._current_entity_status_for_search

    @property
    def exist_entity_from_current_query(self):
        return self._exist_entity_from_current_query

    @property
    def new_entity_from_current_query(self):
        return self._new_entity_from_current_query

    @property
    def entity_from_current_response(self):
        return self._entity_from_current_response

    # Setter function
    @entity_from_current_response.setter
    def entity_from_current_response(self, value):
        self._entity_from_current_response = value


def generate_execute_parameter(current_turn, dialog_state, user_query):
    return DialogExecuteParameter(current_turn, dialog_state, user_query)
