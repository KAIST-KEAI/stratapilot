import sys

sys.dont_write_bytecode = True
from jarvis.atom_action.src import *

def view_document(file_path) -> None:
    return evince(file_path)

<<<<<<< HEAD
<<<<<<< HEAD
=======
def view_txt(file_path) -> None:
    return gedit(file_path)
=======
# add by wzm
def view_office_document(file_path, sys_version) -> None:
    if 'mac' in sys_version:
        return soffice(file_path)
    else:
        return libreoffice(file_path)
>>>>>>> a71dd16 (add mac version for open doc)

>>>>>>> aaa5bdd (add multi-parameter open_document function)
def play_audio(file_path) -> None:
    return rhythmbox_client(f"--play-uri=\"{file_path}\"")

def play_video(file_path) -> None:
    return totem(file_path)

def view_office_document(file_path) -> None:
    return libreoffice(file_path)
