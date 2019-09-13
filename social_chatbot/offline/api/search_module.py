import globals

from online.online_service.short_sentence_search_service import SentenceSearchConstraint

class ShortSentenceSearchApi(object):

    def __init__(self, local_configure):
        self.language_processor = globals.nlp_processor
        self.short_sentence_search_server = globals.short_sentence_search_server

    def search_processor(self, raw_query, constraint_dict):

        search_constraint = SentenceSearchConstraint(**constraint_dict)
        query = self.language_processor.generate_query(raw_query)
        if len(search_constraint.entity_list) == 0:
            search_constraint.entity_list = query.topic_entity_ids
        search_result = self.short_sentence_search_server.search_sentence(query, search_constraint)
        return search_result.to_json()

