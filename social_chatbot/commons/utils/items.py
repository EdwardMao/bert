class ScoredItem(object):

    def __init__(self, item_id, item_type, item_score):

        self.item_id = item_id
        self.item_type = item_type
        self.item_score = item_score

    def __repr__(self):
        return "({}, {}, {})".format(self.item_id, self.item_type, self.item_score)

    def to_json(self):
        return {
            "item_id": self.item_id,
            "item_type": self.item_type,
            "item_score": self.item_score
        }