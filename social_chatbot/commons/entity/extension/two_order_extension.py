import codecs
import json
import random

import globals
from commons.entity.extension.entity_extension import EntityExtension


class EntityTwoOrderExtensionFromKG(EntityExtension):

    def __init__(self, configure):

        self.sub_placeholder = configure.sub_placeholder
        self.obj_a_placeholder = configure.obj_a_placeholder
        self.obj_b_placeholder = configure.obj_b_placeholder
        self.relations_file = configure.relations_2a_json_file
        self.templates_file = configure.templates_2a_json_file
        self.type_list_file = configure.type_list_json_file
        self.alias_top_k = configure.alias_top_k
        self.candidate_top_k = configure.candidate_top_k

        self.relations_dict = json.loads(codecs.open(self.relations_file, 'r', 'utf-8').read())
        self.templates_dict = json.loads(codecs.open(self.templates_file, 'r', 'utf-8').read())
        temp_focus_type_list = json.loads(codecs.open(self.type_list_file, 'r', 'utf-8').read())

        super().__init__("EntityTwoOrderExtensionFromKG", temp_focus_type_list)

    # Return value is (obj_a_name, _id_obj_a, obj_b_name, _id_obj_b, pop_val)
    def select_object_two_order(self, subject_id, subject, pred_a, type_a, pred_b, type_b):
        if pred_a not in subject:
            return (None, None, None, None, 0)

        accessed_item_list_obj_a = subject[pred_a]
        if not accessed_item_list_obj_a:
            return (None, None, None, None, 0)

        id_list_obj_a = self.copy_accessed_entity_id(accessed_item_list_obj_a)
        if not id_list_obj_a:  # do search only when _id is not copied
            id_list_obj_a = self.search_accessed_entity_id(accessed_item_list_obj_a)

        id_sel = []
        for _id_obj_a in id_list_obj_a:  # obj_a must have _id and name
            obj_a_dict = globals.entity_warehouse_server.get_entry_by_kbid(_id_obj_a)
            if obj_a_dict:
                if self.check_type(obj_a_dict, type_a):
                    obj_a_name = self.get_random_name(obj_a_dict, self.alias_top_k)
                    pop_val_a = self.popular_value_reweight(obj_a_dict)

                    # TODO: instead of returnign the top, return a list and select by the combined score
                    obj_b_name, _id_obj_b, pop_val_b = self.select_object(obj_a_dict, pred_b, type_b)

                    if obj_b_name:  # obj_b must have name, but _id is not a must yet
                        if _id_obj_b == subject_id:  # looping, ignore
                            continue

                        pop_val = pop_val_a + pop_val_b  # TODO: +?
                        id_sel.append((obj_a_name, _id_obj_a, obj_b_name, _id_obj_b, pop_val))

        if id_sel:
            id_sel.sort(key=lambda x: x[-1], reverse=True)
            return random.choice(id_sel[:self.candidate_top_k])
        else:
            return (None, None, None, None, 0)

    def template_to_sentence(self,
                             subject_name,
                             subject_type,
                             predicate_a,
                             predicate_b,
                             obj_a_name,
                             obj_b_name):

        temp_key = str((subject_type, predicate_a, predicate_b))
        if temp_key in self.templates_dict:
            templates = self.templates_dict[temp_key]
            # TODO: select one from multiple templates
            sentence = templates[0]
            sentence = sentence.replace(self.sub_placeholder, subject_name)
            sentence = sentence.replace(self.obj_a_placeholder, obj_a_name)
            sentence = sentence.replace(self.obj_b_placeholder, obj_b_name)
            return sentence
        else:
            return ''

    # Return value is (sentence, _id_obj_a, _id_obj_b, combined_pop_val)
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
                            pred_a = relation[0]
                            type_a = relation[1]
                            pred_b = relation[2]
                            type_b = relation[3]

                            obj_a_name, _id_obj_a, obj_b_name, _id_obj_b, pop_val = \
                                self.select_object_two_order(entity_id, subject, pred_a, type_a, pred_b, type_b)

                            if obj_b_name:
                                sentence = self.template_to_sentence(subject_name,
                                                                     subject_type,
                                                                     pred_a,
                                                                     pred_b,
                                                                     obj_a_name,
                                                                     obj_b_name)

                                result.append((sentence, _id_obj_a, _id_obj_b, pop_val))

        if result:
            result.sort(key=lambda x: x[-1], reverse=True)
            return random.choice(result[:self.candidate_top_k])
        else:
            return ('', None, None, 0)