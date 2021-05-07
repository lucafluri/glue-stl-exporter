from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from PyQt5.QtCore import QObject, QThread, pyqtSignal


class SaveItemsWorker(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(int)
    
    def __init__(self, controller):
        super(SaveItemsWorker, self).__init__()
        self.isRunning = True
        self.controller = controller

    def stop(self):
        self.isRunning = False
        
        
    def run(self, selectedDict):
        count = 0
        for selectedItem in selectedDict.values():
            if not self.isRunning:
                break

            self.controller.saveSelectedItem(selectedItem)

            count += 1
            self.progress.emit(count)
        self.finished.emit()

