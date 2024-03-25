from pathlib import Path
from PyQt5.QtCore import QModelIndex
from PyQt5.QtWidgets import QAction
from napari_plugin_engine import napari_hook_implementation
from qtpy.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QMenu,
    QWidget,
    QVBoxLayout,
    QLabel,
    QFileDialog,
    QLineEdit,
    QTreeView,
)
from qtpy.QtCore import QPoint, QRegExp, QSortFilterProxyModel, Qt, QDir
from qtpy.QtGui import QFileSystemModel
from napari.viewer import Viewer
from magicgui.widgets import FileEdit
from magicgui.types import FileDialogMode

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from qtpy.QtCore import QModelIndex

from napari_tools_menu import register_dock_widget


class DirectoryFriendlyFilterProxyModel(QSortFilterProxyModel):
    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        """Accepts directories and files that pass the base class's filter
        
        Note: This custom proxy ensures that we can search for filenames and keep the directories
        in the tree view
        """
        # Get the index for the row
        model = self.sourceModel()
        index = model.index(source_row, 0, source_parent)

        # Always accept directories
        if model.isDir(index):
            return True

        # For files, use the base class's implementation
        return super().filterAcceptsRow(source_row, source_parent)


@register_dock_widget(menu="Utilities > Folder browser")
class FolderBrowser(QWidget):
    """Main Widget for the Folder Browser Dock Widget
    
    The napari viewer is passed in as an argument to the constructor
    """
    viewer: Viewer
    folder_chooser: FileEdit
    file_system_model: QFileSystemModel
    proxy_model: DirectoryFriendlyFilterProxyModel
    search_field: QLineEdit
    tree_view: QTreeView

    def __init__(self, napari_viewer):
        super().__init__()
        self.viewer = napari_viewer

        self.setLayout(QVBoxLayout())

        # --------------------------------------------
        # Directory selection
        current_directory: Path = Path(QFileDialog.getExistingDirectory(self, "Select Directory"))
        self.layout().addWidget(QLabel("Directory"))
        self.folder_chooser = FileEdit(
            mode=FileDialogMode.EXISTING_DIRECTORY,
            value=current_directory,
        )
        self.layout().addWidget(self.folder_chooser.native)

        def directory_changed(*_) -> None:
            current_directory = Path(self.folder_chooser.value)
            self.tree_view.setRootIndex(
                self.proxy_model.mapFromSource(
                    self.file_system_model.index(current_directory.as_posix())
                )
            )

        self.folder_chooser.line_edit.changed.connect(directory_changed)

        # --------------------------------------------
        # File system abstraction with proxy for search filtering
        self.file_system_model = QFileSystemModel()
        self.file_system_model.setRootPath(QDir.rootPath())
        self.proxy_model = DirectoryFriendlyFilterProxyModel()
        self.proxy_model.setSourceModel(self.file_system_model)

        # Create search box and connect to proxy model
        self.layout().addWidget(QLabel("File filter"))
        self.search_field = QLineEdit()
        # Note: We should agree on the best regex interaction to provide here
        def update_filter(text: str) -> None:
            self.proxy_model.setFilterRegExp(QRegExp(text, Qt.CaseInsensitive))
        self.search_field.textChanged.connect(update_filter)
        search_widget = QWidget()
        search_widget.setLayout(QHBoxLayout())
        search_widget.layout().addWidget(QLabel("Search:"))
        search_widget.layout().addWidget(self.search_field)
        self.layout().addWidget(search_widget)

        # Tree view and image selection
        self.tree_view = QTreeView()
        self.tree_view.setModel(self.proxy_model)
        # self.tree_view.setRootIndex(self.file_system_model.index(self.current_directory.as_posix()))
        self.tree_view.setRootIndex(
            self.proxy_model.mapFromSource(
                self.file_system_model.index(current_directory.as_posix())
            )
        )
    
        # Enable selecting multiple files for stack viewing (with shift/ctrl)
        self.tree_view.setSelectionMode(QAbstractItemView.ExtendedSelection)

        # Connect the double click signal to a slot that opens the file
        self.tree_view.doubleClicked.connect(self.__tree_double_click)

        # Enable context menu for multi selection
        self.tree_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(self.__show_context_menu)

        # Hide the columns for size, type, and last modified
        self.tree_view.setHeaderHidden(True)
        self.tree_view.hideColumn(1)
        self.tree_view.hideColumn(2)
        self.tree_view.hideColumn(3)
        
        self.layout().addWidget(self.tree_view)

    def __tree_double_click(self, index: QModelIndex) -> None:
        """Action on double click in the tree model
        
        Opens the selected file or in the folder
        
        Args:
            index: Index of the selected item in the tree view
        """
        # Note: Need to remap indices from proxy to source for file system operations
        source_index: QModelIndex = self.proxy_model.mapToSource(index)
        file_path: str = self.file_system_model.filePath(source_index)
        if self.file_system_model.isDir(source_index):
            self.tree_view.setRootIndex(index)
            self.folder_chooser.value = file_path
        else:
            print(f"Opening file: {file_path}")
            self.viewer.open(file_path)

    def __show_context_menu(self, position: QPoint) -> None:
        """Show a context menu when right-clicking in the tree view"""
        menu = QMenu()
        open_multiple_action: QAction = menu.addAction("Open multiple files")
        open_multiple_action.triggered.connect(
            lambda: self.__open_multi_selection(is_stack=False)
        )
        open_as_stack_action: QAction = menu.addAction("Open as stack")
        open_as_stack_action.triggered.connect(
            lambda: self.__open_multi_selection(is_stack=True)
        )
        # Show the menu at the cursor position
        menu.exec_(self.tree_view.viewport().mapToGlobal(position))

    def __open_multi_selection(self, is_stack: bool) -> None:
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


@napari_hook_implementation
def napari_experimental_provide_dock_widget():
    return [FolderBrowser]


if __name__ == "__main__":
    # Simple test main function to run the widget in the debugger
    import napari

    viewer = napari.Viewer()
    napari.run()