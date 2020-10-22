import os
import shutil

def clear_dir(currentDir):
    for file_or_folder in os.listdir(currentDir):
        if os.path.isdir(file_or_folder):
            shutil.rmtree(file_or_folder)
        elif os.path.isfile(file_or_folder):
            os.remove(file_or_folder)
        else:
            pass
