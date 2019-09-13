import logging
import json

from collections import defaultdict


class OnlineInfoLogger(object):

    def __init__(self):
        self.system_logger = logging.getLogger("system_log")
        self.user_logger = logging.getLogger("user_log")
        self.component_logger = logging.getLogger("component_log")
        pass

    def component_logging(self, execute_parameter, log_str=""):
        if log_str != "":
            self.component_logger.info(log_str)
            return

        logging_dict = defaultdict()
        logging_dict["session_id"] = execute_parameter.dialog_state.session_id
        logging_dict["turn"] = execute_parameter.current_turn
        logging_dict["query"] = execute_parameter.user_query.to_api() \
            if execute_parameter.user_query is not None else ""
        for key, value in execute_parameter.logger_dict.items():
            logging_dict[key] = value

        logging_dict["current_intent_id"] = execute_parameter.current_intent_id
        logging_dict["current_grounding_id"] = execute_parameter.current_grounding_id
        logging_dict["current_search_constraint"] = execute_parameter.current_search_constraint
        logging_dict["current_search_result"] = execute_parameter.current_search_result
        logging_dict["current_question_id"] = execute_parameter.current_question_id
        logging_dict["current_entity_id"] = execute_parameter.current_entity_id
        logging_dict["current_grounding_entity_id"] = execute_parameter.current_grounding_entity_id
        logging_dict["current_intent_entity_id"] = execute_parameter.current_intent_entity_id
        logging_dict["current_question_entity_id"] = execute_parameter.current_question_entity_id
        logging_dict["current_question_entity_id"] = execute_parameter.current_qa_result.to_json() \
            if execute_parameter.current_qa_result is not None else ""

        logging_dict["current_entity_status_for_search"] = execute_parameter.current_entity_status_for_search.name \
            if execute_parameter.current_entity_status_for_search is not None else ""
        logging_dict["exist_entity_from_current_query"] = execute_parameter.exist_entity_from_current_query
        logging_dict["new_entity_from_current_query"] = execute_parameter.new_entity_from_current_query

        self.component_logger.info(json.dumps(logging_dict))
        pass

    def system_logging(self, execute_parameter, log_str=""):
        if log_str != "":
            self.component_logger.info(log_str)
            return
        pass

    def user_logging(self, execute_parameter, log_str=""):
        if log_str != "":
            self.component_logger.info(log_str)
            return

        logging_dict = defaultdict()
        logging_dict["session_id"] = execute_parameter.dialog_state.session_id
        logging_dict["turn"] = execute_parameter.current_turn
        logging_dict["query"] = execute_parameter.user_query.raw_query \
            if execute_parameter.user_query is not None else ""
        logging_dict["response"] = "".join(execute_parameter.response_str_list)

        self.user_logger.info(json.dumps(logging_dict))
        pass
