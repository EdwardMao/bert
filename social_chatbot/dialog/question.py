import globals
import random

from commons.nlu.classifier.attitude_classifier import YesNoLabel
from commons.nlu.classifier.dialog_act_classifier import DialogActLabel
from dialog.schema import GraphBaseObj
from dialog.schema import PolicyConditions

from collections import defaultdict


class AnnotatedQuestion(GraphBaseObj):

    def __init__(self, id, question_template, policy_entity_type, policy_dict):

        super().__init__(id, self.__class__.__name__)

        self.question_template = question_template
        self.initialize(self.question_template)
        self.entity_type = policy_entity_type
        self.is_waiting_response = False
        self.policy_dict = defaultdict()
        for policy_condition, intent_id in policy_dict.items():
            self.policy_dict[PolicyConditions[policy_condition]] = intent_id
        if len(self.policy_dict) > 0:
            self.is_waiting_response = True

        pass

    def execute(self, exe_parameter):

        if len(self.samples_without_entity_slot) == 0 and len(self.samples_with_entity_slot) == 0:
            return ""

        if len(self.samples_without_entity_slot) > 0 and len(self.samples_with_entity_slot) == 0:
            return self._generate_question_from_samples_without_entity_slot()

        if len(self.samples_without_entity_slot) == 0 and len(self.samples_with_entity_slot) > 0:
            return self._generate_question_from_samples_with_entity_slot(exe_parameter)

        if len(self.samples_without_entity_slot) > 0 and len(self.samples_with_entity_slot) > 0:
            r_number = random.randint(0, 1)
            if r_number == 0 and exe_parameter.current_question_entity_id != "":
                return self._generate_question_from_samples_with_entity_slot(exe_parameter)
            else:
                return self._generate_question_from_samples_without_entity_slot()
        pass

    def can_answer_question(self, exe_parameter):

        # it seems when we decide the query is answering this question or not,
        # we need to update the entity in the query if it really answered.

        user_query = exe_parameter.user_query
        entity_candidate = self.generate_entity_candidate(user_query)

        if len(entity_candidate) > 0 and PolicyConditions.HasEntity in self.policy_dict:
            return True, self.policy_dict[PolicyConditions.HasEntity]

        if len(entity_candidate) == 0 and PolicyConditions.NoEntity in self.policy_dict:
            return True, self.policy_dict[PolicyConditions.NoEntity]

        for sentence in user_query.sentence_list:
            if sentence.yesno_result_with_confidence == YesNoLabel.Yes and \
                    sentence.dialog_act_result_with_confidence == DialogActLabel.Statement and \
                    PolicyConditions.Yes in self.policy_dict:
                # use previous entity as current entity
                exe_parameter.user_query.update_type2entity(exe_parameter.previous_question_entity_id)
                return True, self.policy_dict[PolicyConditions.Yes]

            if sentence.yesno_result_with_confidence == YesNoLabel.No and \
                    sentence.dialog_act_result_with_confidence == DialogActLabel.Statement and \
                    PolicyConditions.No in self.policy_dict:
                # TODO: found another or reverse entity of exe_parameter.previous_question_entity_id
                exe_parameter.user_query.update_type2entity(exe_parameter.previous_question_entity_id)
                return True, self.policy_dict[PolicyConditions.No]

            if sentence.yesno_result_with_confidence == YesNoLabel.Unclear and \
                    sentence.dialog_act_result_with_confidence != DialogActLabel.Question and \
                    PolicyConditions.YNUnclear in self.policy_dict:
                # assume there is no entity at current turn
                return True, self.policy_dict[PolicyConditions.YNUnclear]

        return False, ""

    def _generate_question_from_samples_without_entity_slot(self):
        return random.choice(self.samples_without_entity_slot)

    def _generate_question_from_samples_with_entity_slot(self, exe_parameter):

        current_entity_id = exe_parameter.current_question_entity_id

        if current_entity_id == "":
            log_str = "No question generated from samples_with_entity_slot due to no entity found from [%s]\n" % \
                      exe_parameter.user_query.raw_query
            self.system_logger.error(log_str)
            print(log_str)
            return ""

        entity_name = globals.entity_warehouse_server.get_random_name_by_kbid(current_entity_id)
        entity_type = globals.entity_warehouse_server.get_type_by_kbid(current_entity_id)

        for one_type in entity_type:
            entity_slot = '[' + str(one_type) + '_object]'
            random.shuffle(self.samples_with_entity_slot)
            for one_sample in self.samples_with_entity_slot:
                if one_sample.find(entity_slot) >= 0:
                    return one_sample.replace(entity_slot, entity_name)

        for one_sample in self.samples_with_entity_slot:
            if one_sample.find(self.entity_slot_base) >= 0:
                return one_sample.replace(self.entity_slot_base, entity_name)

        log_str = "No question generated from samples_with_entity_slot when entity is [%s]\n" % \
                  (str(entity_type) + "_" + current_entity_id + "_" + entity_name)
        self.system_logger.error(log_str)
        print(log_str)

        return ""
