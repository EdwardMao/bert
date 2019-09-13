from commons.knowledge_graph.internal_kg_api import InternalKGAPI


class Answer(object):

    def __init__(self,
                 is_an_answer,
                 score=0,
                 answer_id="",
                 answer_abstract="",
                 answer_prop="",
                 question_related_entity="",
                 result_str=""):

        self.is_an_answer = is_an_answer
        self.score = score
        self.answer_id = answer_id
        self.answer_abstract = answer_abstract
        self.answer_prop = answer_prop
        self.question_related_entity = question_related_entity
        self.result_str = result_str

    def to_json(self):

        return {
            "answer_id":self.answer_id,
            "answer_abstract": self.answer_abstract,
            "answer_prop": self.answer_prop,
            "question_related_entity": self.question_related_entity,
            "result_str": self.result_str,
            "score": self.score
        }


class QAServer(object):

    def __init__(self, qa_configure):

        self.qa_core = InternalKGAPI(True)
        self.threshold_value = qa_configure.threshold_value
        self.turn_on = qa_configure.turn_on

    def qa_retrieve(self, question):

        answer_dict = self.qa_core.qa_retrieve(question)
        if len(answer_dict) == 0:
            return Answer(False)

        if "score" not in answer_dict:
            return Answer(False)

        score = float(answer_dict["score"][0])
        if score < self.threshold_value:
            return Answer(False)

        answer_id = ""
        if "answer_id" in answer_dict:
            answer_id = answer_dict["answer_id"][0][0]

        answer_abstract = ""
        if "abstract" in answer_dict:
            answer_abstract = answer_dict["abstract"][0]

        answer_prop = ""
        if "answer_prop" in answer_dict:
            answer_prop = answer_dict["answer_prop"][0]

        question_related_entity = ""
        if "entity_name" in answer_dict:
            question_related_entity = answer_dict["entity_name"][0]

        result_str = ""
        if "result" in answer_dict:
            result_str = answer_dict["result"][0]

        return Answer(True,
                      score=score,
                      answer_id=answer_id,
                      answer_abstract=answer_abstract,
                      answer_prop=answer_prop,
                      question_related_entity=question_related_entity,
                      result_str=result_str
                      )




