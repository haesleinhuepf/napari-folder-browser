from napari_plugin_engine import napari_hook_implementation
from qtpy.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLineEdit, QListWidget, QListWidgetItem, QLabel, QFileDialog
from qtpy.QtCore import QEvent, Qt
from qtpy.QtCore import Signal, QObject, QEvent
from magicgui.widgets import FileEdit
from magicgui.types import FileDialogMode

from os import listdir
from os.path import isfile, join
import fnmatch

class MyQLineEdit(QLineEdit):
    keyup = Signal()
    keydown = Signal()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Up:
            self.keyup.emit()
            return
        elif event.key() == Qt.Key_Down:
            self.keydown.emit()
            return
        super().keyPressEvent(event)

class FolderBrowser(QWidget):
    def __init__(self, napari_viewer):
        super().__init__()
        self.viewer = napari_viewer

        self.setLayout(QVBoxLayout())


        # --------------------------------------------
        # Directory selection
        file = str(QFileDialog.getExistingDirectory(self, "Select Directory"))

        self.layout().addWidget(QLabel("Directory"))
        filename_edit = FileEdit(
            mode=FileDialogMode.EXISTING_DIRECTORY,
            value=file)
        self.layout().addWidget(filename_edit.native)

        def directory_changed(*args, **kwargs):
            self.current_directory = str(filename_edit.value.absolute()).replace("\\", "/").replace("//", "/")
            self.all_files = [f for f in listdir(self.current_directory) if isfile(join(self.current_directory, f))]

            text_changed() # update shown list

        filename_edit.line_edit.changed.connect(directory_changed)

        # --------------------------------------------
        #  File filter
        self.layout().addWidget(QLabel("File filter"))
        seach_field = MyQLineEdit("*")
        results = QListWidget()

        # update search
        def text_changed(*args, **kwargs):
            search_string = seach_field.text()

            results.clear()
            for file_name in self.all_files:
                if fnmatch.fnmatch(file_name, search_string):
                    _add_result(results, file_name)
            results.sortItems()

        # navigation in the list
        def key_up():
            if results.currentRow() > 0:
                results.setCurrentRow(results.currentRow() - 1)

        def key_down():
            if results.currentRow() < results.count() - 1:
                results.setCurrentRow(results.currentRow() + 1)

        seach_field.keyup.connect(key_up)
        seach_field.keydown.connect(key_down)
        seach_field.textChanged.connect(text_changed)

        # open file on ENTER and double click
        def item_double_clicked():
            item = results.currentItem()
            print("opening", item.file_name)
            self.viewer.open(join(self.current_directory, item.file_name))

        seach_field.returnPressed.connect(item_double_clicked)
        #results.itemDoubleClicked.connect(item_double_clicked)
        results.itemActivated.connect(item_double_clicked)

        self.setLayout(QVBoxLayout())

        w = QWidget()
        w.setLayout(QHBoxLayout())
        w.layout().addWidget(QLabel("Search:"))
        w.layout().addWidget(seach_field)
        self.layout().addWidget(w)

        self.layout().addWidget(results)

        directory_changed() # run once to initialize


def _add_result(results, file_name):
    item = QListWidgetItem(file_name)
    item.file_name = file_name
    results.addItem(item)


@napari_hook_implementation
def napari_experimental_provide_dock_widget():
    return [FolderBrowser]
