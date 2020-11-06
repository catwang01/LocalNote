import os
import urllib
import html
import re
import evernote.edam.type.ttypes as Types
from evernote.edam.notestore import NoteStore
from evernote.api.client import EvernoteClient
import subprocess
import argparse   
import logging

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - line:%(lineno)d - %(message)s")

def execute_cmd(cmd, **kwargs):
    completed_process = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, **kwargs)
    return completed_process.stdout.decode().strip()

def nbconvert(filename):
    cmd = "jupyter nbconvert --to markdown --stdout {}".format(filename)
    content = execute_cmd(cmd)
    logging.debug("filename: {} content: {}".format(filename, content))
    return content

class Client:
    def __init__(self):
        developer_token = 'S=s54:U=157132c:E=175bc7ccef9:C=17598704928:P=1cd:A=en-devtoken:V=2:H=9695fda68b52d26fa24b2956f2924bb9'
        # Set up the NoteStore client
        self.client = EvernoteClient(token=developer_token, china=True ,sandbox=False)
        self.notestore = self.client.get_note_store()

    def create_note(self, title, content):
        quoted_content = urllib.parse.quote(content)
        newnote = Types.Note()
        newnote.title = title
        newnote.content = '<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/enml2.dtd">'
        newnote.content += '<en-note><div>{}</div><center>{}</center></en-note>'.format(html.escape(content), quoted_content)
        newnote.attributes = Types.NoteAttributes(contentClass='yinxiang.markdown')
        newnote = self.notestore.createNote(newnote)
        logging.debug("newnote's title: {} newnote's guid: {}".format(newnote.title, newnote.guid))


    def find_by_title(self, title):
        note_filter = NoteStore.NoteFilter()
        note_filter.words = "intitle:{}".format(title)
        notes = self.notestore.findNotes(note_filter, 0, 10).notes
        for note in notes:
            if note.title == title:
                return note
        return None

    def update_note(self, note, title, content):
        quoted_content = urllib.parse.quote(content)
        newnote = Types.Note()
        newnote.title = title
        newnote.content = '<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/enml2.dtd">'
        newnote.content += '<en-note><div>{}</div><center>{}</center></en-note>'.format(html.escape(content), quoted_content)
        newnote.guid = note.guid
        newnote = self.notestore.updateNote(newnote)
        logging.debug("updated note's title: {} updated note's guid: {}".format(newnote.title, newnote.guid))

        
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", type=str)
    parser.add_argument("filename", type=str)

    args = parser.parse_args()

    client = Client()
    title, filetype = args.filename.split('.')
    if filetype == 'md':
        with open(args.filename) as f:
            content = f.read()
    elif filetype == 'ipynb':
        content = nbconvert(args.filename)
    else:
        raise Exception("Unsupported filetype: {}".format(filetype))

    strip_control_characters = lambda s:"".join(i  for i in s if ord(i)!=27)
    content = strip_control_characters(content)
    logging.debug("content: {}".format(content))

    if args.mode == 'add':
        client.create_note(title, content)
        logging.info("create note: {} SUCCESS!".format(title))
    elif args.mode == 'update':
        note = client.find_by_title(title)
        if note:
            answer = input("Do you want to update note: {}? [y/n]".format(node.title))
            if answer == 'y':
                client.update_note(note, title, content)
                logging.info("Note {} has been udpated! SUCCESS".format(note.title))
            else:
                logging.info("Skip!")
    else:
        raise Exception("Unsupported mode: {}".format(args.mode))

if __name__ == "__main__":
    main()
