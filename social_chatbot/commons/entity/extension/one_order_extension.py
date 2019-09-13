import codecs
import json
import random

import globals
from commons.entity.extension.entity_extension import EntityExtension


class EntityOneOrderExtensionFromKG(EntityExtension):

    def __init__(self, configure):

        self.obj_placeholder = configure.obj_placeholder
        self.sub_placeholder = configure.sub_placeholder
        self.templates_file = configure.templates_json_file
        self.relations_file = configure.relations_json_file
        self.type_list_file = configure.type_list_json_file
        self.alias_top_k = configure.alias_top_k
        self.candidate_top_k = configure.candidate_top_k

        self.templates_dict = json.loads(codecs.open(self.templates_file, 'r', 'utf-8').read())
        self.relations_dict = json.loads(codecs.open(self.relations_file, 'r', 'utf-8').read())
        temp_focus_type_list = json.loads(codecs.open(self.type_list_file, 'r', 'utf-8').read())

        super().__init__("EntityOneOrderExtensionFromKG", temp_focus_type_list)

    def template_to_sentence(self, subject_name, subject_type, predicate, obj_name):
        temp_key = str((subject_type, predicate))
        if temp_key in self.templates_dict:
            templates = self.templates_dict[temp_key]
            # TODO: select one from multiple templates
            sentence = templates[0]
            sentence = sentence.replace(self.sub_placeholder, subject_name)
            sentence = sentence.replace(self.obj_placeholder, obj_name)
            return sentence
        else:
            return ''

    # Return value is (sentence, _id_obj, obj_pop_val)
    def generate_sentence_and_entity(self, entity_id):
        result = []
        subject = globals.entity_warehouse_server.get_entry_by_kbid(entity_id)
        if subject:
            if 'type' in subject:
                subject_name = self.get_random_name(subject, self.alias_top_k)
                for item in subject['type']:
                    subject_type = self.switch_list_dict(item, 0)
                    if subject_type in self.relations_dict:
                        for relation in self.relations_dict[subject_type]:
                            predicate = relation[0]
                            object_type_requirement = relation[1]
                            obj_name, _id_obj, obj_pop_val = self.select_object(subject, predicate, object_type_requirement)
                            if obj_name:
                                sentence = self.template_to_sentence(subject_name, subject_type, predicate, obj_name)
                                result.append((sentence, _id_obj, obj_pop_val))

        if result:
            result.sort(key=lambda x: x[-1], reverse=True)
            return random.choice(result[:self.candidate_top_k])
        else:
            return ('', None, 0)