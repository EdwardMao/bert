import globals
import json
import logging

from commons.nlu.classifier.dialog_act_classifier import DialogActLabel
from commons.nlu.schema.response import Response
from commons.utils import generate_html_str_with_br
from dialog.dialog_state import DialogTurnState
from online.online_service.execute_parameter import generate_execute_parameter
from online.online_service.online_logging import OnlineInfoLogger
from online.online_service.short_sentence_search_service import SentenceSearchConstraint

class ChatEngine(object):

    def __init__(self):

        self.dialog_graph = globals.dialog_graph
        self.nlp_processor = globals.nlp_processor
        self.intent_classifier_server = globals.intent_classifier_server
        self.general_response_generator = globals.general_response_generator
        self.qa_server = globals.qa_server
        self.short_sentence_search_server = globals.short_sentence_search_server
        self.init_intent_id = "系统_初始化"
        pass

    def call(self, current_turn, dialog_state, user_raw_query):

        if not dialog_state.started:
            dialog_state.started = True
            user_query = None
            execute_parameter = generate_execute_parameter(current_turn, dialog_state, user_query)
            self.dialog_graph.get_intent(self.init_intent_id).execute(execute_parameter)
            return post_process(execute_parameter)

        user_query = self.nlp_processor.generate_query(user_raw_query)
        execute_parameter = generate_execute_parameter(current_turn, dialog_state, user_query)

        answerable, answer_to_intent_id = self.can_answer_last_turn_question(execute_parameter)
        execute_parameter.add_to_log("answerable", answerable)
        execute_parameter.add_to_log("answer_to_intent_id", answer_to_intent_id)

        if user_query.single_entity and answerable:
            return self.generate_intent_response(execute_parameter, answer_to_intent_id)

        _, top_intent, intent_log = self.intent_classifier_server.classify(user_query)
        if top_intent is not None:
            execute_parameter.add_to_log("top_intent", top_intent.to_json())
            execute_parameter.add_to_log("intent_log", intent_log)
            return self.generate_intent_response(execute_parameter, top_intent.item_id)
        execute_parameter.add_to_log("top_intent", "")
        execute_parameter.add_to_log("intent_log", intent_log)

        if answerable:
            return self.generate_intent_response(execute_parameter, answer_to_intent_id)

        # execute qa process
        if self.qa_server.turn_on:
            qa_answer = self.qa_server.qa_retrieve(user_raw_query)
            execute_parameter.current_qa_result = qa_answer
            if qa_answer.is_an_answer:
                return self.generate_qa_response(execute_parameter, qa_answer)

        if DialogActLabel.Question in user_query.dialog_act_to_sentence_index:
            return self.generate_question_response(execute_parameter)

        return self.generate_statement_response(execute_parameter)

    def generate_qa_response(self, execute_parameter, qa_answer):

        execute_parameter.current_turn_search_index.add(qa_answer.question_related_entity)
        execute_parameter.response_str_list = ["好像我知道点什么 ^_^ " + qa_answer.result_str]
        print(qa_answer.to_json())
        search_constraint = SentenceSearchConstraint(**json.loads(globals.default_sentence_search_constraint_str))
        search_constraint.entity_list = [qa_answer.question_related_entity]

        search_result_in_qa_response = \
            self.short_sentence_search_server.search_sentence(execute_parameter.user_query, search_constraint)
        random_sentence = \
            search_result_in_qa_response.get_random_sentence_from_topk(3, execute_parameter.dialog_state.search_index)

        if random_sentence is not None:
            execute_parameter.response_str_list.append(self.dialog_graph.get_grounding("系统_说到").execute(None) +
                                                       self.dialog_graph.get_grounding("系统_听说").execute(None) +
                                                       random_sentence.raw_sentence)
            execute_parameter.current_turn_search_index.add(random_sentence.sentence_index)
            execute_parameter.add_to_log("search_result_in_qa_result", random_sentence.to_json())
            execute_parameter.add_to_log("search_constraint_in_qa_result",
                                         search_result_in_qa_response.search_query_dict)

        return post_process(execute_parameter)

    def generate_intent_response(self, execute_parameter, intent_id):

        execute_parameter.user_query.has_intent = True
        execute_parameter.current_intent_id = intent_id
        self.dialog_graph.get_intent(intent_id).execute(execute_parameter)
        return post_process(execute_parameter)

    def generate_question_response(self, execute_parameter):

        # generate grounding for question
        user_query = execute_parameter.user_query
        question_sentence_index = execute_parameter.user_query.dialog_act_to_sentence_index[DialogActLabel.Question][0]
        execute_parameter.index_of_current_question_sentence = question_sentence_index
        question_sentence = user_query.sentence_list[question_sentence_index]
        question_type = question_sentence.question_type_result.name
        question_grounding_result = self.dialog_graph.get_grounding(question_type).execute(execute_parameter)
        execute_parameter.add_to_log("question_grounding_result", question_grounding_result.to_json())

        # conduct general search
        general_response_list = self.general_response_generator.generate_general_search_response(execute_parameter)

        #TODO: grounding is need between quetion_grounding and general response

        execute_parameter.response_str_list = \
            [question_grounding_result.grounding_str, "不过，" + general_response_list[0]]
        for response_str in general_response_list[1:]:
            execute_parameter.response_str_list.append(response_str)

        return post_process(execute_parameter)

    def generate_statement_response(self, execute_parameter):

        general_response_list = self.general_response_generator.generate_general_search_response(execute_parameter)
        for response_str in general_response_list:
            execute_parameter.response_str_list.append(response_str)

        return post_process(execute_parameter)

    def can_answer_last_turn_question(self, execute_parameter):

        current_turn = execute_parameter.current_turn
        last_turn_question_wait_for_response = \
            execute_parameter.dialog_state.question_waiting_for_response(current_turn - 1)

        if last_turn_question_wait_for_response is None:
            return False, ""

        return self.dialog_graph.get_question(last_turn_question_wait_for_response).\
            can_answer_question(execute_parameter)


def post_process(execute_parameter):

    # generate response
    bot_response = Response(execute_parameter)

    # generate turn state
    dialog_turn_state = DialogTurnState(execute_parameter.current_turn, execute_parameter.user_query, bot_response)

    # update dialog state
    execute_parameter.dialog_state.update_dialog_state(execute_parameter.current_turn, dialog_turn_state)

    # logging
    globals.online_info_logger.component_logging(execute_parameter)
    globals.online_info_logger.user_logging(execute_parameter)

    return generate_html_str_with_br(execute_parameter.response_str_list)
