import logging
import globals
from collections import defaultdict
from operator import attrgetter


class EntityStatus(object):

    def __init__(self, entity_id, freq, most_recent_turn):

        self.entity_id = entity_id
        self.freq = freq
        self.most_recent_turn = most_recent_turn


class DialogTurnState(object):

    def __init__(self, turn_number, user_query, bot_response):

        self.turn_number = turn_number

        self.user_query = user_query
        self.bot_response = bot_response

        self.user_utterance = ""
        self.bot_utterance = ""

        if user_query is None and turn_number > 1:
            raise ValueError("User query is None in [%d]th turn\n" % turn_number)

        if turn_number > 1:
            self.user_utterance = user_query.raw_query

        if bot_response is None:
            raise ValueError("Bot response is None in [%d]th turn\n" % self.turn_number)

        self.bot_utterance = " ".join(bot_response.response_str_list)


class DialogSessionState(object):

    def __init__(self, session_id):

        self.system_logger = logging.getLogger("system_log")

        # session global parameter
        self.started = False
        self.current_turn = 1
        self.dialog_graph = globals.dialog_graph
        self.session_id = session_id
        # store the entity freq and most recent mentioned turn information
        # entity_id to EntityStatus
        self.entity_status = defaultdict(EntityStatus)

        # store search history index
        self.search_index = set()

        # store extension history index
        self.extension_index = set()

        # store topic history index
        self.topic = set()

        self.turn_state = defaultdict()

        # index from turn to full info
        self.turn_to_raw_query = defaultdict()
        self.turn_to_raw_response = defaultdict()
        self.turn_to_executed_intent = defaultdict()
        self.turn_to_executed_grounding = defaultdict()
        self.turn_to_executed_search_constraint = defaultdict()
        self.turn_to_executed_search_result = defaultdict()
        self.turn_to_executed_question = defaultdict()
        self.turn_to_executed_entity = defaultdict()
        self.turn_to_executed_qa_result = defaultdict()
        self.turn_to_executed_grounding_entity = defaultdict()
        self.turn_to_executed_intent_entity = defaultdict()
        self.turn_to_executed_question_entity = defaultdict()
        self.turn_to_question_waiting_for_response = defaultdict()
        self.turn_to_executed_entity_status = defaultdict()
        self.turn_to_executed_exist_entity = defaultdict()
        self.turn_to_executed_new_entity = defaultdict()
        self.turn_to_executed_response_entity = defaultdict()

    def update_dialog_state(self, turn_number, dialog_turn_state):

        if self.current_turn != turn_number:
            raise ValueError("Dialog current_turn [%d] is not equal to turn_number [%d]\n" %
                             (self.current_turn, turn_number))

        self.turn_state[turn_number] = dialog_turn_state

        self.turn_to_raw_query[turn_number] = dialog_turn_state.user_utterance
        self.turn_to_raw_response[turn_number] = dialog_turn_state.bot_utterance

        self.turn_to_executed_intent[turn_number] = dialog_turn_state.bot_response.intent_id
        self.turn_to_executed_grounding[turn_number] = dialog_turn_state.bot_response.grounding_id
        self.turn_to_executed_search_constraint[turn_number] = dialog_turn_state.bot_response.search_constraint
        self.turn_to_executed_search_result[turn_number] = dialog_turn_state.bot_response.search_result
        self.turn_to_executed_question[turn_number] = dialog_turn_state.bot_response.question_id
        self.turn_to_executed_entity[turn_number] = dialog_turn_state.bot_response.entity_id
        self.turn_to_executed_qa_result[turn_number] = dialog_turn_state.bot_response.qa_result
        self.turn_to_executed_grounding_entity[turn_number] = dialog_turn_state.bot_response.grounding_entity_id
        self.turn_to_executed_intent_entity[turn_number] = dialog_turn_state.bot_response.intent_entity_id
        self.turn_to_executed_question_entity[turn_number] = dialog_turn_state.bot_response.question_entity_id
        self.turn_to_executed_entity_status[turn_number] = dialog_turn_state.bot_response.entity_status_for_search
        self.turn_to_executed_exist_entity[turn_number] = dialog_turn_state.bot_response.exist_entity_from_query
        self.turn_to_executed_new_entity[turn_number] = dialog_turn_state.bot_response.new_entity_from_query
        self.turn_to_executed_response_entity[turn_number] = dialog_turn_state.bot_response.entity_from_response

        self.turn_to_question_waiting_for_response[turn_number] = None
        if dialog_turn_state.bot_response.question_id != "" and \
                self.dialog_graph.question_dict[dialog_turn_state.bot_response.question_id].is_waiting_response:
            self.turn_to_question_waiting_for_response[turn_number] = dialog_turn_state.bot_response.question_id

        all_entities_from_this_turn = dialog_turn_state.bot_response.entity_id \
                                      + dialog_turn_state.bot_response.entity_from_response

        for one_entity_id in all_entities_from_this_turn:
            if one_entity_id not in self.entity_status:
                self.entity_status[one_entity_id] = EntityStatus(one_entity_id, 1, turn_number)
            else:
                self.entity_status[one_entity_id].freq += 1
                self.entity_status[one_entity_id].most_recent_turn = turn_number

        self.search_index.update(dialog_turn_state.bot_response.search_index)
        self.extension_index.update(dialog_turn_state.bot_response.extension_index)
        self.topic.update(dialog_turn_state.bot_response.topic)

        self.current_turn += 1

    def question_waiting_for_response(self, turn_number):
        if turn_number >= self.current_turn:
            raise ValueError("Provided turn [%d] should not be less than history max turn [%d]\n" % (turn_number,
                                                                                                     self.current_turn))
        return self.turn_to_question_waiting_for_response[turn_number]

    def execute_intent(self, turn_number):
        if turn_number >= self.current_turn:
            raise ValueError("Provided turn [%d] should not be less than history max turn [%d]\n" % (turn_number,
                                                                                                     self.current_turn))
        return self.turn_to_executed_intent[turn_number]

    def execute_grounding(self, turn_number):
        if turn_number >= self.current_turn:
            raise ValueError("Provided turn [%d] should not be less than history max turn [%d]\n" % (turn_number,
                                                                                                     self.current_turn))
        return self.turn_to_executed_grounding[turn_number]

    def execute_search_result(self, turn_number):
        if turn_number >= self.current_turn:
            raise ValueError("Provided turn [%d] should not be less than history max turn [%d]\n" % (turn_number,
                                                                                                     self.current_turn))
        return self.turn_to_executed_search_result[turn_number]

    def execute_search_constraint(self, turn_number):
        if turn_number >= self.current_turn:
            raise ValueError("Provided turn [%d] should not be less than history max turn [%d]\n" % (turn_number,
                                                                                                     self.current_turn))
        return self.turn_to_executed_search_constraint[turn_number]

    def execute_question(self, turn_number):
        if turn_number >= self.current_turn:
            raise ValueError("Provided turn [%d] should not be less than history max turn [%d]\n" % (turn_number,
                                                                                                     self.current_turn))
        return self.turn_to_executed_question[turn_number]

    def execute_entity(self, turn_number):
        if turn_number >= self.current_turn:
            raise ValueError("Provided turn [%d] should not be less than history max turn [%d]\n" % (turn_number,
                                                                                                     self.current_turn))
        return self.turn_to_executed_entity[turn_number]

    def execute_qa(self, turn_number):
        if turn_number >= self.current_turn:
            raise ValueError("Provided turn [%d] should not be less than history max turn [%d]\n" % (turn_number,
                                                                                                     self.current_turn))
        return self.turn_to_executed_qa_result[turn_number]

    def execute_grounding_entity(self, turn_number):
        if turn_number >= self.current_turn:
            raise ValueError("Provided turn [%d] should not be less than history max turn [%d]\n" % (turn_number,
                                                                                                     self.current_turn))
        return self.turn_to_executed_grounding_entity[turn_number]

    def execute_intent_entity(self, turn_number):
        if turn_number >= self.current_turn:
            raise ValueError("Provided turn [%d] should not be less than history max turn [%d]\n" % (turn_number,
                                                                                                     self.current_turn))
        return self.turn_to_executed_intent_entity[turn_number]

    def execute_question_entity(self, turn_number):
        if turn_number >= self.current_turn:
            raise ValueError("Provided turn [%d] should not be less than history max turn [%d]\n" % (turn_number,
                                                                                                     self.current_turn))
        return self.turn_to_executed_question_entity[turn_number]

    def execute_entity_status(self, turn_number):
        if turn_number >= self.current_turn:
            raise ValueError("Provided turn [%d] should not be less than history max turn [%d]\n" % (turn_number,
                                                                                                     self.current_turn))
        return self.turn_to_executed_entity_status[turn_number]

    def execute_exist_entity(self, turn_number):
        if turn_number >= self.current_turn:
            raise ValueError("Provided turn [%d] should not be less than history max turn [%d]\n" % (turn_number,
                                                                                                     self.current_turn))
        return self.turn_to_executed_exist_entity[turn_number]

    def execute_new_entity(self, turn_number):
        if turn_number >= self.current_turn:
            raise ValueError("Provided turn [%d] should not be less than history max turn [%d]\n" % (turn_number,
                                                                                                     self.current_turn))
        return self.turn_to_executed_new_entity[turn_number]

    def execute_response_entity(self, turn_number):
        if turn_number >= self.current_turn:
            raise ValueError("Provided turn [%d] should not be less than history max turn [%d]\n" % (turn_number,
                                                                                                     self.current_turn))
        return self.turn_to_executed_response_entity[turn_number]

    def entities_ranked_by_recent_then_freq(self):

        sorted_entities = sorted(list(self.entity_status.values()),
                                 key=attrgetter('most_recent_turn', 'freq'),
                                 reverse=True)

        return [item.entity_id for item in sorted_entities]

    def entities_ranked_by_freq_then_recent(self):

        sorted_entities = sorted(list(self.entity_status.values()),
                                 key=attrgetter('freq', 'most_recent_turn'),
                                 reverse=True)

        return [item.entity_id for item in sorted_entities]


