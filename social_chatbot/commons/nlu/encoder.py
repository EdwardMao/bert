
class Encoder(object):
    def __init__(self, lang):
        self.encoders = {
            'zh': self.to_simplified,
            'zh-classical': self.to_simplified,
        }
        self.lang = lang
        if self.lang in ['zh', 'zh-classical']:
            import zhconv
            self.convert = zhconv.convert

    def encoding(self, text):
        if self.lang in self.encoders:
            return self.encoders[self.lang](text)
        else:
            return text

    def to_simplified(self, text):
        return self.convert(text, 'zh-cn')
