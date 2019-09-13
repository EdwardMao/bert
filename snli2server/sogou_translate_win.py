import requests
import codecs
import time
import sys
import os
import subprocess

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import pyperclip

def get_clipboard_data():
    p = subprocess.Popen(['pbpaste'], stdout=subprocess.PIPE)
    retcode = p.wait()
    data = p.stdout.read()
    return data.decode("utf-8")


def set_clipboard_data(data):
    p = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
    p.stdin.write(data)
    p.stdin.close()
    p.communicate()


class ChromeBrowser(object):

    def __init__(self, chromedriver_path, sleep_time):
        self.chromedriver_path = chromedriver_path
        os.environ["webdriver.chrome.driver"] = chromedriver_path
        self.browser = webdriver.Chrome(chromedriver_path)
        self.url = "https://fanyi.sogou.com/"
        self.webcontent = self.browser.get("https://fanyi.sogou.com/")
        self.sleep_time = sleep_time

    def _execute_script(self):

        self.browser.execute_script(
            '''

            //var kw = document.getElementById('sogou-translate-output');
            //alert(kw.innerText);
            //var res = kw.innerText;
            //alert(res);

            id = "sogou-translate-output"
            attr = "innerHTML";
            let target = null;

            if (attr) {
                target = document.createElement('div');
                target.id = 'tempTarget';
                target.style.opacity = '0';
                if (id) {
                    let curNode = document.querySelector('#' + id);
                    target.innerText = curNode[attr];
                } else {
                    target.innerText = attr;
                }
                document.body.appendChild(target);
            } else {
                target = document.querySelector('#' + id);
            }

            //alert(target.innerText);

            try {
                let range = document.createRange();
                range.selectNode(target);
                window.getSelection().removeAllRanges();
                window.getSelection().addRange(range);
                document.execCommand('copy');
                window.getSelection().removeAllRanges();
                //alert('复制成功')
            } catch (e) {
                //alert('复制失败')
                var fail = 1;
            }

            if (attr) {
                // remove temp target
                target.parentElement.removeChild(target);
            }
            ''')

    def translate(self, input):

        try:
            input_box = self.browser.find_element_by_id("sogou-translate-input")
            input_box.clear()
            input_box.send_keys(input)
            time.sleep(self.sleep_time)
            self._execute_script()
            return pyperclip.paste()
            return get_clipboard_data()
        except Exception:
            return None

class DataSet(object):

    def __init__(self, input_file, output_file):

        self.input_file = input_file
        self.out_file = output_file
        self.all_sentences = codecs.open(input_file, 'r', 'utf-8').read().splitlines()
        lines = codecs.open(output_file, 'r', 'utf-8').read().splitlines()
        self.exist_sentences = {}
        for line in lines:
            elems = line.split("\t")
            self.exist_sentences[elems[0]] = elems[1]
        self.current_index = 0

    def _save(self):

        f = codecs.open(self.out_file, 'w', 'utf-8')
        for sentence, response_text in self.exist_sentences.items():
            f.write(sentence + "\t" + response_text + "\n")
        f.close()

    def next_sentence(self):

        if self.current_index == len(self.all_sentences):
            return None

        while self.all_sentences[self.current_index] in self.exist_sentences:
            self.current_index += 1

        return_sentence = self.all_sentences[self.current_index]
        self.current_index += 1
        return return_sentence

    def update_exist_sentence(self, sentence, translated_sentence):

        self.exist_sentences[sentence] = translated_sentence
        self._save()

#chromedriver = sys.argv[1]
#input_file = sys.argv[2]
#output_file = sys.argv[3]
chromedriver = "C:\\Users\\v_weiqmao\\Desktop\\snli2server\\chromedriver.exe"
input_file = "C:\\Users\\v_weiqmao\\Desktop\\snli2server\\all_sentences.tsv"
output_file = "C:\\Users\\v_weiqmao\\Desktop\\snli2server\\translated_sentences.tsv"

if len(sys.argv) >= 5:
    sleep_time = int(sys.argv[4])
else:
    sleep_time = 2

if len(sys.argv) >= 6:
    wait_time = int(sys.argv[5])
else:
    wait_time = 30


crawler = ChromeBrowser(chromedriver, sleep_time)
dataset = DataSet(input_file, output_file)
has_error = False
current_sentence = ""
while True:
    if not has_error:
        current_sentence = dataset.next_sentence()
    else:
        has_error = False
    if current_sentence is not None:
        translated_text = crawler.translate(current_sentence)
        if translated_text is None:
            has_error = True
            print("sleeping due to error")
            time.sleep(wait_time)
        else:
            dataset.update_exist_sentence(current_sentence, translated_text)
    else:
        break
sys.exit()