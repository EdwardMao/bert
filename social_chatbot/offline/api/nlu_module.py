import globals
from dialog.dialog_state import DialogSessionState
from online.online_service.execute_parameter import generate_execute_parameter

class NluApi(object):

    def __init__(self, local_configure):

        self.language_processor = globals.nlp_processor
        self.bm25_sentence_similarity_server = globals.bm25_sentence_similarity_server
        self.intent_classifier_server = globals.intent_classifier_server

    def nlu_processor(self, raw_text):

        query = self.language_processor.generate_query(raw_text)

        dialog_state = DialogSessionState("4api")
        exe_parameter = generate_execute_parameter(0, dialog_state, query)
        for index, sentence in enumerate(query.sentence_list):
            exe_parameter.index_of_current_question_sentence = index
            grounding_id = sentence.question_type_result.name
            grounding_obj = globals.dialog_graph.get_grounding(grounding_id)
            question_response = grounding_obj.execute(exe_parameter)
            query.sentence_list[index].question_response = question_response.grounding_str

        return query.to_api()

    def bm25_similarity(self, query_a, query_b):

        query_a = self.language_processor.generate_query(query_a)
        query_b = self.language_processor.generate_query(query_b)
        score, a_vector, b_vector = self.bm25_sentence_similarity_server.get_similarity(query_a, query_b)
        return {
            "score": score,
            "query_a": query_a.to_api(),
            "query_b": query_b.to_api(),
            "a_idf_vector": a_vector,
            "b_tf_vector": b_vector
        }

    def intent_classifier(self, query):

        query = self.language_processor.generate_query(query)
        ranked_intents, decision, decision_log = self.intent_classifier_server.classify(query)
        ranked_intents = [str(item) for item in ranked_intents]
        return_dict = {"ranked_intents": ranked_intents,
                       "query_json": query.to_api(),
                       "decision": str(decision),
                       "decision_log": decision_log}

        return return_dict

