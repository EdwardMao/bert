import io
import queue


class State(object):
    def __init__(self, depth):
        self.success = {}
        self.before = None
        self.emits = set()
        self.depth = depth

    def add_word(self, word):
        if word in self.success:
            return self.success.get(word)
        else:
            state = State(self.depth+1)
            self.success[word] = state
            return state

    def add_one_emit(self, keyword):
        self.emits.add(keyword)

    def add_emits(self, emits):
        self.emits = self.emits | emits

    def set_before(self, state):
        self.before = state

    def get_transitions(self):
        return self.success.keys()

    def next_state(self, word):
        return self.success.get(word)


class Trie(object):
    def __init__(self):
        self.root = State(0)
        self.root.set_before(self.root)
        self.is_create_before = False
        self.weights = {}

    def add_keyword(self, keyword):
        current_state = self.root
        for word in list(keyword):
            current_state = current_state.add_word(word)
        current_state.add_one_emit(keyword)

    def add_dict_word(self, words):
        for line in words:
            line = line.split('\t')
            word = line[0].strip()
            self.add_keyword(word)
            if len(line) == 1:
                self.weights[word] = 1.0 * len(word)
            else:
                self.weights[word] = float(line[1]) * len(word)

    def add_dict(self, path):
        if not path:
            return

        words = []
        with io.open(path, 'r', encoding='utf8') as f:
            for line in f:
                line = line.strip('\n').strip()
                if line:
                    line = line.split('\t')
                    word = line[0].strip()
                    self.add_keyword(word)
                    if len(line) == 1:
                        self.weights[word] = 1.0 * len(word)
                    else:
                        self.weights[word] = float(line[1]) * len(word)

    def create_before(self):
        state_queue = queue.Queue()
        for v in self.root.success.values():
            state_queue.put(v)
            v.set_before(self.root)

        while not state_queue.empty():
            current_state = state_queue.get()
            transitions = current_state.get_transitions()
            for word in transitions:
                target_state = current_state.next_state(word)
                state_queue.put(target_state)
                trace_state = current_state.before

                while trace_state.next_state(word) is None and trace_state.depth != 0:
                    trace_state = trace_state.before

                if trace_state.next_state(word) is not None:
                    target_state.set_before(trace_state.next_state(word))
                    target_state.add_emits(trace_state.next_state(word).emits)
                else:
                    target_state.set_before(trace_state)
        self.is_create_before = True

    def get_state(self, current_state, word):
        new_current_state = current_state.next_state(word)

        while new_current_state is None and current_state.depth != 0:
            current_state = current_state.before
            new_current_state = current_state.next_state(word)

        return new_current_state

    def parse_text(self, text):
        matchs = []
        if not self.is_create_before:
            self.create_before()

        position = 0
        current_state = self.root
        for word in list(text):
            position += 1
            current_state = self.get_state(current_state, word)
            if not current_state:
                current_state = self.root
                continue

            for keyword in current_state.emits:
                matchs.append((position - len(keyword), position, keyword))

        return matchs

    def cut(self, text):
        matchs = self.parse_text(text)
        return matchs

    def get_weight(self, word):
        return self.weights.get(word,1)
