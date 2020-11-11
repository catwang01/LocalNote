import os
import time
import urllib
import markdown
from markdown.extensions.fenced_code import FencedCodeExtension
import html
import re
import evernote.edam.type.ttypes as Types
from evernote.edam.notestore import NoteStore
from evernote.api.client import EvernoteClient
import subprocess
import argparse   
import logging

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - line:%(lineno)d - %(message)s")

def chinese_count(s):
    # 中文字符范围
    ret = 0
    for ch in s:
        if '\u4e00' <= ch <= '\u9fff':
            ret += 1
    return ret

def pad(s, length=30):
    s= str(s)
    ret = length - chinese_count(s) - len(s)
    if ret > 0:
        s += " " * ret
    return s

def tohtml(mdtext):
    return markdown.markdown(mdtext, extensions=[FencedCodeExtension()])


def timestamp2str(timestamp):
    return time.strftime(
        '%Y-%m-%d %H:%M:%S',
        time.localtime(timestamp)
    )

def execute_cmd(cmd, **kwargs):
    completed_process = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, **kwargs)
    return completed_process.stdout.decode().strip()

def strip_control_characters(s):
    return re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1F\x7F]", "", s) 

def nbconvert(filename):
    cmd = 'jupyter nbconvert --to markdown --stdout "{}"'.format(filename)
    content = execute_cmd(cmd)
    return content

class Client:
    def __init__(self):
        developer_token = 'S=s54:U=157132c:E=175bc7ccef9:C=17598704928:P=1cd:A=en-devtoken:V=2:H=9695fda68b52d26fa24b2956f2924bb9'
        # Set up the NoteStore client
        self.client = EvernoteClient(token=developer_token, china=True ,sandbox=False)
        self.notestore = self.client.get_note_store()

    def make_markdown_content(self, content):
        markdowncontent = urllib.parse.quote(content)
        normalcontent = tohtml(content)
        style = 'style=\"display: block; overflow-x: auto; background: #1e1e1e; line-height: 160%; box-sizing: content-box; border: 0; border-radius: 0; letter-spacing: -.3px; padding: 18px; color: #f4f4f4; white-space: pre-wrap;\"'
        normalcontent = re.sub("class=\".*?\"", style, normalcontent)
        ret = '<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/enml2.dtd">'
        ret += '<en-note><div>{normalcontent}</div><center>{markdowncontent}</center></en-note>'.format(normalcontent=normalcontent, markdowncontent=markdowncontent)
        return ret

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
                print("Note {} has been updated! SUCCESS".format(note.title))
            else:
                print("Skip!")
        else:
            print("No similar note called {} was found!".format(title))
    else:
        raise Exception("Unsupported mode: {}".format(args.mode))

if __name__ == "__main__":
    main()
