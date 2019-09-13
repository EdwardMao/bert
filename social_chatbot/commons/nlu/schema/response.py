class Response(object):

    def __init__(self, execute_parameter):
        # response_str: the actual string text of the response
        # intent_id:
        # grounding_id:
        # search_id:
        # question_id
        # exe_entity
        self.response_str_list = execute_parameter.response_str_list
        self.intent_id = execute_parameter.current_intent_id
        self.grounding_id = execute_parameter.current_grounding_id
        self.search_constraint = execute_parameter.current_search_constraint
        self.search_result = execute_parameter.current_search_result
        self.question_id = execute_parameter.current_question_id
        self.entity_id = execute_parameter.current_entity_id
        self.grounding_entity_id = execute_parameter.current_grounding_entity_id
        self.intent_entity_id = execute_parameter.current_intent_entity_id
        self.question_entity_id = execute_parameter.current_question_entity_id
        self.qa_result = execute_parameter.current_qa_result

        self.entity_status_for_search = execute_parameter.current_entity_status_for_search
        self.exist_entity_from_query = execute_parameter.exist_entity_from_current_query
        self.new_entity_from_query = execute_parameter.new_entity_from_current_query
        self.entity_from_response = execute_parameter.entity_from_current_response

        self.search_index = execute_parameter.current_turn_search_index
        self.extension_index = execute_parameter.current_turn_extension_index
        self.topic = execute_parameter.current_turn_topic
