from enum import Enum

from commons.entity.extension.one_order_extension import EntityOneOrderExtensionFromKG
from commons.entity.extension.two_order_extension import EntityTwoOrderExtensionFromKG
from commons.entity.extension.analogy_extension import EntityAnalogyExtensionFromKG


class EntityExtensionStatus(Enum):

    Initial = 1
    ExtensionFailure = 2
    OneOrderOneEntity = 3
    OneOrderZeroEntity = 4
    TwoOrderTwoEntity = 5
    TwoOrderOneEntity = 6
    TwoOrderZeroEntity = 7
    AnalogyOneEntity = 8
    AnalogyZeroEntity = 9


class EntityExtensionOutput(object):

    def __init__(self, name, input_id_list):

        self.name = name
        self.sentence = ''
        self.input_id_list = input_id_list.copy()
        self.executed_id_list = input_id_list.copy()
        self.extended_id_list = []
        self.pop_val = 0
        self.status = EntityExtensionStatus.Initial
        self.index = ""

    def to_json(self):
        return {
            "extension_type": self.name,
            "extension_sentence": self.sentence,
            "input_id_list": self.input_id_list,
            "extended_id_list": self.extended_id_list,
            "status": self.status.name
        }


class EntityExtensionWrapper(object):

    def __init__(self, configure):

        self.one_order_extension_module = EntityOneOrderExtensionFromKG(configure)
        self.two_order_extension_module = EntityTwoOrderExtensionFromKG(configure)
        self.analogy_extension_module = EntityAnalogyExtensionFromKG(configure)

    # entity_id_list: can be a list of _id, or one string of _id
    # module = '1': one order; module = '2': two order
    def generate_sentence_and_entity_call(self, entity_id_list, module = '2'):

        sel_module = str(module)
        result = EntityExtensionOutput('Module_' + sel_module, entity_id_list)

        if entity_id_list:

            if sel_module == '1':
                # TODO: now use the first entity
                sentence, _id_obj, pop_val = \
                    self.one_order_extension_module.generate_sentence_and_entity(entity_id_list[0])
                result.sentence = sentence
                if _id_obj:
                    result.extended_id_list.append(_id_obj)
                result.pop_val = pop_val

                if not sentence:
                    result.status = EntityExtensionStatus.ExtensionFailure
                elif not result.extended_id_list:
                    result.status = EntityExtensionStatus.OneOrderZeroEntity
                else:
                    result.status = EntityExtensionStatus.OneOrderOneEntity

            elif sel_module == '3':
                sentence, _id_obj, pop_val = \
                    self.analogy_extension_module.generate_sentence_and_entity(entity_id_list)
                result.sentence = sentence
                if _id_obj:
                    result.extended_id_list.append(_id_obj)
                result.pop_val = pop_val

                if not sentence:
                    result.status = EntityExtensionStatus.ExtensionFailure
                elif not result.extended_id_list:
                    result.status = EntityExtensionStatus.AnalogyZeroEntity
                else:
                    result.status = EntityExtensionStatus.AnalogyOneEntity

            else:  # Use '2' by default
                # TODO: now use the first entity
                sentence, _id_obj_a, _id_obj_b, pop_val = \
                    self.two_order_extension_module.generate_sentence_and_entity(entity_id_list[0])
                result.sentence = sentence
                if _id_obj_a:
                    result.extended_id_list.append(_id_obj_a)
                if _id_obj_b:
                    result.extended_id_list.append(_id_obj_b)
                result.pop_val = pop_val

                if not sentence:
                    result.status = EntityExtensionStatus.ExtensionFailure
                elif not result.extended_id_list:
                    result.status = EntityExtensionStatus.TwoOrderZeroEntity
                elif len(result.extended_id_list) == 1:
                    result.status = EntityExtensionStatus.TwoOrderOneEntity
                else:
                    result.status = EntityExtensionStatus.TwoOrderTwoEntity

        else:
            result.status = EntityExtensionStatus.ExtensionFailure

        return result

    def generate_sentence_and_entity(self, entity_id_list, module = '0'):
        sel_module = str(module)

        if sel_module == '1' or sel_module == '2' or sel_module == '3':
            return self.generate_sentence_and_entity_call(entity_id_list, sel_module)
        else:
            result = self.generate_sentence_and_entity_call(entity_id_list, '2')
            if result.status == EntityExtensionStatus.ExtensionFailure:
                return self.generate_sentence_and_entity_call(entity_id_list, '1')
            else:
                return result
