# coding=utf8
from urllib.parse import unquote
from .storage import RemoteStorage
from urllib.parse import quote
from evernote.api.client import EvernoteClient
import sys, hashlib, re, time, mimetypes
from lxml import etree
import os
sys.path.append(os.path.dirname(__file__))
import evernote.edam.type.ttypes as Types
from evernote.edam.notestore import NoteStore
from evernote.edam.error.ttypes import EDAMUserException


class EvernoteController(object):
    def __init__(self, token, isSpecialToken=False, sandbox=False, isInternational=False, notebooks=None):
        self.token = token
        ischina = not isInternational
        self.client = EvernoteClient(token=self.token, china=ischina, sandbox=sandbox)
        self.isSpecialToken = isSpecialToken
        self.userStore = self.client.get_user_store()
        self.noteStore = self.client.get_note_store()
        self.storage = RemoteStorage(notebooks)

    def get_upload_limit(self):
        return {
            1: 25 * 1024 * 1024,
            3: 100 * 1024 * 1024,
            5: 200 * 1024 * 1024,
        }.get(self.userStore.getUser().privilege, 0)

    def create_notebook(self, noteFullPath):
        if self.get(noteFullPath): return False
        notebook = Types.Notebook()
        notebook.name = noteFullPath
        try:
            notebook = self.noteStore.createNotebook(notebook)
        except EDAMUserException as e:
            if e.errorCode == 10 and e.parameter == 'Notebook.name':
                self.storage.update(self.token, self.noteStore)
                return True
            else:
                raise e
        self.storage.create_notebook(notebook)
        return True

    def create_note(self, noteFullPath, content=''):
        if self.get(noteFullPath): return False
        notebookName, noteName = noteFullPath
        note = self._create_note(notebookName, noteName, content)
        note = self.noteStore.createNote(note)
        self.storage.create_note(note, notebookName)
        return True

    def _create_note(self, notebookName, noteName, content, otherAttr={}):
        note = Types.Note()
        note.title = noteName
        note.content = '<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/enml2.dtd"><en-note><center>{}</center></en-note>'.format(quote(content))
        if self.get([notebookName]) is None: self.create_notebook(notebookName)
        note.attributes = Types.NoteAttributes(contentClass='yinxiang.markdown')
        note.notebookGuid = self.get([notebookName]).guid
        for attr, value in otherAttr.items():
            setattr(note, attr, value)
        return note

    def update_note(self, noteFullPath, content=None):
        note = self.get(noteFullPath)
        if note is None: return self.create_note(noteFullPath, content or '')
        notebook, title = noteFullPath[0], noteFullPath[1]
        newnote = self._create_note(notebook, title, content, otherAttr={'guid': note.guid})
        self.noteStore.updateNote(newnote)

        self.storage.delete_note(noteFullPath)
        self.storage.create_note(note, notebook)
        return True

    def get_content(self, noteFullPath):
        note = self.get(noteFullPath)
        if note is None: return
        content = self.noteStore.getNoteContent(note.guid)
        parsed_content = parse_content(content)
        return parsed_content

    def get_attachment(self, noteFullPath):

        note = self.get(noteFullPath) # NoteMetadata
        attachmentDict = {}
        for resource in (self.noteStore.getNote(note.guid, False, True, False, False).resources or {}):
            attachmentDict[resource.attributes.fileName] = resource.data.body
        return attachmentDict

    def move_note(self, noteFullPath, _to):
        if self.get(noteFullPath) is None: return False
        if len(noteFullPath) < 2 or 1 < len(_to): raise Exception('Type Error')
        self.noteStore.copyNote(self.token, self.get(noteFullPath).guid, self.get(_to).guid)
        if self.isSpecialToken:
            self.noteStore.expungeNote(self.token, self.get(noteFullPath).guid)
        else:
            self.noteStore.deleteNote(self.token, self.get(noteFullPath).guid)
        self.storage.move_note(noteFullPath, _to)
        return True

    def delete_note(self, noteFullPath):
        note = self.get(noteFullPath)
        if note is None: return False
        if len(noteFullPath) < 2: raise Exception('Types Error')
        self.noteStore.deleteNote(self.token, note.guid)
        self.storage.delete_note(noteFullPath)
        return True

    def delete_notebook(self, noteFullPath):
        if not self.get(noteFullPath) or not self.isSpecialToken: return False
        if 1 < len(noteFullPath): raise Exception('Types Error')
        self.noteStore.expungeNotebook(self.token, self.get(noteFullPath).guid)
        self.storage.delete_notebook(noteFullPath)
        return True

    def get(self, s):
        """

        :param s: ['Vim', 'Vscode C++ 一键编译运行']
        :return:
        """
        return self.storage.get(s)

    def show_notebook(self):
        self.storage.show_notebook()

    def show_notes(self, notebook=None):
        self.storage.show_notes(notebook)

    def _md5(self, s):
        m = hashlib.md5()
        m.update(s)
        return m.hexdigest()

def parse_content(text):
    html = bytes(bytearray(text, encoding='utf-8'))
    html = etree.HTML(html)
    centerTag = html.xpath('//center/text()')[0]
    return unquote(centerTag)

if __name__ == '__main__':
    # You can get this from 'https://%s/api/DeveloperToken.action'%SERVICE_HOST >>
    # In China it's https://app.yinxiang.com/api/DeveloperToken.action <<
    token = 'S=s1:U=91eca:E=15be6680420:C=1548eb6d760:P=1cd:A=en-devtoken:V=2:H=026e6ff5f5d0753eb37146a1b4660cc9'
    e = EvernoteController(token, True, True)
    # e.update_note('Hello', 'Test', 'Changed', 'README.md')
    e.create_note(['Test', '中文'], 'Chinese')
