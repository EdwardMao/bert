import codecs
import json
import random

import globals
from commons.entity.extension.entity_extension import EntityExtension


class EntityAnalogyExtensionFromKG(EntityExtension):

    def __init__(self, configure):
        self.Alg_Requirement_Const = 3

        self.obj_placeholder = configure.obj_placeholder
        self.sub_placeholder = configure.sub_placeholder
        self.ana_sub_placeholder = configure.ana_sub_placeholder
        self.ana_obj_placeholder = configure.ana_obj_placeholder
        self.relations_file = configure.relations_json_file
        self.templates_file = configure.templates_analogy_json_file
        self.type_list_file = configure.type_list_json_file
        self.pred_synonym_file = configure.pred_synonym_json_file
        self.pred_mapping_file = configure.pred_mapping_json_file
        self.alias_top_k = configure.alias_top_k
        self.candidate_top_k = configure.candidate_top_k

        self.relations_dict = json.loads(codecs.open(self.relations_file, 'r', 'utf-8').read())
        self.templates_dict = json.loads(codecs.open(self.templates_file, 'r', 'utf-8').read())
        self.pred_synonym = json.loads(codecs.open(self.pred_synonym_file, 'r', 'utf-8').read())
        self.pred_mapping = json.loads(codecs.open(self.pred_mapping_file, 'r', 'utf-8').read())
        temp_focus_type_list = json.loads(codecs.open(self.type_list_file, 'r', 'utf-8').read())

        super().__init__("EntityAnalogyExtensionFromKG", temp_focus_type_list)

    def unified_predicate(self, input_predicate):
        if input_predicate in self.pred_mapping:
            return self.pred_mapping[input_predicate]
        else:
            return input_predicate

    def diversed_predicate(self, input_predicate):
        if input_predicate in self.pred_synonym:
            return self.pred_synonym[input_predicate]
        else:
            return [input_predicate]

    def select_object_analogy(self, entry_dict_list):
        K = len(entry_dict_list)

        entry_id_set = []
        entry_id_dict = {}
        for entry_dict in entry_dict_list:
            entry_id_set.append(entry_dict['_id'])
            entry_id_dict[entry_dict['_id']] = entry_dict
        entry_id_set = set(entry_id_set)

        # Find the existing relations from the entries
        relations_exist = []
        for subject in entry_dict_list:
            # Use type and relation dict to reduce the dict search space
            if 'type' in subject:
                subject_id = subject['_id']
                for item in subject['type']:
                    subject_type = self.switch_list_dict(item, 0)
                    if subject_type in self.relations_dict:
                        for relation in self.relations_dict[subject_type]:
                            predicate = relation[0]
                            unique_pred = self.unified_predicate(predicate)
                            if predicate in subject:
                                for obj in subject[predicate]:
                                    obj_id = self.switch_list_dict(obj, 1)
                                    if obj_id in entry_id_set and obj_id != subject_id:
                                        relations_exist.append([[subject_id, obj_id], unique_pred, subject_type])

        # Discover new entity with relation in analogy
        discover_list = []
        for subject in entry_dict_list:
            subject_id = subject['_id']
            subject_name = self.get_random_name(subject, self.alias_top_k)

            for relation in relations_exist:
                analogy_list = relation[0]
                unique_pred = relation[1]
                required_sub_type = relation[2]

                if self.check_type(subject, required_sub_type):

                    ana_sub_id = analogy_list[0]
                    ana_obj_id = analogy_list[1]
                    ana_sub_name = self.get_random_name(entry_id_dict[ana_sub_id], self.alias_top_k)
                    ana_obj_name = self.get_random_name(entry_id_dict[ana_obj_id], self.alias_top_k)

                    predicate_list = self.diversed_predicate(unique_pred)

                    if subject_id not in analogy_list:
                        for predicate in predicate_list:
                            if predicate in subject:
                                for obj in subject[predicate]:
                                    obj_id = self.switch_list_dict(obj, 1)
                                    if obj_id and obj_id not in entry_id_set:
                                        obj_dict = globals.entity_warehouse_server.get_entry_by_kbid(obj_id)
                                        pop_val = self.popular_value_reweight(obj_dict)
                                        obj_name = self.get_random_name(obj_dict, self.alias_top_k)
                                        discover_list.append((obj_name,
                                                              obj_id,
                                                              subject_name,
                                                              ana_sub_name,
                                                              ana_obj_name,
                                                              required_sub_type,
                                                              unique_pred,
                                                              pop_val))

        if discover_list:
            discover_list.sort(key=lambda x: x[-1], reverse=True)
            return random.choice(discover_list[:self.candidate_top_k])
        else:
            return (None, None, None, None, None, None, None, None, 0)


    def template_to_sentence(self,
                             subject_name,
                             subject_type,
                             unique_predicate,
                             obj_name,
                             ana_sub_name,
                             ana_obj_name):

        temp_key = str((subject_type, unique_predicate))
        if temp_key in self.templates_dict:
            templates = self.templates_dict[temp_key]
            # TODO: select one from multiple templates
            sentence = templates[0]
            sentence = sentence.replace(self.sub_placeholder, subject_name)
            sentence = sentence.replace(self.obj_placeholder, obj_name)
            sentence = sentence.replace(self.ana_sub_placeholder, ana_sub_name)
            sentence = sentence.replace(self.ana_obj_placeholder, ana_obj_name)
            return sentence
        else:
            return ''

    # Return value is (sentence, _id_obj, obj_pop_val)
    def generate_sentence_and_entity(self, entity_id_list):

        if len(entity_id_list) < self.Alg_Requirement_Const:
            return ('', None, 0)

        entry_dict_list = []
        for _id in entity_id_list:
            entry_dict = globals.entity_warehouse_server.get_entry_by_kbid(_id)
            if entry_dict:
                entry_dict_list.append(entry_dict)

        if len(entry_dict_list) < self.Alg_Requirement_Const:
            return ('', None, 0)

        # TODO: first 3, or top 3, or random 3
        entry_dict_list.sort(key=lambda x: self.popular_value_reweight(x), reverse=True)
        # TODO: now use only top 3 through self.Alg_Requirement_Const
        entry_dict_list = entry_dict_list[:self.Alg_Requirement_Const]

        obj_name, obj_id, sub_name, ana_sub_name, ana_obj_name, sub_type, predicate, pop_val = \
            self.select_object_analogy(entry_dict_list)

        sentence = self.template_to_sentence(sub_name, sub_type, predicate, obj_name, ana_sub_name, ana_obj_name)
        
        return (sentence, obj_id, pop_val)