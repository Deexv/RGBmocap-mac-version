"""Small GUI request preparation; all baking/copying runs in a worker."""
import uuid
from pathlib import Path
from PySide6.QtWidgets import QFileDialog


def targets(files):
    used=set();result=[]
    for project,kind,source,target in files:
        target=Path(target);folder=target.with_suffix('');number=2
        while folder.exists() or str(folder.resolve()).casefold() in used:
            folder=target.parent/(target.stem+'_'+str(number));number+=1
        used.add(str(folder.resolve()).casefold());result.append((project,kind,source,folder/target.name))
    return result


def choose_combined(parent):
    name, _ = QFileDialog.getSaveFileName(parent, 'Export One Blender File', 'Motion.blend',
                                           'Blender (*.blend)', options=QFileDialog.DontConfirmOverwrite)
    return Path(name).with_suffix('.blend') if name else None
