from enum import Enum
import numpy as np
import re
from commons.nlu.classifier.classifier import BaseClassifier

class EmotionLabel(Enum):

    快乐 = 0 # Happy
    安心 = 1 # At Ease
    得意 = 2 # Complacent
    赞扬 = 3 # Praise
    尊敬 = 4 # Respect
    喜爱 = 5 # Fond
    相信 = 6 # Believe
    祝愿 = 7 # Wish
    愿意 = 8 # Willing
    振奋 = 9 # Aroused
    无愧 = 10 # Deserved
    感动感激 = 11 # Moved
    佩服 = 12 # Admire
    豪迈 = 13 # Heroic
    庄重 = 14 # Solemn
    满意 = 15 # Content
    亲切 = 16 # Kind
    愤怒 = 17 # Angry
    激动 = 18 # Excited
    着急 = 19 # Anxious
    悲伤 = 20 # Sad
    疚 = 21 # Guilty
    思 = 22 # Miss
    失望 = 23 # Disappointed
    哭泣 = 24 # Weeping
    委屈 = 25 # Wronged
    痛苦 = 26 # Suffering
    恐惧 = 27 # Afraid
    慌 = 28 # Panic
    羞 = 29 # Shy
    惊奇 = 30 # Surprised
    镇定 = 31 # Calm
    贬责 = 32 # Blame
    烦闷 = 33 # Anguish
    憎恶 = 34 # Hatred
    妒忌 = 35 # Jealous
    鄙视 = 36 # Contempt
    怀疑 = 37 # Suspicious
    漠视 = 38 # Indifferent
    不满不安 = 39 # Uneasy

class CoarseEmotionLabel(Enum):

    乐 = 0
    好 = 1
    怒 = 2
    哀 = 3
    惧 = 4
    恶 = 5
    惊 = 6

class EmotionClassifier(BaseClassifier):

    def __init__(self, emotion_classifier_configure):

        super().__init__()
        self.data_root = emotion_classifier_configure.data_root
        self.keywords_path = self.data_root + "/emotion_words.npy"
        self.keywords = np.load(self.keywords_path, allow_pickle=True).item() # Example: {"keyword":[[emotion0, coarse_emotion0, degree0, polarity0], [...], ...]}

    def classify(self, query):

        keywords_spotted = []
        for sentence in query.sentence_list:
            for token in sentence.token_list:
                if token.original_text in self.keywords:
                    keywords_spotted.append(token.original_text)

            sentence.emotion_keywords = keywords_spotted
            for keyword in keywords_spotted:
                emotion_set = self.keywords[keyword]
                for emotion in emotion_set:
                    sentence.emotion.append(EmotionLabel[emotion[0]])
                    sentence.coarse_emotion.append(CoarseEmotionLabel[emotion[1]])
                    sentence.emotion_degree.append(emotion[2])
                    sentence.emotion_polarity.append(emotion[3])