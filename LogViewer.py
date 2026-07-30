# -*- coding: utf-8 -*-
"""Virtualized log viewer with incremental search."""
from bisect import bisect_left
import os
import re

from PyQt5 import QtCore, QtGui, QtWidgets

from loglibPlus import (open_log_file, rbktimetodate,
                        sort_log_lines_by_timestamp)


RAW_LINE_ROLE = QtCore.Qt.UserRole + 1


def compile_search_pattern(query, use_regex=False, case_sensitive=False):
    """Build the pattern shared by navigation and visible-row highlighting."""
    if not query:
        return None
    expression = query if use_regex else re.escape(query)
    flags = 0 if case_sensitive else re.IGNORECASE
    return re.compile(expression, flags)


def find_match_ranges(pattern, text):
    """Return non-empty match spans suitable for text highlighting."""
    if pattern is None:
        return []
    return [match.span() for match in pattern.finditer(text)
            if match.end() > match.start()]


class LogLineModel(QtCore.QAbstractListModel):
    """Expose log lines on demand without building a second text document."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.lines = []
        self._visible_rows = None
        self._line_number_width = 1
        font = QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont)
        metrics = QtGui.QFontMetrics(font)
        self._row_size = QtCore.QSize(
            metrics.horizontalAdvance('M') * 4096,
            max(20, metrics.height() + 4))

    def setLines(self, lines):
        self.beginResetModel()
        self.lines = lines if lines is not None else []
        self._visible_rows = None
        self._line_number_width = max(1, len(str(len(self.lines))))
        self.endResetModel()

    def setVisibleRows(self, source_rows):
        self.beginResetModel()
        self._visible_rows = (None if source_rows is None
                              else list(source_rows))
        self.endResetModel()

    def sourceRow(self, index):
        if not index.isValid():
            return -1
        row = index.row()
        if self._visible_rows is None:
            return row if row < len(self.lines) else -1
        if 0 <= row < len(self._visible_rows):
            return self._visible_rows[row]
        return -1

    def indexForSourceRow(self, source_row):
        if not 0 <= source_row < len(self.lines):
            return QtCore.QModelIndex()
        if self._visible_rows is None:
            return self.index(source_row, 0)
        position = bisect_left(self._visible_rows, source_row)
        if (position < len(self._visible_rows)
                and self._visible_rows[position] == source_row):
            return self.index(position, 0)
        return QtCore.QModelIndex()

    def visibleSourceRows(self):
        return self._visible_rows

    def rowCount(self, parent=QtCore.QModelIndex()):
        if parent.isValid():
            return 0
        if self._visible_rows is None:
            return len(self.lines)
        return len(self._visible_rows)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        source_row = self.sourceRow(index)
        if source_row < 0:
            return None
        line = self.lines[source_row]
        if role == QtCore.Qt.DisplayRole:
            return '{:>{width}}  {}'.format(
                source_row + 1,
                line.rstrip('\r\n'),
                width=self._line_number_width)
        if role in (RAW_LINE_ROLE, QtCore.Qt.ToolTipRole):
            return line.rstrip('\r\n')
        if role == QtCore.Qt.SizeHintRole:
            return self._row_size
        return None


class LogHighlightDelegate(QtWidgets.QStyledItemDelegate):
    """Paint search matches without materializing formatted log documents."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pattern = None

    def setSearchPattern(self, pattern):
        self._pattern = pattern
        parent = self.parent()
        if parent is not None and hasattr(parent, 'viewport'):
            parent.viewport().update()

    def paint(self, painter, option, index):
        display_text = index.data(QtCore.Qt.DisplayRole)
        raw_text = index.data(RAW_LINE_ROLE)
        ranges = find_match_ranges(self._pattern, raw_text or '')
        if not ranges:
            super().paint(painter, option, index)
            return

        text = display_text or ''
        prefix_length = max(0, len(text) - len(raw_text or ''))
        opt = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        opt.text = ''
        style = (opt.widget.style() if opt.widget is not None
                 else QtWidgets.QApplication.style())

        painter.save()
        painter.setClipRect(option.rect)
        style.drawControl(QtWidgets.QStyle.CE_ItemViewItem,
                          opt, painter, opt.widget)
        text_rect = style.subElementRect(
            QtWidgets.QStyle.SE_ItemViewItemText, opt, opt.widget)

        highlight_format = QtGui.QTextCharFormat()
        highlight_format.setBackground(QtGui.QColor('#ffd54f'))
        highlight_format.setForeground(QtGui.QColor('#202020'))
        format_ranges = []
        for start, end in ranges:
            format_range = QtGui.QTextLayout.FormatRange()
            format_range.start = prefix_length + start
            format_range.length = end - start
            format_range.format = highlight_format
            format_ranges.append(format_range)

        text_option = QtGui.QTextOption()
        text_option.setWrapMode(QtGui.QTextOption.NoWrap)
        layout = QtGui.QTextLayout(text, opt.font)
        layout.setTextOption(text_option)
        layout.setFormats(format_ranges)
        layout.beginLayout()
        line = layout.createLine()
        line.setLineWidth(1000000)
        layout.endLayout()

        color_role = (QtGui.QPalette.HighlightedText
                      if opt.state & QtWidgets.QStyle.State_Selected
                      else QtGui.QPalette.Text)
        painter.setPen(opt.palette.color(color_role))
        y = text_rect.y() + (text_rect.height() - line.height()) / 2.0
        layout.draw(painter, QtCore.QPointF(text_rect.x(), y))
        painter.restore()


class LogViewer(QtWidgets.QWidget):
    hiddened = QtCore.pyqtSignal('PyQt_PyObject')
    moveHereSignal = QtCore.pyqtSignal('PyQt_PyObject')

    SEARCH_BATCH_SIZE = 20000
    FILTER_BATCH_SIZE = 20000

    def __init__(self):
        super().__init__()
        self.lines = []
        self.title = 'LogViewer'
        self.moveHere_flag = False
        self._search_generation = 0
        self._search_state = None
        self._last_search_signature = None
        self._search_pattern = None
        self._search_error = None
        self._filter_generation = 0
        self._filter_state = None
        self.InitWindow()
        self.resize(900, 800)

    def InitWindow(self):
        self.setWindowTitle(self.title)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        search_layout = QtWidgets.QHBoxLayout()
        self.find_edit = QtWidgets.QLineEdit(self)
        self.find_edit.setPlaceholderText('Search logs')
        self.find_edit.setClearButtonEnabled(True)
        self.find_edit.setStyleSheet(
            'QLineEdit[invalidSearch="true"] {'
            ' border: 1px solid #c62828; background-color: #fff4f4; }')
        self.find_edit.returnPressed.connect(self.findDown)
        self.find_edit.textChanged.connect(self._searchTextChanged)

        self.regex_checkbox = QtWidgets.QCheckBox('Regex', self)
        self.regex_checkbox.setToolTip('Treat the search text as a regular expression')
        self.regex_checkbox.toggled.connect(self._searchOptionsChanged)
        self.case_checkbox = QtWidgets.QCheckBox('Case sensitive', self)
        self.case_checkbox.setToolTip('Match uppercase and lowercase exactly')
        self.case_checkbox.toggled.connect(self._searchOptionsChanged)
        self.filter_checkbox = QtWidgets.QCheckBox('Only matches', self)
        self.filter_checkbox.setToolTip(
            'Only show lines matching the search text')
        self.filter_checkbox.toggled.connect(self._filterToggled)

        self.find_up = QtWidgets.QToolButton(self)
        self.find_up.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_ArrowUp))
        self.find_up.setToolTip('Previous match')
        self.find_up.clicked.connect(self.findUp)
        self.find_down = QtWidgets.QToolButton(self)
        self.find_down.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_ArrowDown))
        self.find_down.setToolTip('Next match')
        self.find_down.clicked.connect(self.findDown)
        self.position_label = QtWidgets.QLabel('0 lines', self)
        self.position_label.setMinimumWidth(220)
        self.position_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        search_layout.addWidget(self.find_edit, 1)
        search_layout.addWidget(self.regex_checkbox)
        search_layout.addWidget(self.case_checkbox)
        search_layout.addWidget(self.filter_checkbox)
        search_layout.addWidget(self.find_up)
        search_layout.addWidget(self.find_down)
        search_layout.addWidget(self.position_label)
        layout.addLayout(search_layout)

        self.line_model = LogLineModel(self)
        self.list_view = QtWidgets.QListView(self)
        self.list_view.setModel(self.line_model)
        self.highlight_delegate = LogHighlightDelegate(self.list_view)
        self.list_view.setItemDelegate(self.highlight_delegate)
        self.list_view.setFont(
            QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont))
        self.list_view.setUniformItemSizes(True)
        self.list_view.setWordWrap(False)
        self.list_view.setTextElideMode(QtCore.Qt.ElideNone)
        self.list_view.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection)
        self.list_view.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.list_view.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerItem)
        self.list_view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.list_view.customContextMenuRequested.connect(self._showContextMenu)
        self.list_view.selectionModel().currentChanged.connect(self._currentChanged)
        self.list_view.selectionModel().selectionChanged.connect(
            self._selectionChanged)
        layout.addWidget(self.list_view)

        QtWidgets.QShortcut(QtGui.QKeySequence.Find, self,
                            activated=self._focusSearch)
        QtWidgets.QShortcut(QtGui.QKeySequence.Copy, self.list_view,
                            activated=self.copySelectedLines)
        QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_F3), self,
                            activated=self.findDown)
        QtWidgets.QShortcut(
            QtGui.QKeySequence(QtCore.Qt.SHIFT + QtCore.Qt.Key_F3), self,
            activated=self.findUp)

    def setLines(self, lines):
        if lines is self.lines and self.line_model.lines is lines:
            return
        self._cancelSearch()
        self._cancelFilter()
        self._last_search_signature = None
        self.lines = lines if lines is not None else []
        self.line_model.setLines(self.lines)
        self.setWindowTitle('{} - {} lines'.format(self.title, len(self.lines)))
        if self.filter_checkbox.isChecked():
            self._startFilter()
        else:
            self.position_label.setText('{} lines'.format(len(self.lines)))

    def setText(self, lines):
        """Backward-compatible alias for callers that previously loaded text."""
        self.setLines(lines)

    def setLineNum(self, line_number):
        if self.moveHere_flag:
            self.moveHere_flag = False
            return
        self._selectLine(line_number)

    def _selectLine(self, line_number):
        if not self.lines:
            return
        line_number = max(0, min(int(line_number), len(self.lines) - 1))
        index = self.line_model.indexForSourceRow(line_number)
        if not index.isValid():
            return
        selection_model = self.list_view.selectionModel()
        selection_model.setCurrentIndex(
            index, QtCore.QItemSelectionModel.ClearAndSelect
            | QtCore.QItemSelectionModel.Rows)
        self.list_view.scrollTo(index, QtWidgets.QAbstractItemView.PositionAtCenter)
        self._updatePosition()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.hiddened.emit(True)

    def hideEvent(self, event):
        self._cancelSearch()
        super().hideEvent(event)

    def readFilies(self, files):
        self.lines = []
        for file in files:
            if not os.path.exists(file):
                continue
            try:
                with open_log_file(file, 'rb') as stream:
                    self.readData(stream, file)
            except (OSError, EOFError):
                continue
        lines = self.lines
        self.lines = []
        self.setLines(sort_log_lines_by_timestamp(lines))

    def readData(self, stream, file):
        for line in stream:
            try:
                decoded_line = line.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    decoded_line = line.decode('gbk')
                except UnicodeDecodeError:
                    print('{} {}:{}'.format(
                        file, 'Skipped due to decoding failure!', line))
                    continue
            self.lines.append(decoded_line)

    def _showContextMenu(self, position):
        index = self.list_view.indexAt(position)
        if index.isValid():
            selection_model = self.list_view.selectionModel()
            if selection_model.isSelected(index):
                selection_model.setCurrentIndex(
                    index, QtCore.QItemSelectionModel.NoUpdate)
            else:
                selection_model.setCurrentIndex(
                    index, QtCore.QItemSelectionModel.ClearAndSelect
                    | QtCore.QItemSelectionModel.Rows)
        if not self.list_view.currentIndex().isValid():
            return
        menu = QtWidgets.QMenu(self)
        selected_count = self.selectedRowCount()
        copy_action = menu.addAction(
            'Copy selected lines' if selected_count > 1 else 'Copy line')
        move_action = menu.addAction('Move Here')
        selected_action = menu.exec_(
            self.list_view.viewport().mapToGlobal(position))
        if selected_action == copy_action:
            self.copySelectedLines()
        elif selected_action == move_action:
            self.moveHere()

    def selectedSourceRows(self):
        rows = {
            self.line_model.sourceRow(index)
            for index in self.list_view.selectionModel().selectedIndexes()
        }
        rows.discard(-1)
        if not rows:
            current_row = self._currentSourceRow()
            if current_row >= 0:
                rows.add(current_row)
        return sorted(rows)

    def selectedRowCount(self):
        return sum(
            selection_range.bottom() - selection_range.top() + 1
            for selection_range in
            self.list_view.selectionModel().selection())

    def copySelectedLines(self):
        rows = self.selectedSourceRows()
        if rows:
            QtWidgets.QApplication.clipboard().setText('\n'.join(
                self.lines[row].rstrip('\r\n') for row in rows))

    def copyCurrentLine(self):
        """Backward-compatible alias that now copies all selected rows."""
        self.copySelectedLines()

    def moveHere(self):
        index = self.list_view.currentIndex()
        if not index.isValid():
            return
        line = index.data(RAW_LINE_ROLE)
        match = re.match(r'\[(.*?)\].*', line)
        if match:
            self.moveHere_flag = True
            self.moveHereSignal.emit(rbktimetodate(match.group(1)))

    def _currentSourceRow(self):
        return self.line_model.sourceRow(self.list_view.currentIndex())

    def _setVisibleRows(self, source_rows):
        selected_rows = self.selectedSourceRows()
        current_row = self._currentSourceRow()
        self.line_model.setVisibleRows(source_rows)

        selection_model = self.list_view.selectionModel()
        selection_model.clearSelection()
        for source_row in selected_rows:
            index = self.line_model.indexForSourceRow(source_row)
            if index.isValid():
                selection_model.select(
                    index, QtCore.QItemSelectionModel.Select
                    | QtCore.QItemSelectionModel.Rows)
        current_index = self.line_model.indexForSourceRow(current_row)
        if current_index.isValid():
            selection_model.setCurrentIndex(
                current_index, QtCore.QItemSelectionModel.NoUpdate)

    def _filterToggled(self, checked):
        self._cancelSearch()
        self._last_search_signature = None
        if checked:
            self._startFilter()
        else:
            self._cancelFilter()
            self._setVisibleRows(None)
            self._updatePosition()

    def _startFilter(self):
        self._cancelFilter()
        if not self.filter_checkbox.isChecked():
            return
        if self._search_error is not None:
            self._setVisibleRows([])
            self._showSearchError()
            return
        if self._search_pattern is None:
            self._setVisibleRows(None)
            self._updatePosition()
            return

        generation = self._filter_generation
        self._filter_state = {
            'pattern': self._search_pattern,
            'row': 0,
            'matches': [],
        }
        self.position_label.setText('Filtering...')
        QtCore.QTimer.singleShot(
            0, lambda: self._filterBatch(generation))

    def _filterBatch(self, generation):
        if (generation != self._filter_generation
                or self._filter_state is None):
            return
        state = self._filter_state
        total = len(self.lines)
        batch_end = min(total, state['row'] + self.FILTER_BATCH_SIZE)
        while state['row'] < batch_end:
            source_row = state['row']
            if state['pattern'].search(
                    self.lines[source_row].rstrip('\r\n')) is not None:
                state['matches'].append(source_row)
            state['row'] += 1

        if state['row'] >= total:
            matches = state['matches']
            self._filter_state = None
            self._setVisibleRows(matches)
            self._updatePosition()
            return
        QtCore.QTimer.singleShot(
            0, lambda: self._filterBatch(generation))

    def _cancelFilter(self):
        self._filter_generation += 1
        self._filter_state = None

    def findUp(self):
        self._startSearch(-1)

    def findDown(self):
        self._startSearch(1)

    def _startSearch(self, direction):
        query = self.find_edit.text()
        if not query or not self.lines:
            self.position_label.setText('{} lines'.format(len(self.lines)))
            return

        self._updateSearchPattern()
        if self._search_error is not None:
            self._showSearchError()
            return

        if self.filter_checkbox.isChecked():
            if self._filter_state is not None:
                self.position_label.setText('Filtering...')
                return
            visible_rows = self.line_model.visibleSourceRows()
            if visible_rows is None:
                visible_rows = list(range(len(self.lines)))
            if not visible_rows:
                self.position_label.setText('No matches')
                return
            current_visible_row = self.list_view.currentIndex().row()
            signature = self._searchSignature()
            same_search = (signature == self._last_search_signature
                           and current_visible_row >= 0)
            if current_visible_row < 0:
                target_row = 0 if direction > 0 else len(visible_rows) - 1
            elif same_search:
                target_row = ((current_visible_row + direction)
                              % len(visible_rows))
            else:
                target_row = current_visible_row
            self._last_search_signature = signature
            self._selectLine(visible_rows[target_row])
            return

        current_row = self._currentSourceRow()
        signature = self._searchSignature()
        same_search = (signature == self._last_search_signature
                       and current_row >= 0)
        if current_row < 0:
            start_row = 0 if direction > 0 else len(self.lines) - 1
        elif same_search:
            start_row = (current_row + direction) % len(self.lines)
        else:
            start_row = current_row

        self._search_generation += 1
        generation = self._search_generation
        self._last_search_signature = signature
        self._search_state = {
            'pattern': self._search_pattern,
            'direction': direction,
            'row': start_row,
            'scanned': 0,
        }
        self.position_label.setText('Searching...')
        QtCore.QTimer.singleShot(
            0, lambda: self._searchBatch(generation))

    def _searchBatch(self, generation):
        if generation != self._search_generation or self._search_state is None:
            return
        state = self._search_state
        total = len(self.lines)
        batch_end = min(total, state['scanned'] + self.SEARCH_BATCH_SIZE)
        while state['scanned'] < batch_end:
            row = state['row']
            line = self.lines[row].rstrip('\r\n')
            if state['pattern'].search(line) is not None:
                self._search_state = None
                self._selectLine(row)
                return
            state['row'] = (row + state['direction']) % total
            state['scanned'] += 1

        if state['scanned'] >= total:
            self._search_state = None
            self.position_label.setText('No matches')
            return
        QtCore.QTimer.singleShot(
            0, lambda: self._searchBatch(generation))

    def _searchTextChanged(self, _text):
        self._cancelSearch()
        self._last_search_signature = None
        self._updateSearchPattern()
        if self.filter_checkbox.isChecked():
            self._startFilter()
        if self._search_error is not None:
            self._showSearchError()
        elif not self.filter_checkbox.isChecked():
            self._updatePosition()

    def _searchOptionsChanged(self, _checked):
        self._searchTextChanged(self.find_edit.text())

    def _searchSignature(self):
        return (self.find_edit.text(),
                self.regex_checkbox.isChecked(),
                self.case_checkbox.isChecked())

    def _updateSearchPattern(self):
        try:
            self._search_pattern = compile_search_pattern(
                self.find_edit.text(),
                use_regex=self.regex_checkbox.isChecked(),
                case_sensitive=self.case_checkbox.isChecked())
            self._search_error = None
        except re.error as error:
            self._search_pattern = None
            self._search_error = str(error)

        invalid = self._search_error is not None
        self.find_edit.setProperty('invalidSearch', invalid)
        self.find_edit.setToolTip(
            'Invalid regular expression: {}'.format(self._search_error)
            if invalid else '')
        self.find_edit.style().unpolish(self.find_edit)
        self.find_edit.style().polish(self.find_edit)
        self.highlight_delegate.setSearchPattern(self._search_pattern)

    def _showSearchError(self):
        self.position_label.setText('Invalid regular expression')

    def _cancelSearch(self):
        self._search_generation += 1
        self._search_state = None

    def _currentChanged(self, current, previous):
        self._updatePosition()

    def _selectionChanged(self, selected, deselected):
        self._updatePosition()

    def _updatePosition(self):
        if self._search_error is not None and self.find_edit.text():
            self._showSearchError()
            return
        if self._filter_state is not None:
            self.position_label.setText('Filtering...')
            return
        selected_count = self.selectedRowCount()
        visible_count = self.line_model.rowCount()
        if selected_count > 1:
            if self.filter_checkbox.isChecked():
                self.position_label.setText(
                    '{} selected | {} / {} lines'.format(
                        selected_count, visible_count, len(self.lines)))
            else:
                self.position_label.setText(
                    '{} selected / {} lines'.format(
                        selected_count, len(self.lines)))
            return
        source_row = self._currentSourceRow()
        if source_row >= 0:
            if self.filter_checkbox.isChecked():
                self.position_label.setText(
                    'Line {} | {} / {} lines'.format(
                        source_row + 1, visible_count, len(self.lines)))
            else:
                self.position_label.setText(
                    'Line {} / {}'.format(source_row + 1, len(self.lines)))
        elif self.filter_checkbox.isChecked():
            self.position_label.setText(
                '{} / {} lines'.format(visible_count, len(self.lines)))
        else:
            self.position_label.setText(
                '{} lines'.format(len(self.lines)))

    def _focusSearch(self):
        self.find_edit.setFocus()
        self.find_edit.selectAll()


if __name__ == '__main__':
    import sys

    app = QtWidgets.QApplication(sys.argv)
    view = LogViewer()
    view.readFilies(['test1.log'])
    view.show()
    sys.exit(app.exec_())
