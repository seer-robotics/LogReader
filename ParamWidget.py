# -*- coding: utf-8 -*-
"""Read-only searchable view of parameters stored in robot.param."""
import os
import sqlite3

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import pyqtSignal

from paramutils import find_parameter_database, read_parameter_database


CHANGED_ROLE = QtCore.Qt.UserRole + 1


class ParameterFilterProxyModel(QtCore.QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._changed_only = False

    def setChangedOnly(self, enabled):
        enabled = bool(enabled)
        if self._changed_only == enabled:
            return
        self._changed_only = enabled
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        if self._changed_only:
            value_index = self.sourceModel().index(
                source_row, 2, source_parent)
            if not value_index.data(CHANGED_ROLE):
                return False
        return super().filterAcceptsRow(source_row, source_parent)


class ParameterWidget(QtWidgets.QMainWindow):
    hiddened = pyqtSignal('PyQt_PyObject')

    HEADERS = ('Module', 'Parameter', 'Value', 'Default', 'Type', 'Mutable')

    def __init__(self, parent=None):
        super().__init__(parent)
        self.database_path = None
        self.setWindowTitle('Robot Parameters')
        self.resize(1050, 650)
        self.setMinimumSize(700, 420)

        central_widget = QtWidgets.QWidget(self)
        self.setCentralWidget(central_widget)
        layout = QtWidgets.QVBoxLayout(central_widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self.search_edit = QtWidgets.QLineEdit(self)
        self.search_edit.setPlaceholderText('Search parameters')
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self._filterChanged)
        self.changed_only_check = QtWidgets.QCheckBox('Changed only', self)
        self.changed_only_check.toggled.connect(self._changedOnlyToggled)
        filter_layout = QtWidgets.QHBoxLayout()
        filter_layout.setContentsMargins(0, 0, 0, 0)
        filter_layout.addWidget(self.search_edit, 1)
        filter_layout.addWidget(self.changed_only_check)
        layout.addLayout(filter_layout)

        self.source_model = QtGui.QStandardItemModel(0, len(self.HEADERS), self)
        self.source_model.setHorizontalHeaderLabels(self.HEADERS)
        self.proxy_model = ParameterFilterProxyModel(self)
        self.proxy_model.setSourceModel(self.source_model)
        self.proxy_model.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.proxy_model.setFilterKeyColumn(-1)
        self.proxy_model.setSortCaseSensitivity(QtCore.Qt.CaseInsensitive)

        self.table = QtWidgets.QTableView(self)
        self.table.setModel(self.proxy_model)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectItems)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setSortingEnabled(True)
        self.table.setWordWrap(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(24)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.Interactive)
        self.table.setColumnWidth(0, 160)
        self.table.setColumnWidth(1, 260)
        self.table.setColumnWidth(2, 180)
        self.table.setColumnWidth(3, 180)
        self.table.setColumnWidth(4, 100)
        self.table.setColumnWidth(5, 80)
        layout.addWidget(self.table)

        self.result_label = QtWidgets.QLabel('0 parameters', self)
        self.statusBar().addPermanentWidget(self.result_label)

        QtWidgets.QShortcut(QtGui.QKeySequence.Find, self,
                            activated=self._focusSearch)
        QtWidgets.QShortcut(QtGui.QKeySequence.Copy, self.table,
                            activated=self.copySelection)

        self.table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._showContextMenu)

    def loadFromLogFiles(self, log_files):
        database_path = find_parameter_database(log_files)
        if database_path is None:
            self.clear('params/robot.param not found')
            return False
        return self.loadDatabase(database_path)

    def loadDatabase(self, database_path):
        try:
            records = read_parameter_database(database_path)
        except (OSError, sqlite3.Error) as error:
            self.clear('Cannot read robot.param: {}'.format(error))
            return False

        self.database_path = os.path.abspath(database_path)
        self.source_model.removeRows(0, self.source_model.rowCount())
        changed_brush = QtGui.QBrush(QtGui.QColor('#fff1c2'))
        immutable_brush = QtGui.QBrush(QtGui.QColor('#777777'))
        for record in records:
            values = (
                record.module,
                record.key,
                record.value,
                record.default_value,
                record.type_name,
                'Yes' if record.mutable else 'No',
            )
            items = [QtGui.QStandardItem(value) for value in values]
            for item in items:
                item.setToolTip(item.text())
            value_changed = record.value != record.default_value
            items[2].setData(value_changed, CHANGED_ROLE)
            if value_changed:
                items[2].setBackground(changed_brush)
                items[2].setFont(self._boldFont(items[2].font()))
            if not record.mutable:
                for item in items:
                    item.setForeground(immutable_brush)
            items[5].setTextAlignment(QtCore.Qt.AlignCenter)
            self.source_model.appendRow(items)

        self.search_edit.clear()
        self.table.sortByColumn(0, QtCore.Qt.AscendingOrder)
        self.setWindowTitle('Robot Parameters - {}'.format(
            os.path.basename(self.database_path)))
        self.statusBar().showMessage(self.database_path)
        self._updateResultCount()
        return True

    @staticmethod
    def _boldFont(font):
        font.setBold(True)
        return font

    def clear(self, message=''):
        self.database_path = None
        self.source_model.removeRows(0, self.source_model.rowCount())
        self.setWindowTitle('Robot Parameters')
        self.statusBar().showMessage(message)
        self._updateResultCount()

    def _filterChanged(self, text):
        self.proxy_model.setFilterFixedString(text)
        self._updateResultCount()

    def _changedOnlyToggled(self, enabled):
        self.proxy_model.setChangedOnly(enabled)
        self._updateResultCount()

    def _updateResultCount(self):
        visible_count = self.proxy_model.rowCount()
        total_count = self.source_model.rowCount()
        if visible_count == total_count:
            self.result_label.setText('{} parameters'.format(total_count))
        else:
            self.result_label.setText(
                '{} / {} parameters'.format(visible_count, total_count))

    def _focusSearch(self):
        self.search_edit.setFocus()
        self.search_edit.selectAll()

    def copySelection(self):
        indexes = self.table.selectionModel().selectedIndexes()
        if not indexes:
            return
        indexes.sort(key=lambda index: (index.row(), index.column()))
        rows = {}
        for index in indexes:
            rows.setdefault(index.row(), []).append(index.data())
        text = '\n'.join(
            '\t'.join(str(value) for value in values)
            for _, values in sorted(rows.items()))
        QtWidgets.QApplication.clipboard().setText(text)

    def _showContextMenu(self, position):
        if not self.table.selectionModel().selectedIndexes():
            return
        menu = QtWidgets.QMenu(self)
        copy_action = menu.addAction('Copy')
        copy_action.triggered.connect(self.copySelection)
        menu.exec_(self.table.viewport().mapToGlobal(position))

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.hiddened.emit(True)
