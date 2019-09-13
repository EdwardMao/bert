import globals


class DialogGraphApi(object):

    def __init__(self, local_configure):
        self.language_processor = globals.nlp_processor
        self.dialog_graph = globals.dialog_graph

    def get_intent(self, intent_id):

        if intent_id in self.dialog_graph.intent_dict:
            return self.dialog_graph.intent_dict[intent_id].to_json()
        else:
            return {}

