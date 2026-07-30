# -*- coding: utf-8 -*-
"""Virtualized categorized viewer for parsed log events."""
from PyQt5 import QtCore, QtGui, QtWidgets


EVENT_TIME_ROLE = QtCore.Qt.UserRole + 1
EVENT_CONTENT_ROLE = QtCore.Qt.UserRole + 2

EVENT_CATEGORIES = (
    ('fatal', 'FATAL'),
    ('error', 'ERROR'),
    ('warning', 'WARNING'),
    ('notice', 'NOTICE'),
    ('taskstart', 'TASK START'),
    ('taskfinish', 'TASK FINISHED'),
    ('service', 'SERVICE'),
)


class EventTableModel(QtCore.QAbstractTableModel):
    """Expose event lists without creating a table item for every row."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.times = []
        self.contents = []
        self._row_count = 0

    def setEvents(self, times, contents):
        self.beginResetModel()
        self.times = times if times is not None else []
        self.contents = contents if contents is not None else []
        self._row_count = min(len(self.times), len(self.contents))
        self.endResetModel()

    def rowCount(self, parent=QtCore.QModelIndex()):
        return 0 if parent.isValid() else self._row_count

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 0 if parent.isValid() else 2

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < self._row_count:
            return None
        event_time = self.times[index.row()]
        content = self.contents[index.row()].rstrip('\r\n')
        if role == QtCore.Qt.DisplayRole:
            if index.column() == 0:
                return event_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            if index.column() == 1:
                return content
        if role == EVENT_TIME_ROLE:
            return event_time
        if role in (EVENT_CONTENT_ROLE, QtCore.Qt.ToolTipRole):
            return content
        return None

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return ('Time', 'Event')[section]
        return None


class EventViewer(QtWidgets.QWidget):
    hiddened = QtCore.pyqtSignal('PyQt_PyObject')
    moveHereSignal = QtCore.pyqtSignal('PyQt_PyObject')

    def __init__(self, parent=None):
        super().__init__(parent)
        self.models = {}
        self.proxies = {}
        self.views = {}
        self._tab_keys = []
        self._initWindow()
        self.resize(1200, 760)

    def _initWindow(self):
        self.setWindowTitle('Event Viewer')
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self.filter_edit = QtWidgets.QLineEdit(self)
        self.filter_edit.setPlaceholderText('Filter events')
        self.filter_edit.setClearButtonEnabled(True)
        self.filter_edit.textChanged.connect(self._filterChanged)
        layout.addWidget(self.filter_edit)

        self.tabs = QtWidgets.QTabWidget(self)
        fixed_font = QtGui.QFontDatabase.systemFont(
            QtGui.QFontDatabase.FixedFont)
        for key, label in EVENT_CATEGORIES:
            model = EventTableModel(self)
            proxy = QtCore.QSortFilterProxyModel(self)
            proxy.setSourceModel(model)
            proxy.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)
            proxy.setFilterKeyColumn(-1)

            view = QtWidgets.QTableView(self.tabs)
            view.setModel(proxy)
            view.setFont(fixed_font)
            view.setWordWrap(False)
            view.setAlternatingRowColors(True)
            view.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
            view.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
            view.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
            view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
            view.customContextMenuRequested.connect(
                lambda position, table=view:
                self._showContextMenu(table, position))
            view.verticalHeader().setVisible(False)
            view.horizontalHeader().setStretchLastSection(True)
            view.setColumnWidth(0, 190)

            self.models[key] = model
            self.proxies[key] = proxy
            self.views[key] = view
            self._tab_keys.append(key)
            self.tabs.addTab(view, '{} (0)'.format(label))
        self.tabs.currentChanged.connect(self._updateCount)
        layout.addWidget(self.tabs, 1)

        self.result_label = QtWidgets.QLabel('0 events', self)
        self.result_label.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        layout.addWidget(self.result_label)

        QtWidgets.QShortcut(QtGui.QKeySequence.Find, self,
                            activated=self._focusFilter)
        QtWidgets.QShortcut(QtGui.QKeySequence.Copy, self,
                            activated=self.copyCurrentEvent)

    def setEvents(self, event_sources):
        total = 0
        for tab_index, (key, label) in enumerate(EVENT_CATEGORIES):
            source = event_sources.get(key) if event_sources else None
            if source is None:
                times, contents = [], []
            else:
                times = source.t()
                contents = source.content()[0]
            self.models[key].setEvents(times, contents)
            count = self.models[key].rowCount()
            total += count
            self.tabs.setTabText(
                tab_index, '{} ({})'.format(label, count))
        self.setWindowTitle('Event Viewer - {} events'.format(total))
        self._updateCount()

    def _filterChanged(self, text):
        for proxy in self.proxies.values():
            proxy.setFilterFixedString(text)
        self._updateCount()

    def _currentView(self):
        index = self.tabs.currentIndex()
        if not 0 <= index < len(self._tab_keys):
            return None
        return self.views[self._tab_keys[index]]

    def _showContextMenu(self, view, position):
        index = view.indexAt(position)
        if not index.isValid():
            return
        view.setCurrentIndex(index)
        menu = QtWidgets.QMenu(self)
        move_action = menu.addAction('Move Here')
        copy_action = menu.addAction('Copy event')
        selected = menu.exec_(view.viewport().mapToGlobal(position))
        if selected == move_action:
            self.moveCurrentEvent(view)
        elif selected == copy_action:
            self.copyCurrentEvent(view)

    def moveCurrentEvent(self, view=None):
        view = view or self._currentView()
        if view is None or not view.currentIndex().isValid():
            return
        event_time = view.currentIndex().data(EVENT_TIME_ROLE)
        if event_time is not None:
            self.moveHereSignal.emit(event_time)

    def copyCurrentEvent(self, view=None):
        view = view or self._currentView()
        if view is None or not view.currentIndex().isValid():
            return
        content = view.currentIndex().data(EVENT_CONTENT_ROLE)
        if content is not None:
            QtWidgets.QApplication.clipboard().setText(content)

    def _updateCount(self):
        index = self.tabs.currentIndex()
        if not 0 <= index < len(self._tab_keys):
            self.result_label.setText('0 events')
            return
        key = self._tab_keys[index]
        visible = self.proxies[key].rowCount()
        total = self.models[key].rowCount()
        if visible == total:
            self.result_label.setText('{} events'.format(total))
        else:
            self.result_label.setText(
                '{} / {} events'.format(visible, total))

    def _focusFilter(self):
        self.filter_edit.setFocus()
        self.filter_edit.selectAll()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.hiddened.emit(True)
