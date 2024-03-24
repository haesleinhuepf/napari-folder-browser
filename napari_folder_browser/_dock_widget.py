from pathlib import Path
from PyQt5.QtCore import QModelIndex
from PyQt5.QtWidgets import QAction
from napari_plugin_engine import napari_hook_implementation
from numpy import stack
from qtpy.QtWidgets import (
    QAbstractItemView,
    QMenu,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QLabel,
    QFileDialog,
    QTreeView,
)
from qtpy.QtCore import QPoint, Qt, QDir, Signal
from qtpy.QtGui import QFileSystemModel
from magicgui.widgets import FileEdit
from magicgui.types import FileDialogMode

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from qtpy.QtCore import QModelIndex

from os import listdir
from os.path import isfile, join
import fnmatch
from napari_tools_menu import register_dock_widget

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

@register_dock_widget(menu="Utilities > Folder browser")
class FolderBrowser(QWidget):
    """Main Widget for the Folder Browser Dock Widget
    
    The napari viewer is passed in as an argument to the constructor
    """
    def __init__(self, napari_viewer):
        super().__init__()
        self.viewer = napari_viewer

        self.setLayout(QVBoxLayout())

        # --------------------------------------------
        # Directory selection
        top_level_directory: Path = Path(QFileDialog.getExistingDirectory(self, "Select Directory"))

        # Create file system model & tree view
        self.file_system_model = QFileSystemModel()
        self.file_system_model.setRootPath(QDir.rootPath())

        self.tree_view = QTreeView()
        self.tree_view.setModel(self.file_system_model)
        self.tree_view.setRootIndex(self.file_system_model.index(str(top_level_directory)))
        
        # Enable selecting multiple files for stack viewing (with shift/ctrl)
        self.tree_view.setSelectionMode(QAbstractItemView.ExtendedSelection)

        # Connect the double click signal to a slot that opens the file
        self.tree_view.doubleClicked.connect(self.tree_double_click)

        # Enable context menu for multi selection
        self.tree_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(self.show_context_menu)

        # Hide the columns for size, type, and last modified
        self.tree_view.setHeaderHidden(True)
        self.tree_view.hideColumn(1)
        self.tree_view.hideColumn(2)
        self.tree_view.hideColumn(3)
        
        self.layout().addWidget(self.tree_view)


    def tree_double_click(self, index: QModelIndex) -> None:
        """Action on double click in the tree model
        
        Opens the selected file or in the folder
        """
        file_path: str = self.file_system_model.filePath(index)
        if self.file_system_model.isDir(index):
            self.tree_view.setRootIndex(index)
        else:
            print(f"Opening file: {file_path}")
            self.viewer.open(file_path)


    def show_context_menu(self, position: QPoint) -> None:
        """Show a context menu when right-clicking in the tree view"""
        menu = QMenu()
        open_multiple_action: QAction = menu.addAction("Open multiple files")
        open_multiple_action.triggered.connect(
            lambda: self.open_multi_selection(is_stack=False)
        )
        open_as_stack_action: QAction = menu.addAction("Open as stack")
        open_as_stack_action.triggered.connect(
            lambda: self.open_multi_selection(is_stack=True)
        )
        # Show the menu at the cursor position
        menu.exec_(self.tree_view.viewport().mapToGlobal(position))


    def open_multi_selection(self, is_stack: bool) -> None:
        """Open multiple files in the viewer
        
        The files are selected in the tree view
        
        Args:
            is_stack: If True, the files are opened as a stack
        """
        # The selection model returns the index for every column
        indices: list[QModelIndex] = self.tree_view.selectionModel().selectedIndexes()

        # We simply ignore folders in the multi-selection
        fs_paths: list[str] = [
            self.file_system_model.filePath(index) for index in indices
            if not self.file_system_model.isDir(index) and index.column() == 0
        ]

        # Nothing to do when there is no file selected
        if len(fs_paths) == 0:
            return

        self.viewer.open(fs_paths, stack=is_stack)

        # self.layout().addWidget(QLabel("Directory"))
        # filename_edit = FileEdit(
        #     mode=FileDialogMode.EXISTING_DIRECTORY,
        #     value=top_level_directory,
        # )
        # self.layout().addWidget(filename_edit.native)

        # def directory_changed(*_) -> None:
        #     self.current_directory = str(filename_edit.value.absolute()).replace("\\", "/").replace("//", "/")
        #     self.all_files = [f for f in listdir(self.current_directory) if isfile(join(self.current_directory, f))]

        #     text_changed() # update shown list

        # filename_edit.line_edit.changed.connect(directory_changed)

        # --------------------------------------------
        #  File filter
        # self.layout().addWidget(QLabel("File filter"))
        # seach_field = MyQLineEdit("*")
        # results = QListWidget()

        # # update search
        # def text_changed(*args, **kwargs):
        #     search_string = seach_field.text()

        #     results.clear()
        #     for file_name in self.all_files:
        #         if fnmatch.fnmatch(file_name, search_string):
        #             _add_result(results, file_name)
        #     results.sortItems()

        # # navigation in the list
        # def key_up():
        #     if results.currentRow() > 0:
        #         results.setCurrentRow(results.currentRow() - 1)

        # def key_down():
        #     if results.currentRow() < results.count() - 1:
        #         results.setCurrentRow(results.currentRow() + 1)

        # seach_field.keyup.connect(key_up)
        # seach_field.keydown.connect(key_down)
        # seach_field.textChanged.connect(text_changed)

        # # open file on ENTER and double click
        # def item_double_clicked():
        #     item = results.currentItem()
        #     print("opening", item.file_name)
        #     self.viewer.open(join(self.current_directory, item.file_name))

        # seach_field.returnPressed.connect(item_double_clicked)
        # #results.itemDoubleClicked.connect(item_double_clicked)
        # results.itemActivated.connect(item_double_clicked)

        # self.setLayout(QVBoxLayout())

        # w = QWidget()
        # w.setLayout(QHBoxLayout())
        # w.layout().addWidget(QLabel("Search:"))
        # w.layout().addWidget(seach_field)
        # self.layout().addWidget(w)

        # self.layout().addWidget(results)

        # directory_changed() # run once to initialize


def _add_result(results, file_name):
    item = QListWidgetItem(file_name)
    item.file_name = file_name
    results.addItem(item)


@napari_hook_implementation
def napari_experimental_provide_dock_widget():
    return [FolderBrowser]


if __name__ == "__main__":
    # Just for running in Debugger
    import napari

    viewer = napari.Viewer()
    napari.run()