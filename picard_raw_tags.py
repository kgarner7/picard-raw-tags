PLUGIN_NAME = "Raw Tags"
PLUGIN_AUTHOR = "Kendall Garner"
PLUGIN_DESCRIPTION = """
This plugin is to show raw tags of a file
"""
PLUGIN_VERSION = "0.1"
PLUGIN_API_VERSIONS = ["2.0", "2.1", "2.2", "2.3", "2.4", "2.5", "2.6", "2.7"]
PLUGIN_LICENSE = ["MIT"]
PLUGIN_LICENSE_URL = "https://opensource.org/license/MIT"

from typing import List, Set, Tuple, Union

from PyQt5 import QtCore, QtWidgets

from mutagen import File as MutagenFile
from picard import log
from picard.album import Album
from picard.file import File
from picard.track import Track
from picard.ui.itemviews import BaseAction, register_album_action, register_file_action
from picard.ui import PicardDialog
from picard.ui.ui_infodialog import Ui_InfoDialog
from picard.ui.util import StandardButton


FileDataMap = List[Tuple[str, str, List[Tuple[str, str]]]]


class RawTagTable(QtWidgets.QTableWidget):
    COLUMN_TAG = 0
    COLUMN_VALUE = 1

    def __init__(self, tags: List[Tuple[str, str]], parent=None):
        super().__init__(parent=parent)

        self.setAccessibleName(_("metadata view"))
        self.setAccessibleDescription(_("Displays raw tags for selected files"))
        self.setColumnCount(2)
        self.setHorizontalHeaderLabels((_("Tag"), _("Original Value")))
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.ResizeToContents
        )
        self.horizontalHeader().setSectionsClickable(False)
        self.verticalHeader().setDefaultSectionSize(21)
        self.verticalHeader().setVisible(False)
        self.setHorizontalScrollMode(
            QtWidgets.QAbstractItemView.ScrollMode.ScrollPerPixel
        )
        self.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.setTabKeyNavigation(False)
        self.setStyleSheet("QTableWidget {border: none;}")
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_MacShowFocusRect, True)

        self.setRowCount(len(tags))

        for idx, (key, value) in enumerate(tags):
            tag_item = QtWidgets.QTableWidgetItem()
            tag_item.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled)
            self.setItem(idx, self.COLUMN_TAG, tag_item)
            tag_item.setText(key)

            value_item = QtWidgets.QTableWidgetItem()
            value_item.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled)
            self.setItem(idx, self.COLUMN_VALUE, value_item)
            if not isinstance(value, str):
                stringified = str(value)
                if len(stringified) > 1000:
                    stringified = stringified[:1000] + "..."
                value_item.setText(stringified)
            else:
                value_item.setText(str(value))
            self.setRowHeight(idx, self.sizeHintForRow(idx))


class RawInfoDialog(PicardDialog):

    def __init__(self, data: "FileDataMap", parent=None):
        super().__init__(parent)
        self.data = data
        self.ui = Ui_InfoDialog()
        self.ui.setupUi(self)
        self.ui.buttonBox.addButton(
            StandardButton(StandardButton.CLOSE),
            QtWidgets.QDialogButtonBox.ButtonRole.AcceptRole,
        )
        self.ui.buttonBox.accepted.connect(self.accept)

        self.ui.tabWidget.removeTab(0)
        self.ui.tabWidget.removeTab(0)
        self.ui.tabWidget.removeTab(0)

        for base_filename, path, raw_data in data:
            raw_data.insert(0, ("path", path))
            file_tab = RawTagTable(raw_data)
            file_tab.setObjectName(base_filename)
            self.ui.tabWidget.addTab(file_tab, base_filename)

        self.setWindowTitle(_("Track Info"))


class ShowRawTags(BaseAction):
    NAME = "Show Raw Tags"

    def callback(self, objs) -> None:
        data: "FileDataMap" = []
        seen_paths: Set[str] = set()

        def parse_item(obj: Union[Album, File, Track]):
            if isinstance(obj, File):
                path = obj.filename
                if path in seen_paths:
                    return

                try:
                    mutagenFile = MutagenFile(path)
                    data.append((obj.base_filename, path, mutagenFile.items()))
                except BaseException as e:
                    log.error(f"[{PLUGIN_NAME}] failure parsing file {path}: {e}")

                seen_paths.add(path)
            elif isinstance(obj, Track):
                for file in obj.files:
                    path = file.filename
                    try:
                        if path in seen_paths:
                            return
                        mutagenFile = MutagenFile(path)
                        data.append((file.base_filename, path, mutagenFile.items()))
                    except BaseException as e:
                        log.error(f"[{PLUGIN_NAME}] failure parsing file {path}: {e}")

                    seen_paths.add(path)
            elif isinstance(obj, Album):
                for track_or_file in obj.iterfiles():
                    parse_item(track_or_file)

        for obj in objs:
            parse_item(obj)

        RawInfoDialog(data).exec()


register_file_action(ShowRawTags())
register_album_action(ShowRawTags())
