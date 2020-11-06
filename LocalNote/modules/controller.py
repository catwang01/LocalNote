import os, time, re
import sys
current_dir = os.path.dirname(__file__)
sys.path.append(current_dir)
sys.path.append(os.path.dirname(current_dir))
from collections import defaultdict

import chardet
from urllib.parse import quote

from .evernotecontroller import EvernoteController
from .storage import LocalStorage
from local import html2text, markdown
from .constant import DOWNLOAD, UPLOAD, CONFLICT


class ObjectStore:
    def __init__(self, store_path='.objects'):
        self.store_path = store_path
        self.create_store()

    def create_store(self):
        if not os.path.exists(self.store_path):
            os.mkdir(self.store_path)

    def add_object(self, guid):
        with open(os.path.join(self.store_path, guid), "w") as f:
            f.write("")

    def delete_object(self, guid):
        object_path = os.path.join(self.store_path, guid)
        if os.path.exists(object_path):
            os.remove(object_path)
        else:
            raise Exception("Object {} doesn't exist".format(object_path))

    def exists(self, guid):
        return os.path.exists(os.path.join(self.store_path, guid))

class Controller(object):
    def __init__(self):
        self.ls = LocalStorage()
        self.token, self.isSpecialToken, self.sandbox, self.isInternational, self.expireTime, self.lastUpdate, self.notebooks = self.ls.get_config()
        self.available, self.ec = self.__check_available()
        if self.available:
            self.es = self.ec.storage
            self.ls.maxUpload = self.ec.get_upload_limit()
        self.changesDict = {}
        self.objectStore = ObjectStore()

    def __check_available(self):
        if not self.isSpecialToken and self.expireTime < time.time(): return False, None
        if self.token == '': return False, None
        try:
            ec = EvernoteController(self.token, self.isSpecialToken, self.sandbox, self.isInternational, self.notebooks)
            self.ls.update_config(self.token, self.isSpecialToken, self.sandbox, self.isInternational,
                                  self.expireTime, self.lastUpdate, self.notebooks)
            return True, ec
        except Exception as e:
            print(e)
            return False, None

    def log_in(self, config={}, **kwargs):
        config = dict(config, **kwargs)
        if config.get('token') is not None: self.token = config.get('token')
        if config.get('isSpecialToken') is not None: self.isSpecialToken = config.get('isSpecialToken')
        if config.get('sandbox') is not None: self.sandbox = config.get('sandbox')
        if config.get('isInternational') is not None: self.isInternational = config.get('isInternational')
        if config.get('expireTime') is not None: self.expireTime = config.get('expireTime')
        if config.get('lastUpdate') is not None: self.lastUpdate = config.get('lastUpdate')
        if config.get('notebooks') is not None: self.notebooks = config.get('notebooks')
        available, ec = self.__check_available()
        if available:
            self.available = True
            self.ec = ec
            self.es = self.ec.storage
            self.ls.maxUpload = self.ec.get_upload_limit()
        return available

    def fetch_notes(self):
        if not self.available: return False
        self.es.update(self.token, self.ec.noteStore)
        return True

    def __get_changes(self, update=False):  # -1 for need download, 1 for need upload, 0 for can be uploaded and downloaded
        if not update: return self.changesDict
        localNoteDict = self.ls.get_file_dict()
        remoteNoteDict = self.es.get_note_dict()

        # self.ls.updated local.updated remote.updated
        # normal [local.updated, remote.updated] < self.ls.updated
        # self.ls.updated < local.updated ==> local is updated
        # self.ls.updated < remote.updated ==> remote is updated

        changeDict = {
            UPLOAD: {},
            DOWNLOAD: {},
            CONFLICT: {}
        }


        localset = set(localNoteDict.keys())
        remoteset = set(remoteNoteDict.keys())

        for notebookName in localset - remoteset:
            if self.ls.lastUpdate < localNoteDict[notebookName].updated:  # local is updated
                changeDict[CONFLICT][notebookName] = [] # because we don't know remote is udpated nor not
            else: # local is unchanged
                changeDict[UPLOAD][notebookName] = []
                for noteName in remoteNoteDict[notebookName].notes:
                    changeDict[UPLOAD][notebookName].append(noteName)

        for notebookName in remoteset - localset:
            if self.ls.lastUpdate < remoteNoteDict[notebookName].updated and \
                self.objectStore.exists(self.es.get([notebookName]).guid): # local is deleted
                    changeDict[CONFLICT][notebookName] = [] # because we don't know local is deleted or not exists at all
            else:
                changeDict[DOWNLOAD][notebookName] = []
                for noteName in remoteNoteDict[notebookName].notes:
                    changeDict[DOWNLOAD][notebookName].append(noteName)

        for notebookName in remoteset & localset:
            localnotebook = localNoteDict[notebookName]
            remotenotebook = remoteNoteDict[notebookName]
            localnoteset = set(localnotebook.notes.keys())
            remotenoteset = set(remotenotebook.notes.keys())

            for noteName in localnoteset - remotenoteset:
                if self.ls.lastUpdate < localnotebook.notes[noteName].updated:  # local is updated
                    if notebookName not in changeDict[CONFLICT]:
                        changeDict[CONFLICT][notebookName] = []
                    changeDict[CONFLICT][notebookName].append(noteName)  # because we don't know remote is udpated nor not
                else:  # local is unchanged
                    if notebookName not in changeDict[DOWNLOAD]:
                        changeDict[DOWNLOAD][notebookName] = []
                    changeDict[DOWNLOAD][notebookName].append(noteName)

            for noteName in remotenoteset - localnoteset:
                if self.ls.lastUpdate < remotenotebook.notes[noteName].updated:  # remote is updated
                    if notebookName not in changeDict[CONFLICT]:
                        changeDict[CONFLICT][notebookName] = []
                    changeDict[CONFLICT][notebookName].append(noteName)  # because we don't know remote is udpated nor not
                else:  # remote is unchanged
                    if notebookName not in changeDict[UPLOAD]:
                        changeDict[UPLOAD][notebookName] = []
                    changeDict[UPLOAD][notebookName].append(noteName)

            for noteName in localnoteset & remotenoteset:
                if self.ls.lastUpdate < localnotebook.notes[noteName].updated: # local is udpated
                    if self.ls.lastUpdate < remotenotebook.notes[noteName].updated: # remote is updated
                        if notebookName not in changeDict[CONFLICT]:
                            changeDict[CONFLICT][notebookName] = []
                        changeDict[CONFLICT][notebookName].append(noteName)
                    else: # remote is unchanged
                        if notebookName not in changeDict[UPLOAD]:
                            changeDict[UPLOAD][notebookName] = []
                        changeDict[UPLOAD][notebookName].append(noteName)
                else: # local is unchanged
                    if self.ls.lastUpdate < remotenotebook.notes[noteName].updated: # remote is updated
                        if notebookName not in changeDict[CONFLICT]:
                            changeDict[CONFLICT][notebookName] = []
                        changeDict[CONFLICT][notebookName].append(noteName)
                    else: # both local and remote are unchanged
                        pass

        self.changesDict = changeDict
        return changeDict


    def get_changes(self):
        return self.__get_changes(True)

    def check_files_format(self):
        return self.ls.check_files_format()

    def download_notes(self, update=True):
        if not self.available: return False
        invalidNoteList = []

        def _download_note(noteFullPath):
            if (any(c in ''.join(noteFullPath) for c in u'\\/:*?"<>|\xa0')
                    or noteFullPath[1] == '.DS_Store'):
                invalidNoteList.append(noteFullPath)
                return
            print(('Downloading ' + os.path.join(*noteFullPath)))
            noteObj = self.es.get(noteFullPath)
            if noteObj is None:  # delete note if is deleted online
                self.ls.write_note(noteFullPath, {})
                return
            content = self.ec.get_content(noteFullPath)
            self.ls.write_note(noteFullPath, content)
            self.objectStore.add_object(self.es.get(noteFullPath).guid)

        downloadDict = self.changesDict[DOWNLOAD]
        for notebookName in downloadDict:
            os.makedirs(notebookName)
            guid = self.es.get([notebookName]).guid
            self.objectStore.add_object(guid)
            for note in downloadDict[notebookName]:
                _download_note([notebookName, note])
        self.ls.update_config(lastUpdate=time.time() + 1)
        return invalidNoteList or True

    def upload_files(self, update=True):
        if not self.available: return False


        localNoteDict = self.ls.get_file_dict()
        remoteNoteDict = self.es.get_note_dict()

        changesDict = self.__get_changes(update)
        uploadDict = changesDict[UPLOAD]
        for notebookName in uploadDict:
            if notebookName not in localNoteDict: # local无 删了
                self.ec.delete_notebook(notebookName)
                self.objectStore.delete_object(self.es.get([notebookName]).guid)
            else:
                if notebookName not in remoteNoteDict: # local 有 remote 没有
                    self.ec.create_notebook(notebookName)
                else:
                    for noteName in uploadDict[notebookName]:
                        if noteName not in localNoteDict[notebookName].notes:
                            self.objectStore.delete_object(self.es.get([notebookName, noteName]).guid)
                            self.ec.delete_note([notebookName, noteName])
                        else:
                            print('Uploading ', '/'.join([notebookName, noteName]))
                            filepath = os.path.join(notebookName, noteName)
                            with open(filepath + ".md") as f:
                                txt = f.read()
                            self.ec.update_note([notebookName, noteName], txt)

        self.ls.update_config(lastUpdate=time.time() + 1)
        return True


def convert_html(htmlDir, force=None):
    # FileName for done, 1 for wrong file type, 2 for file missing
    # 3 for need rename, 4 for unknown encoding
    fileName, ext = os.path.splitext(htmlDir)
    if ext != '.html': return 1
    if not os.path.exists(htmlDir): return 2
    with open(htmlDir, 'rb') as f:
        content = f.read()
    try:
        content = content
    except:
        try:
            content = content.decode(chardet.detect(content)['encoding'])
        except:
            return 4
    if os.path.exists(fileName + '.md'):
        if force is None:
            return 3
        elif force == True:
            pass
        elif force == False:
            index = 1
            while 1:
                if not os.path.exists(fileName + '(%s)' % index + '.md'): break
                index += 1
            fileName += '(%s)' % index
    with open(fileName + '.md', 'wb') as f:
        f.write(html2text(content).encode('utf8'))
    return fileName + '.md'
