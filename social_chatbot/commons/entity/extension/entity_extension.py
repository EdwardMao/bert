from abc import ABCMeta, abstractmethod
import random

import globals
from commons.utils import check_contain_chinese


class EntityExtension(object):

    def __init__(self, name, focus_type_list):

        self.name = name
        self.focus_type_list = focus_type_list

        pass

    # For list, index = 0 finds the content, index = 1 finds the _id directly
    # For dict, index = 0 translates to 'name', index = 1 translates to '_id'
    # index should be 0 or 1
    def switch_list_dict(self, item, index):
        if isinstance(item, dict):
            if index == 1 and '__id' in item:
                return item['__id']
            elif index == 0 and 'name' in item:
                return item['name']
            else:
                return None
        else:
            return item[index]

    def check_type(self, var_dict, type_str):
        if not type_str:  # no requirement
            return True
        elif 'type' not in var_dict:
            return False

        for item in var_dict['type']:
            if self.switch_list_dict(item, 0) == type_str:
                return True
        return False

    # TODO: Raw. Need upgrade.
    def trim_unstructured_text(self, text):
        res = text
        if '。' in res:
            res = res.split('。')[0]
        if '.' in res:
            res = res.split('.')[0]
        if '，' in res:
            res = res.split('，')[0]
        if ',' in res:
            res = res.split(',')[0]
        if '（' in res:
            res = res.split('（')[0]
        if '(' in res:
            res = res.split('(')[0]

        return res

    # Use only top k (k>=0) from the selected alias set. If k=0, no alias.
    def get_random_name(self, var_dict, k):
        candidate_names = [self.switch_list_dict(var_dict['name'][0], 0)]
        if "精选别名" in var_dict:
            for item in var_dict["精选别名"][:k]:
                name_candidate = self.switch_list_dict(item, 0)
                if check_contain_chinese(name_candidate):
                    candidate_names.append(name_candidate)

        return random.choice(candidate_names)

    def popular_value_reweight(self, var_dict):
        pop_val = 0
        if 'popular' in var_dict:
            pop_val = self.switch_list_dict(var_dict['popular'][0], 0)

            # Reduce pop_val if its type is not in the selected set.
            reweight = True
            if 'type' in var_dict:
                for item in var_dict['type']:
                    if self.switch_list_dict(item, 0) in self.focus_type_list:
                        reweight = False
                        break

            if reweight:
                pop_val = int(float(pop_val) * 0.1) - 50

        return pop_val

    def copy_accessed_entity_id(self, accessed_item_list):
        id_list = []
        for obj in accessed_item_list:
            if self.switch_list_dict(obj, 1):  # with _id information
                id_list.append(self.switch_list_dict(obj, 1))

        return id_list

    def search_accessed_entity_id(self, accessed_item_list):
        id_list = []
        for obj in accessed_item_list:
            search_res = globals.entity_warehouse_server.get_entry_by_name(self.switch_list_dict(obj, 0))
            if search_res:
                for response in search_res:
                    id_list.append(response[0])

        return id_list

    # Return value is (obj_name, _id, pop_val)
    def select_object(self, subject, predicate, object_type_requirement):
        if predicate not in subject:
            return (None, None, 0)

        accessed_item_list = subject[predicate]
        if not accessed_item_list:
            return (None, None, 0)

        id_list = self.copy_accessed_entity_id(accessed_item_list)

        if not id_list:
            if not object_type_requirement:
                # TODO: 1. Post-processing in the sentence; 2. Now only use the first element
                return (self.trim_unstructured_text(self.switch_list_dict(accessed_item_list[0], 0)), None, 0)

            else:  # do search only when object type is required and _id is not copied
                id_list = self.search_accessed_entity_id(accessed_item_list)

        id_sel = []
        for _id in id_list:
            obj_dict = globals.entity_warehouse_server.get_entry_by_kbid(_id)
            if obj_dict:
                if self.check_type(obj_dict, object_type_requirement):
                    obj_name = self.get_random_name(obj_dict, self.alias_top_k)
                    pop_val = self.popular_value_reweight(obj_dict)
                    id_sel.append((obj_name, _id, pop_val))

        if id_sel:
            id_sel.sort(key=lambda x: x[-1], reverse=True)
            return random.choice(id_sel[:self.candidate_top_k])
        else:
            return (None, None, 0)

    @abstractmethod
    def generate_sentence_and_entity(self, entity_id):
        pass
