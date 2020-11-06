print('__file__={0} | __name__={1} | __package__={2}'.format(__file__,__name__,str(__package__)))
import json, os, time, sys, re
from .notes import SimpleNote, SimpleNotebook
from os.path import join, exists
import shutil
from functools import reduce
import sys
import os
current_dir = os.path.dirname(__file__)
sys.path.append(current_dir)
sys.path.append(os.path.dirname(current_dir))
import evernote.edam.notestore.NoteStore as NoteStore

CONFIG_DIR = 'user.cfg'

# fileDictFormat: {
# 'notebookName':[('note1', timeStamp), ..],
# }
# fileFormat: {
# 'name': "note's name",
# 'content': u''.encode('utf-8'),
# 'attachment': [('name', u''.encode),..),],
# }


class RemoteStorage():

    storage = {}

    def __init__(self, notebooks=None):
        """

        :param notebooks: None 表示默认所有笔记本
        """
        self.available = False
        self.notebooks = notebooks

    def update(self, token, noteStore):
        f = NoteStore.NoteFilter()
        s = NoteStore.NotesMetadataResultSpec()
        s.includeTitle = True
        s.includeUpdated = True
        for nb in noteStore.listNotebooks():
            if self.notebooks is not None and nb.name not in self.notebooks: continue
            self.storage[nb.name] = {}
            self.storage[nb.name]['notebook'] = nb
            self.storage[nb.name]['notes'] = {}
            f.notebookGuid = nb.guid
            for ns in noteStore.findNotesMetadata(f, 0, 9999, s).notes:
                self.storage[nb.name]['notes'][ns.title] = ns
        self.defaultNotebook = noteStore.getDefaultNotebook(token).name

    def create_note(self, note, notebookName=None):
        if notebookName is None: notebookName = self.defaultNotebook
        if self.get(notebookName) is None: return False
        self.storage[notebookName]['notes'][note.title] = note
        return True

    def create_notebook(self, notebook):
        if self.get(notebook.name) is not None: return False
        self.storage[notebook.name] = {}
        self.storage[notebook.name]['notebook'] = notebook
        self.storage[notebook.name]['notes'] = {}
        return True

    def copy_note(self, noteFullPath, _to=None):
        if _to is None: _to = self.defaultNotebook
        note = self.get(noteFullPath)
        if len(noteFullPath) < 2 or note is None: return False
        self.storage[_to]['notes'][note.title] = note
        return True

    def move_note(self, noteFullPath, _to=None):
        r = self.copy_note(noteFullPath, _to)
        if r == False: return False
        return self.delete_note(noteFullPath)

    def delete_note(self, noteFullPath):
        if self.get(noteFullPath) is None: return False
        del self.storage[noteFullPath[0]]['notes'][noteFullPath[1]]
        return True

    def delete_notebook(self, noteFullPath):
        if self.get(noteFullPath) is None: return False
        del self.storage[noteFullPath[0]]
        return True

    def get(self, l):
        """
        get notebook object or note object
        """
        r = self.storage.get(l[0])
        if r is None: return
        if 1 < len(l): return r['notes'].get(l[1])
        return r.get('notebook')

    def get_note_dict(self):
        """
        :return: noteDict like {'Vim': [('Vscode C++ 一键编译运行', 1602513834.0), ('vim如何添加加注册表', 1549720524.0)]}
        {'Test3': {'updated': 1603275896.0, 'notes': {}},
         'Test2': {'updated': 1603275893.0,
          'notes': {'Leetcode 58. 最后一个单词的长度 copy': 1603277433.0,
           'Pytorch onnx copy': 1603277411.0,
           'haha copy': 1603277355.0,
           'hehe': 1603277253.0,
           'haha': 1603201258.0}},
         'Test1': {'updated': 1603275871.0, 'notes': {}}}
        """
        noteDict = {}
        for notebookName, nb in self.storage.items():
            noteDict[notebookName] = SimpleNotebook(created=nb['notebook'].serviceCreated / 1000, updated=nb['notebook'].serviceUpdated / 1000)
            notes = {}
            for noteName, note in nb['notes'].items():
                notes[noteName] = SimpleNote(updated=note.updated / 1000)
            noteDict[notebookName].notes = notes
        return noteDict

    def show_notebook(self):
        for bn, nb in self.storage.items(): print_line(bn)

    def show_notes(self, notebook=None):
        for bn, nb in self.storage.items():
            if not notebook: print_line(bn + ':')
            if not notebook or bn == notebook:
                for nn, ns in nb['notes'].items():
                    print_line(('' if notebook else '    ') + nn)


def print_line(s):
    t = sys.getfilesystemencoding()
    print(s)


class LocalStorage(object):
    def __init__(self, maxUpload=0):
        self.maxUpload = maxUpload
        self.token, self.isSpecialToken, self.sandbox, self.isInternational, self.expireTime, self.lastUpdate, self.notebooks = self.__load_config()
        self.encoding = sys.stdin.encoding

    def __load_config(self):
        if not exists(CONFIG_DIR): return '', False, True, False, 0, 0, None
        with open(CONFIG_DIR) as f:
            r = json.loads(f.read())
        notebooks = r.get('notebooks')
        return (r.get('token', ''), r.get('is-special-token', False), r.get('sandbox', True),
                r.get('is-international', False), r.get('expire-time', 0), r.get('last-update', 0), notebooks)

    def __store_config(self):
        with open(CONFIG_DIR, 'w') as f:
            notebooks = self.notebooks
            f.write(json.dumps({
                'token': self.token,
                'is-special-token': self.isSpecialToken,
                'sandbox': self.sandbox,
                'is-international': self.isInternational,
                'expire-time': self.expireTime,
                'last-update': self.lastUpdate,
                'notebooks': notebooks}))

    def update_config(self, token=None, isSpecialToken=None, sandbox=None, isInternational=None, expireTime=None,
                      lastUpdate=None, notebooks=None):
        if not token is None: self.token = token
        if not isSpecialToken is None: self.isSpecialToken = isSpecialToken
        if not sandbox is None: self.sandbox = sandbox
        if not isInternational is None: self.isInternational = isInternational
        if not expireTime is None: self.expireTime = expireTime
        if not lastUpdate is None: self.lastUpdate = lastUpdate
        if not notebooks is None: self.notebooks = notebooks
        self.__store_config()

    def get_config(self):
        return self.token, self.isSpecialToken, self.sandbox, self.isInternational, self.expireTime, self.lastUpdate, self.notebooks

    def __str_c2l(self, s):
        return s
        # return s.decode('utf8').encode(sys.stdin.encoding)

    def __str_l2c(self, s):
        return s
        # try:
        #     return s.decode(sys.stdin.encoding).encode('utf8')
        # except:
        #     return s.decode(chardet.detect(s)['encoding'] or 'utf8').encode('utf8')

    def read_note(self, noteFullPath):
        attachmentDict = {}
        if exists(self.__str_c2l(join(*noteFullPath))):  # note is a foldernote
            for attachment in next(os.walk(self.__str_c2l(join(*noteFullPath))))[2]:
                with open(self.__str_c2l(join(*(noteFullPath))) + os.path.sep + attachment, 'rb') as f:
                    attachmentDict[self.__str_l2c(attachment)] = f.read()
        else:  # note is a pure file
            fileList = next(os.walk(self.__str_c2l(join(*noteFullPath[:-1]))))[2]
            for postfix in ('.md', '.html'):
                fName = noteFullPath[-1] + postfix
                if self.__str_c2l(fName) in fileList:
                    with open(self.__str_c2l(join(*noteFullPath)) + postfix, 'rb') as f:
                        attachmentDict[fName] = f.read()
        return attachmentDict

    # def write_note(self, noteFullPath, contentDict={}):
    #     if 1 < len(noteFullPath):
    #         nbName, nName = [self.__str_c2l(s) for s in noteFullPath]
    #         # clear environment
    #         if exists(nbName):
    #             for postfix in ('.md', '.html'):
    #                 if exists(join(nbName, nName + postfix)): os.remove(join(nbName, nName + postfix))
    #             if exists(join(nbName, nName)):
    #                 clear_dir(join(nbName, nName))
    #                 os.rmdir(join(nbName, nName))
    #         else:
    #             os.mkdir(nbName)
    #         # download files
    #         if not contentDict:
    #             pass
    #         elif len(contentDict) == 1:
    #             for k, v in contentDict.items():
    #                 self.write_file(noteFullPath, v, os.path.splitext(k)[1])
    #         else:
    #             if not exists(join(nbName, nName)): os.mkdir(join(nbName, nName))
    #             for k, v in contentDict.items():
    #                 self.write_file(noteFullPath + [k], v, '')  # ok, this looks strange, ext is included in k
    #     else:
    #         if contentDict:  # create folder
    #             if not exists(self.__str_c2l(noteFullPath[0])): os.mkdir(self.__str_c2l(noteFullPath[0]))
    #         else:  # delete folder
    #             noteFullPath = self.__str_c2l(noteFullPath[0])
    #             if exists(noteFullPath):
    #                 clear_dir(noteFullPath)
    #                 os.rmdir(noteFullPath)

    def write_note(self, noteFullPath, content):
        notebookName, noteName = noteFullPath
        if not os.path.exists(notebookName):
            os.mkdir(notebookName)
        with open(os.path.join(notebookName, noteName + ".md"), "w") as f:
            f.write(content)
    # else:
    #     if contentDict:  # create folder
    #         if not exists(self.__str_c2l(noteFullPath[0])): os.mkdir(self.__str_c2l(noteFullPath[0]))
    #     else:  # delete folder
    #         noteFullPath = self.__str_c2l(noteFullPath[0])
    #         if exists(noteFullPath):
    #             clear_dir(noteFullPath)
    #             os.rmdir(noteFullPath)

    # def write_file(self, noteFullPath, content, postfix='.md'):
    #     if len(noteFullPath) < 1: return False
    #     if not exists(self.__str_c2l(noteFullPath[0])):
    #         os.mkdir(self.__str_c2l(noteFullPath[0]))
    #     try:
    #         noteFullPath[1] += postfix
    #         with open(self.__str_c2l(join(*noteFullPath)), 'wb') as f:
    #             f.write(content)
    #         return True
    #     except:
    #         return False

    # def get_file_dict(self, notebooksList=None):
    #     """
    #
    #     :param notebooksList:
    #     :return: {'Test': [('Pytorch onnx copy', 1603186460.9791174), ('Leetcode 58. 最后一个单词的长度 copy', 1603186460.9058812)]}
    #     """
    #     fileDict = {}
    #     for nbName in next(os.walk('.'))[1]:  # get folders
    #         nbNameUtf8 = self.__str_l2c(nbName)
    #         if notebooksList is not None and nbNameUtf8 not in notebooksList: continue
    #         if nbNameUtf8 == '.DS_Store': continue  # Mac .DS_Store ignorance
    #         fileDict[nbNameUtf8] = []
    #         for nName in reduce(lambda x, y: x + y, next(os.walk(nbName))[1:]):  # get folders and files
    #             if nName == '.DS_Store': continue  # Mac .DS_Store ignorance
    #             filePath = join(nbName, nName)
    #             if os.path.isdir(filePath):
    #                 fileDict[nbNameUtf8].append((self.__str_l2c(nName), os.stat(filePath).st_mtime))
    #             else:
    #                 fileDict[nbNameUtf8].append(
    #                     (self.__str_l2c(os.path.splitext(nName)[0]), os.stat(filePath).st_mtime))
    #     return fileDict

    def get_file_dict(self, notebooksList=None):
        """

        :param notebooksList:
        :return: {'Test': [('Pytorch onnx copy', 1603186460.9791174), ('Leetcode 58. 最后一个单词的长度 copy', 1603186460.9058812)]}
        """

        fileDict = {}
        for notebookName in next(os.walk('.'))[1]:  # get folders
            if notebookName == '.objects': continue
            if notebooksList is not None and notebookName not in notebooksList: continue
            if notebookName == '.DS_Store': continue  # Mac .DS_Store ignorance
            fileDict[notebookName] = SimpleNotebook(created=os.path.getctime(notebookName), updated=os.path.getmtime(notebookName))
            notes = {}
            for noteName in os.listdir(notebookName):
                if noteName == '.DS_Store': continue  # Mac .DS_Store ignorance
                filePath = os.path.join(notebookName, noteName)
                notes[os.path.splitext(noteName)[0]] = SimpleNote(created=os.path.getctime(filePath), updated=os.path.getmtime(filePath))
            fileDict[notebookName].notes = notes
        return fileDict

    def check_files_format(self):
        try:
            with open('user.cfg') as f:
                j = json.loads(f.read())
            if len(j) != 7: raise Exception
            for k in j.keys():
                if k not in ('token', 'is-special-token', 'sandbox', 'notebooks',
                             'is-international', 'expire-time', 'last-update'):
                    raise Exception
        except:
            return False, []
        r = []  # (filename, status) 1 for wrong placement, 2 for too large, 3 for missing main file
        notebooks, notes = next(os.walk('.'))[1:]
        notebooks.remove(".objects")
        for note in notes:
            if note not in ('user.cfg', '.DS_Store'): r.append((self.__str_l2c(note), 1))
        for notebook in notebooks:
            if notebook == '.DS_Store':  # Mac .DS_Store ignorance
                r.append(('.DS_Store', 1))
                continue
            folderNotes, notes = next(os.walk(notebook))[1:]
            for note in notes:
                if note == '.DS_Store': continue  # Mac .DS_Store ignorance
                if re.compile('.+\.(md|html)').match(note):
                    if self.maxUpload < os.path.getsize(join(notebook, note)):
                        r.append((self.__str_l2c(join(notebook, note)), 2))
                else:
                    r.append((self.__str_l2c(join(notebook, note)), 3))
            for folderNote in folderNotes:
                if folderNote == '.DS_Store':
                    r.append((self.__str_l2c(join(notebook, folderNote)), 1))
                    continue  # Mac .DS_Store ignorance
                size = 0
                wrongFolders, attas = next(os.walk(join(notebook, folderNote)))[1:]
                if filter(lambda x: re.compile('.+\.(md|html)').match(x), attas) == []:
                    r.append((self.__str_l2c(join(notebook, folderNote)), 3))
                for atta in attas: size += os.path.getsize(join(notebook, folderNote, atta))
                for wrongFolder in wrongFolders:
                    r.append((self.__str_l2c(join(notebook, folderNote, wrongFolder)), 1))
                if self.maxUpload < size:
                    r.append((self.__str_l2c(join(notebook, folderNote)), 2))
        return True, r


