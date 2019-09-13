import globals
import random
from dialog.schema import GraphBaseObj
from collections import defaultdict


class IntentGrounding(GraphBaseObj):

    def __init__(self, id, grounding_entity_type, template):
        super().__init__(id, self.__class__.__name__)
        self.id = id
        self.grounding_template = template
        self.entity_type = grounding_entity_type
        self.initialize(self.grounding_template)
        pass

    def execute(self, exe_parameter):

        if len(self.samples_without_entity_slot) == 0 and len(self.samples_with_entity_slot) == 0:
            return ""

        if len(self.samples_without_entity_slot) > 0 and len(self.samples_with_entity_slot) == 0:
            return self._generate_grounding_from_samples_without_entity_slot()

        if len(self.samples_without_entity_slot) == 0 and len(self.samples_with_entity_slot) > 0:
            return self._generate_grounding_from_samples_with_entity_slot(exe_parameter)

        if len(self.samples_without_entity_slot) > 0 and len(self.samples_with_entity_slot) > 0:
            r_number = random.randint(0, 1)
            if r_number == 0:
                return self._generate_grounding_from_samples_without_entity_slot()
            else:
                return self._generate_grounding_from_samples_with_entity_slot(exe_parameter)
        pass

    def _generate_grounding_from_samples_without_entity_slot(self):
        return random.choice(self.samples_without_entity_slot)

    def _generate_grounding_from_samples_with_entity_slot(self, exe_parameter):

        random_entity_id, random_entity_type, entity_random_name = \
            self._random_select_execute_entity_candidate(exe_parameter.user_query)

        if random_entity_id is None:
            log_str = "No grounding generated from samples_with_entity_slot due to no entity found from [%s]\n" % \
                      exe_parameter.user_query.raw_query
            self.system_logger.error(log_str)
            print(log_str)
            return ""

        entity_slot = '[' + str(random_entity_type) + '_object]'
        random.shuffle(self.samples_with_entity_slot)
        for one_sample in self.samples_with_entity_slot:
            if one_sample.find(entity_slot) >= 0:
                exe_parameter.current_grounding_entity_id = random_entity_id
                return one_sample.replace(entity_slot, entity_random_name)

        for one_sample in self.samples_with_entity_slot:
            if one_sample.find(self.entity_slot_base) >= 0:
                exe_parameter.current_grounding_entity_id = random_entity_id
                return one_sample.replace(self.entity_slot_base, entity_random_name)

        log_str = "No grounding generated from samples_with_entity_slot when random entity is [%s]\n" % \
                  (str(random_entity_type) + "_" + random_entity_id + "_" + entity_random_name)
        self.system_logger.error(log_str)
        print(log_str)

        return ""
