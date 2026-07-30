# -*- coding: utf-8 -*-
import os
import re
import tempfile
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PyQt5 import QtCore, QtGui, QtTest, QtWidgets

from LogViewer import (LogViewer, compile_search_pattern,
                       find_match_ranges)


class TestSearchPattern(unittest.TestCase):
    def test_plain_text_escapes_regular_expression_characters(self):
        pattern = compile_search_pattern('value[1]')

        self.assertIsNotNone(pattern.search('VALUE[1]'))
        self.assertIsNone(pattern.search('value1'))

    def test_case_sensitive_matching(self):
        pattern = compile_search_pattern('MaxSpeed', case_sensitive=True)

        self.assertIsNotNone(pattern.search('MaxSpeed=1.0'))
        self.assertIsNone(pattern.search('maxspeed=1.0'))

    def test_regular_expression_matching(self):
        pattern = compile_search_pattern(
            r'GoodsPos\.(x|y)\s*=\s*-?\d+(\.\d+)?', use_regex=True)

        self.assertIsNotNone(pattern.search('GoodsPos.x = -1.25'))
        self.assertIsNone(pattern.search('GoodsPos.theta = 90'))

    def test_match_ranges_include_every_non_empty_match(self):
        pattern = compile_search_pattern('alpha')

        self.assertEqual(
            [(0, 5), (6, 11)],
            find_match_ranges(pattern, 'Alpha ALPHA'))

    def test_invalid_regular_expression_raises(self):
        with self.assertRaises(re.error):
            compile_search_pattern('[', use_regex=True)


class TestLogViewerSearch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = (QtWidgets.QApplication.instance()
                   or QtWidgets.QApplication([]))

    def setUp(self):
        self.viewer = LogViewer()
        self.viewer.setLines([
            'Alpha first\n',
            'second alpha\n',
            'third ALPHA\n',
            'GoodsPos.x = -1.25\n',
        ])

    def tearDown(self):
        self.viewer.hide()
        self.viewer.deleteLater()
        self.app.processEvents()

    def _finish_search(self):
        for _ in range(20):
            self.app.processEvents()
            if self.viewer._search_state is None:
                return
        self.fail('incremental search did not finish')

    def _finish_filter(self):
        for _ in range(100):
            self.app.processEvents()
            if self.viewer._filter_state is None:
                return
        self.fail('incremental filter did not finish')

    def test_default_search_is_case_insensitive_and_wraps(self):
        self.viewer.find_edit.setText('alpha')

        self.viewer.findDown()
        self._finish_search()
        self.assertEqual(0, self.viewer.list_view.currentIndex().row())

        self.viewer.findDown()
        self._finish_search()
        self.assertEqual(1, self.viewer.list_view.currentIndex().row())

        self.viewer.findUp()
        self._finish_search()
        self.assertEqual(0, self.viewer.list_view.currentIndex().row())

    def test_case_sensitive_search(self):
        self.viewer.find_edit.setText('alpha')
        self.viewer.case_checkbox.setChecked(True)

        self.viewer.findDown()
        self._finish_search()

        self.assertEqual(1, self.viewer.list_view.currentIndex().row())

    def test_regular_expression_search(self):
        self.viewer.regex_checkbox.setChecked(True)
        self.viewer.find_edit.setText(r'GoodsPos\.[xy]\s*=\s*-?\d+\.\d+')

        self.viewer.findDown()
        self._finish_search()

        self.assertEqual(3, self.viewer.list_view.currentIndex().row())

    def test_invalid_regular_expression_is_reported(self):
        self.viewer.regex_checkbox.setChecked(True)
        self.viewer.find_edit.setText('[')

        self.viewer.findDown()

        self.assertIsNone(self.viewer._search_state)
        self.assertIsNone(self.viewer.highlight_delegate._pattern)
        self.assertEqual(
            'Invalid regular expression', self.viewer.position_label.text())

    def test_visible_matches_are_painted_with_highlight_color(self):
        self.viewer.resize(700, 300)
        self.viewer.find_edit.setText('alpha')
        self.viewer.show()
        self.app.processEvents()

        image = self.viewer.grab().toImage().convertToFormat(
            QtGui.QImage.Format_ARGB32)
        highlight = QtGui.QColor('#ffd54f').rgb()
        highlighted_pixels = sum(
            1
            for y in range(image.height())
            for x in range(image.width())
            if image.pixel(x, y) == highlight)

        self.assertGreater(highlighted_pixels, 0)

    def test_ctrl_click_selects_non_contiguous_lines(self):
        self.viewer.resize(700, 300)
        self.viewer.show()
        self.app.processEvents()
        first = self.viewer.line_model.index(0, 0)
        third = self.viewer.line_model.index(2, 0)

        QtTest.QTest.mouseClick(
            self.viewer.list_view.viewport(), QtCore.Qt.LeftButton,
            QtCore.Qt.NoModifier,
            self.viewer.list_view.visualRect(first).center())
        QtTest.QTest.mouseClick(
            self.viewer.list_view.viewport(), QtCore.Qt.LeftButton,
            QtCore.Qt.ControlModifier,
            self.viewer.list_view.visualRect(third).center())

        self.assertEqual([0, 2], self.viewer.selectedSourceRows())
        self.assertIn('2 selected', self.viewer.position_label.text())

    def test_copy_selected_lines_uses_original_log_order(self):
        selection_model = self.viewer.list_view.selectionModel()
        for row in (2, 0):
            selection_model.select(
                self.viewer.line_model.index(row, 0),
                QtCore.QItemSelectionModel.Select)

        self.viewer.copySelectedLines()

        self.assertEqual(
            'Alpha first\nthird ALPHA',
            QtWidgets.QApplication.clipboard().text())

    def test_filter_only_shows_case_insensitive_matches(self):
        self.viewer.find_edit.setText('alpha')
        self.viewer.filter_checkbox.setChecked(True)
        self._finish_filter()

        self.assertEqual(3, self.viewer.line_model.rowCount())
        self.assertEqual([0, 1, 2],
                         self.viewer.line_model.visibleSourceRows())
        self.assertEqual('3 / 4 lines', self.viewer.position_label.text())

    def test_filter_keeps_original_line_numbers(self):
        self.viewer.find_edit.setText('GoodsPos')
        self.viewer.filter_checkbox.setChecked(True)
        self._finish_filter()

        display = self.viewer.line_model.index(0, 0).data(
            QtCore.Qt.DisplayRole)

        self.assertTrue(display.lstrip().startswith('4  GoodsPos'))

    def test_filter_respects_case_and_regex_options(self):
        self.viewer.find_edit.setText('alpha$')
        self.viewer.regex_checkbox.setChecked(True)
        self.viewer.case_checkbox.setChecked(True)
        self.viewer.filter_checkbox.setChecked(True)
        self._finish_filter()

        self.assertEqual([1], self.viewer.line_model.visibleSourceRows())

    def test_disabling_filter_restores_all_lines(self):
        self.viewer.find_edit.setText('GoodsPos')
        self.viewer.filter_checkbox.setChecked(True)
        self._finish_filter()
        self.viewer.filter_checkbox.setChecked(False)

        self.assertIsNone(self.viewer.line_model.visibleSourceRows())
        self.assertEqual(4, self.viewer.line_model.rowCount())

    def test_search_navigates_filtered_rows(self):
        self.viewer.find_edit.setText('alpha')
        self.viewer.filter_checkbox.setChecked(True)
        self._finish_filter()

        self.viewer.findDown()
        self.assertEqual(0, self.viewer._currentSourceRow())
        self.viewer.findDown()
        self.assertEqual(1, self.viewer._currentSourceRow())

    def test_read_files_orders_overlapping_logs_by_timestamp(self):
        paths = []
        for content in (
                ('[260728 154405.500][1][R][d] later\n'
                 '[260728 154448.385][2][R][d] later end\n'),
                ('[260728 152829.456][3][R][d] early\n'
                 '[260728 154100.468][4][MF][d] target\n')):
            with tempfile.NamedTemporaryFile(
                    suffix='.log', delete=False) as stream:
                stream.write(content.encode('utf-8'))
                paths.append(stream.name)
                self.addCleanup(os.remove, stream.name)

        self.viewer.readFilies(paths)

        self.assertEqual([
            '[260728 152829.456]',
            '[260728 154100.468]',
            '[260728 154405.500]',
            '[260728 154448.385]',
        ], [line[:19] for line in self.viewer.lines])


if __name__ == '__main__':
    unittest.main()
