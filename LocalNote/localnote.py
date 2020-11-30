import os
import json
import time
import urllib
import markdown
from markdown.extensions.fenced_code import FencedCodeExtension
from markdown.extensions.toc import TocExtension
from markdown.extensions.tables import TableExtension
# from markdown.extensions.
import html
import re
from lxml import etree
import evernote.edam.type.ttypes as Types
from evernote.edam.notestore import NoteStore
from evernote.api.client import EvernoteClient
from evernote.edam.error.ttypes import EDAMUserException
import subprocess
import argparse   
import logging

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - line:%(lineno)d - %(message)s")

def ischinese(ch):
    return '\u4e00' <= ch <= '\u9fff'

def chinese_count(s):
    # 中文字符范围
    ret = 0
    for ch in s:
        if ischinese(ch):
            ret += 1
    return ret

def pad(s, length=30):
    s= str(s)
    ret = length - chinese_count(s) - len(s)
    if ret > 0:
        s += " " * ret
    return s

def tohtml(mdtext):
    return markdown.markdown(mdtext, extensions=[FencedCodeExtension(), TableExtension()])

def timestamp2str(timestamp):
    return time.strftime(
        '%Y-%m-%d %H:%M:%S',
        time.localtime(timestamp)
    )


def create_toc_for_html(content):
    html = etree.HTML(content)
    # html.xpath("//h1/text() | //h2/text() | //h3/text() | //h4/text() | //h5/text() | //h6/text()")
    titles = html.xpath("//h1 | //h2 | //h3 | //h4 | //h5 | //h6")

    n = len(titles)
    lis = [etree.Element("li") for i in range(len(titles))]
    for i in range(len(titles)):
        a = etree.Element("a")
        a.text = titles[i].text
        a.attrib['style'] = "line-height: 160%; box-sizing: content-box; text-decoration: underline; color: #5286bc;"
        lis[i].append(a)
    # 添加一个 ul 元素。 st[-1] 会取到这个元素
    lis.append(etree.Element("ul"))

    st = [-1]
    for i in range(n + 1):
        while len(st) > 1 and (i == n or titles[st[-1]].tag >= titles[i].tag):
            idx = st.pop()
            if lis[st[-1]].tag != 'ul':
                ul = etree.Element("ul")
                ul.append(lis[st[-1]])
                lis[st[-1]] = ul
            lis[st[-1]].append(lis[idx])
        if i < len(titles): st.append(i)

    div = etree.Element("div")
    if len(lis[-1].getchildren()) == 1:
        div.append(lis[-1].getchildren()[0])
    else:
        div.append(lis[-1])
    return etree.tostring(div).decode()

def execute_cmd(cmd, **kwargs):
    completed_process = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, **kwargs)
    return completed_process.stdout.decode().strip()

def strip_control_characters(s):
    return re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1F\x7F]", "", s) 

def nbconvert(filename):
    cmd = 'jupyter nbconvert --to markdown --stdout "{}"'.format(filename)
    content = execute_cmd(cmd)
    return content


class Config:

    def __init__(self, path):
        self.path = path
        if os.path.exists(self.path):
            with open(self.path, encoding='utf8') as f:
                self.config = json.load(f)
        else:
            self.config = {}

    def get(self, key):
        return self.config.get(key, None)

    def add(self, key, val):
        self.config[key] = val
        with open(self.path, 'w', encoding='utf8') as f:
            json.dump(self.config, f)


class Client:
    def __init__(self):
        config = Config("config.json")
        developer_token = config.get('developer_token')

        while True:
            # Set up the NoteStore client
            if developer_token is None:
                print("You don't have a develop token! Please ask at https://app.yinxiang.com/api/DeveloperToken.action")
                developer_token = input("Input your token: ")
            try:
                self.client = EvernoteClient(token=developer_token, china=True ,sandbox=False)
                self.notestore = self.client.get_note_store()
            except EDAMUserException as e:
                print("Your develop token has been expired! Please ask at https://app.yinxiang.com/api/DeveloperToken.action")
                developer_token = input("Input your new token: ")
            else:
                break
        config.add('developer_token', developer_token)


    def make_markdown_content(self, content):

        def add_text_tag(matched):

            def add_text(matched):
                s = matched.group(0)
                return r'\text{{{}}}'.format(s)

            latex_content = matched.group(1)
            return "$${}$$".format(re.sub(r"[\u4e00-\u9fff]{1,}", add_text, latex_content))

        pattern = re.compile("\$\$(.*?)\$\$", re.DOTALL)
        content = re.sub(pattern, add_text_tag, content)
        markdowncontent = urllib.parse.quote(content)

        content = re.sub(r"```(.*?)\n", "```\n", content)
        content = re.sub(r'\[toc\]', "", content)

        normalcontent = tohtml(content)
        style = '<code style=\"display: block; overflow-x: auto; background: #1e1e1e; line-height: 160%; box-sizing: content-box; border: 0; border-radius: 0; letter-spacing: -.3px; padding: 18px; color: #f4f4f4; white-space: pre-wrap;\">'
        normalcontent = re.sub("<code.*?>", style, normalcontent)
        toc = create_toc_for_html(normalcontent)
        normalcontent = toc + normalcontent
        ret = '<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/enml2.dtd">'
        ret += '<en-note><div>{normalcontent}</div><center style="display:none !important;visibility:collapse !important;height:0 !important;white-space:nowrap;width:100%;overflow:hidden">{markdowncontent}</center></en-note>'.format(normalcontent=normalcontent, markdowncontent=markdowncontent)
        return ret

    def get_note_detail(self, guid):
        fullnote = self.notestore.getNote(guid, True, True, True, True)
        return fullnote

    def get_note(self, content, title):
        note = Types.Note()
        note.title = title.strip()
        note.content = self.make_markdown_content(content)
        return note

    def create_note(self, title, content):
        note = self.get_note(content, title)
        note.attributes = Types.NoteAttributes(contentClass='yinxiang.markdown', source='localnote')
        note = self.notestore.createNote(note)
        logging.debug("note's title: {} note's guid: {}".format(note.title, note.guid))

    def find_by_title(self, title):
        note_filter = NoteStore.NoteFilter()
        note_filter.words = title
        notes = self.notestore.findNotes(note_filter, 0, 10).notes
        return notes

    def update_note(self, note, title, content):
        newnote = self.get_note(content, title)
        newnote.guid = note.guid
        newnote.attributes = Types.NoteAttributes(contentClass='yinxiang.markdown', source='localnote')
        newnote = self.notestore.updateNote(newnote)
        logging.debug("updated note's title: {} updated note's guid: {}".format(newnote.title, newnote.guid))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", type=str)
    parser.add_argument("filename", type=str)

    args = parser.parse_args()

    client = Client()
    _, filetype = os.path.splitext(args.filename)
    title = os.path.splitext(os.path.basename(args.filename))[0]
    if filetype == '.md':
        with open(args.filename, encoding='utf8') as f:
            content = f.read()
    elif filetype == '.ipynb':
        content = nbconvert(args.filename)
    else:
        raise Exception("Unsupported filetype: {}".format(filetype))

    content = strip_control_characters(content)
    logging.debug("filename: {} content: {}".format(args.filename, content))

    if args.mode == 'add':
        client.create_note(title, content)
        print("create note: {} SUCCESS!".format(title))
    elif args.mode == 'update':
        notes = client.find_by_title(title)
        if notes:
            print("There are {} notes similar with {}, they are: ".format(len(notes), args.filename))
            for i, note in enumerate(notes):
                print("{no:<5}{title}created:{created}last updated:{updated}".format(
                    no=str(i) + ".", 
                    title=pad(note.title, 40),
                    created=pad(timestamp2str(note.created)),
                    updated=pad(timestamp2str(note.updated)))
                )
            answer = input("Choose one to update. Input 'n' to quit: ")
            print("Input: {}".format(answer))
            if answer.isdigit():
                i = int(answer)
                note = notes[i]
                client.update_note(note, title, content)
            else:
                print("Skip!")
        else:
            print("No similar note called {} was found!".format(title))
    else:
        raise Exception("Unsupported mode: {}".format(args.mode))

if __name__ == "__main__":
    main()
