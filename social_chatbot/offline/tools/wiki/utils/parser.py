import os
import re
import logging


logger = logging.getLogger()


class Parser(object):
    def __init__(self, lang):
        self.inits = {
            'unitok': self.unitok_init,
            'en': self.moses_init,
            'en_spacy': self.spacy_init,
            'zh': self.zh_init,
            'gan': self.zh_init,
            'wuu': self.zh_init,
            'zh-yue': self.zh_init,
            'zh-classical': self.zh_init,
            'zh_ltp': self.ltp_init,
        }
        self.lang = lang

        logger.info('language: %s' % self.lang)
        if self.lang not in self.inits:
            logger.info('initializing model: unitok')
            self.inits['unitok']()
        else:
            logger.info('initializing model: %s' % self.lang)
            self.inits[self.lang]()
        logger.info('done.')

    def _parse(self, text, index=0):
        sents = []
        index = index
        para_count = 0
        for para in re.split('\n\s*\n', text):
            if not para:
                continue
            for line in para.split('\n'):
                if not line:
                    continue
                for sent in self.sent_seger(line):
                    if self.processor:
                        r = self.processor(sent.replace('_', ' '))
                        toked_sent, processed_res = r
                    else:
                        toked_sent = self.tokenizer(sent.replace('_', ' '))
                        processed_res = {}
                    start = text.index(sent, index)
                    end = start + len(sent)
                    index = end
                    sents.append({
                        'tokens': toked_sent,
                        'start': start,
                        'end': end,
                        'results': processed_res,
                        'paragraph_index': para_count
                    })
            para_count += 1
        return sents

    # Moses
    def moses_init(self):
        from nltk.tokenize.moses import MosesTokenizer
        from nltk.tokenize import sent_tokenize
        self.model_punkt = sent_tokenize
        self.model_moses = MosesTokenizer(self.lang)

        self.parse = self._parse
        self.sent_seger = self.punkt_sent_seger
        self.tokenizer = self.moses_tokenizer
        self.processor = None

    def punkt_sent_seger(self, text):
        return self.model_punkt(text)

    def moses_tokenizer(self, text, shift=0):
        toked_sent = []
        index = 0
        for tok in self.model_moses.tokenize(text, escape=False):
            if tok.strip() == '':
                index += len(tok)
                continue
            tok_start = text.index(tok, index)
            tok_end = tok_start + len(tok)
            toked_sent.append((tok, (tok_start+shift, tok_end+shift)))
            index = tok_end
        return toked_sent

    # Unitok
    def unitok_init(self):
        from nltk.tokenize import sent_tokenize
        self.model_punkt = sent_tokenize
        from utils import unitok
        self.model = unitok.unitok_tokenize

        self.parse = self._parse
        self.sent_seger = self.punkt_sent_seger
        self.tokenizer = self.unitok_tokenizer
        self.processor = None

    def unitok_tokenizer(self, text, shift=0):
        toked_sent = []
        index = 0
        for tok in self.model(text):
            if tok.strip() == '':
                index += len(tok)
                continue
            tok_start = text.index(tok, index)
            tok_end = tok_start + len(tok)
            toked_sent.append((tok, (tok_start+shift, tok_end+shift)))
            index = tok_end
        return toked_sent

    # Chinese
    def zh_init(self):
        import jieba
        jieba.initialize()
        self.model_jieba = jieba

        self.parse = self._parse
        self.sent_seger = self.zh_sent_seger
        self.tokenizer = self.zh_tokenizer
        self.processor = None

    def zh_sent_seger(self, text):
        """
        use Chinese punctuation as delimiter
        :param text:
        :return:
        """
        res = []
        sent_end_char = [u'。', u'！', u'？']
        current_sent = ''
        for i, char in enumerate(list(text)):
            if char in sent_end_char or i == len(list(text)) - 1:
                res.append(current_sent + char)
                current_sent = ''
            else:
                current_sent += char

        return [item.strip() for item in res]

    def zh_tokenizer(self, text, shift=0):
        toked_sent = []
        index = 0
        for tok in self.model_jieba.cut(text):
            if tok.strip() == '':
                index += len(tok)
                continue
            tok_start = text.index(tok, index)
            tok_end = tok_start + len(tok)
            toked_sent.append((tok, (tok_start+shift, tok_end+shift)))
            index = tok_end
        return toked_sent

    # Spacy (English)
    def spacy_init(self):
        import spacy
        self.model = spacy.load('en')

        self.parse = self._parse
        self.sent_seger = self.spacy_sent_seger
        self.tokenizer = self.spacy_tokenizer
        self.processor = self.spacy_processor

    def spacy_sent_seger(self, text):
        return [s.text for s in self.model(text).sents]

    def spacy_tokenizer(self, text, shift=0):
        toked_sent = []
        for t in self.model.tokenizer(text):
            if t.text.strip() == '':
                continue
            toked_sent.append((t.text, (t.idx+shift, t.idx+len(t)+shift)))
        return toked_sent

    def spacy_processor(self, text, shift=0):
        toked_sent = []
        processed_res = {}
        doc_obj = self.model(text)
        for t in doc_obj:
            if t.text.strip() == '':
                continue
            toked_sent.append((t.text, (t.idx+shift, t.idx+len(t)+shift)))
        processed_res['tree'] = doc_obj.print_tree()
        ner = []
        for i in doc_obj.ents:
            assert text[i.start_char:i.end_char] == i.text
            ner.append({
                'text': i.text,
                'offset': (i.start_char, i.end_char),
                'label': i.label_
            })
        processed_res['ner'] = ner
        return toked_sent, processed_res

    # LTP (Chinese)
    def ltp_init(self):
        import pyltp
        LTP_DATA_DIR = '/nas/data/m1/panx2/lib/ltp/ltp_data_v3.4.0'
        cws_model_path = os.path.join(LTP_DATA_DIR, 'cws.model')
        pos_model_path = os.path.join(LTP_DATA_DIR, 'pos.model')
        ner_model_path = os.path.join(LTP_DATA_DIR, 'ner.model')
        par_model_path = os.path.join(LTP_DATA_DIR, 'parser.model')

        self.model_ltp_splitter = pyltp.SentenceSplitter()
        self.model_ltp_segmentor = pyltp.Segmentor()
        self.model_ltp_segmentor.load(cws_model_path)
        self.model_ltp_postagger = pyltp.Postagger()
        self.model_ltp_postagger.load(pos_model_path)
        self.model_ltp_recognizer = pyltp.NamedEntityRecognizer()
        self.model_ltp_recognizer.load(ner_model_path)
        self.model_ltp_dparser = pyltp.Parser()
        self.model_ltp_dparser.load(par_model_path)

        self.parse = self._parse
        self.sent_seger = self.ltp_sent_seger
        self.tokenizer = self.ltp_tokenizer
        self.processor = self.ltp_processor

    def ltp_sent_seger(self, text):
        return [s for s in self.model_ltp_splitter.split(text)]

    def ltp_tokenizer(self, text, shift=0):
        # ltp cannot handle whitespace
        whitespaces = [' ', '\t', '\u3000']
        for ws in whitespaces:
            text = text.replace(ws, '，')

        toked_sent = []
        index = 0
        for tok in self.model_ltp_segmentor.segment(text):
            if tok.strip() == '':
                index += len(tok)
                continue
            tok_start = text.index(tok, index)
            tok_end = tok_start + len(tok)
            toked_sent.append((tok, (tok_start+shift, tok_end+shift)))
            index = tok_end
        return toked_sent

    def ltp_processor(self, text, shift=0):
        # ltp cannot handle whitespace
        whitespaces = [' ', '\t', '\u3000']
        for ws in whitespaces:
            text = text.replace(ws, '，')

        toked_sent = []
        index = 0
        tokens = self.model_ltp_segmentor.segment(text)
        for tok in tokens:
            if tok.strip() == '':
                index += len(tok)
                continue
            tok_start = text.index(tok, index)
            tok_end = tok_start + len(tok)
            toked_sent.append((tok, (tok_start+shift, tok_end+shift)))
            index = tok_end

        processed_res = {}
        postags = [p for p in self.model_ltp_postagger.postag(tokens)]
        netags = [n for n in self.model_ltp_recognizer.recognize(tokens,
                                                                 postags)]
        arcs = [(a.head, a.relation) \
                for a in self.model_ltp_dparser.parse(tokens, postags)]

        processed_res['pos'] = postags
        processed_res['ner'] = netags
        processed_res['arc'] = arcs

        return toked_sent, processed_res
