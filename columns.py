import re
# noinspection PyPep8Naming
import xml.etree.ElementTree as etree
from enum import IntEnum
from sys import stderr
from typing import List, Tuple

import pytest
from markdown.blockprocessors import BlockProcessor
from markdown.extensions import Extension


def null(*args, **kwargs):
    pass


debug_update_spaces_print = null  # python is cute like that.
debug_table = null


class ColumnsException(Exception):
    pass


def num_str(num):
    return f'{num:,}'


def tag(name):
    return f'COLUMNS_TAG:{name.lower()}'  # add stx?


class ListInfo:
    def __init__(self, indent, is_ordered):
        self.indent = indent
        self.is_ordered = is_ordered
        # usually set later as entire table is needed.
        self.order_sequence = 0
        self.depth = 0


class Cell:
    def __init__(self, text):
        m = re.match(r'(\s*)(?:([-*+])|(?:(\d+)\.))\s+(.*)', text)
        if m:
            self.list_ = ListInfo(indent=len(m.group(1)), is_ordered=bool(m.group(3)))
            self.text = m.group(4).strip()
        else:
            self.list_ = None
            self.text = text.strip()

    def is_numeric_column_like(self):
        """ true if string is a number, or something belonging in a numeric column """
        other = re.match(r'(?i)^\s*(?:n/?a|-+)?\s*$', self.text)
        return bool(self.is_number() or other)

    def _try_number(self):
        """ return float, correcting for percent signs and cruft, or None if not parsable """
        try:
            is_percent = '%' in self.text
            value = float(re.sub('[* ,$_%]', '', self.text))
            return value / 100.0 if is_percent else value
        except (ValueError, TypeError):
            return None

    def is_number(self):
        """ true is string is a number, including '$' """
        return self._try_number() is not None

    def as_number(self):
        """ return string as number (including '$'), or 0 if not parsable """
        value = self._try_number()
        return value if value is not None else 0

    def is_countable(self):
        """ true iff string is countable by <#>.
            That is, non-ignorable value, skipping blanks, dashes, and n/a values """
        return not re.match(r'(?i)^\s*(?:n/?a|-+)?\s*$', self.text)


class Kinds(IntEnum):
    tbd = 0
    header = 1
    data = 2
    blank_sep = 3
    footer = 4


class TableRow:
    def __init__(self, text, columns: List[Tuple[int, int]]):
        self.text = text.rstrip()
        self.kind = Kinds.tbd
        self.cells = [Cell(text[start:end].rstrip()) for (start, end) in columns]

    def __str__(self):
        return f"({str(self.kind)}, col_text={'|'.join((c.text for c in self.cells))}"

    def is_all_decorated(self):
        no_undecorated = all([re.match(r'^\s*(?:([*_]).*\1)?\s*$', c.text) for c in self.cells])
        return self.text.strip() and no_undecorated

    def is_all_separator(self):
        no_non_dash = all([re.match(r'^\s*([#=\-_+]*)\s*$', c.text) for c in self.cells])
        return self.text.strip() and no_non_dash

    def has_calculated(self):
        return bool(re.search(r'<(\+|-|%|#|avg)>', self.text))


class Align(IntEnum):
    left = 0
    right = 1


class Table:
    """ A table is a collection of TableLines.  Userlist requires __init__ signature. """

    # Userlist feels like too much 'behind the scenes stuff'.
    def __init__(self, lines, col_stops):
        self.rows = [TableRow(line, col_stops) for line in lines]
        self.set_row_kinds()
        self.col_alignment = self.find_column_alignments()
        self.organize_column_lists()
        self.replace_calc_fields()
        debug_table(f"cols: {col_stops}")
        debug_table("\n".join(str(l) for l in self.rows))

    def __str__(self):
        return f'(table:{len(self.rows)}) {[str(row) for row in self.rows]}'

    def organize_column_lists(self):
        """ set depth and sequence numbers for all list items """
        num_cells = len(self.rows[0].cells)
        for cell_num in range(num_cells):
            for row_num, row in enumerate(self.rows):
                cell = row.cells[cell_num]
                if cell.list_:
                    for above in range(row_num - 1, -1, -1):
                        above_cell = self.rows[above].cells[cell_num]
                        if not above_cell.list_:
                            # found a top level
                            cell.list_.depth = 1
                            cell.list_.order_sequence = 1
                            break
                        elif above_cell.list_.indent < cell.list_.indent:
                            # found a list item parent
                            cell.list_.depth = above_cell.list_.depth + 1
                            cell.list_.order_sequence = 1
                            break
                        elif above_cell.list_.indent == cell.list_.indent:
                            # found a peer item, at same depth
                            cell.list_.depth = above_cell.list_.depth
                            cell.list_.order_sequence = above_cell.list_.order_sequence + 1
                            cell.list_.is_ordered = above_cell.list_.is_ordered
                            break
                        else:
                            # found some child of a node further up the table, ignore
                            pass

        for row_num, row in enumerate(self.rows):
            pass

    def set_row_kinds(self):
        def check_rows():
            if len(self.rows) < 2:
                raise ColumnsException('Too few rows')

        if self.rows[1].is_all_separator():
            self.rows[0].kind = Kinds.header
            del self.rows[1]
            check_rows()

        while not self.rows[-1].text:
            del self.rows[-1]  # kill trailing blank lines
            check_rows()
        if self.rows[-2].is_all_separator():
            self.rows[-1].kind = Kinds.footer
            del self.rows[-2]
            check_rows()
        elif self.rows[-1].has_calculated():
            self.rows[-1].kind = Kinds.footer

        for row_num, row in enumerate(self.rows):
            if row.kind == Kinds.tbd:
                if row.has_calculated():
                    raise ColumnsException('Calculated field outside footer')
                elif row.text:
                    row.kind = Kinds.data
                else:
                    row.kind = Kinds.blank_sep  # might be bottom of table, but will delete it soon

    @staticmethod
    def calc_row(row: TableRow, computing_rows: List[TableRow]):
        """ Fills in calculated fields in a row given a list of rows to calculate from.
            For example, '<#>' in any field would be replaced with the number of countable items
        """
        for cell_num, cell in enumerate(row.cells):
            if '<#>' in cell.text:
                computing_cells = [r.cells[cell_num] for r in computing_rows]
                count = sum([1 for c in computing_cells if cell.is_countable()])
                cell.text = cell.text.replace('<#>', num_str(count))
            if '<+>' in cell.text:
                computing_cells = [r.cells[cell_num] for r in computing_rows]
                total = sum([t.as_number() for t in computing_cells])
                cell.text = cell.text.replace('<+>', num_str(total))
            if '<avg>' in cell.text:
                computing_cells = [r.cells[cell_num] for r in computing_rows]
                count_numbers = sum([1 for c in computing_cells if c.is_number()])
                total = sum([c.as_number() for c in computing_cells])
                if count_numbers:
                    cell.text = cell.text.replace('<avg>', num_str(total / count_numbers))
                else:
                    cell.text = cell.text.replace('<avg>', '--')
            if '<%>' in cell.text:
                Table.calc_percentage(cell, cell_num, computing_rows)

    @staticmethod
    def calc_percentage(cell, cell_num, computing_rows):
        # percentages should replace '<%>' with 100.0, and the blank column above with percentages
        # of the numbers in the next column to the left (the ref column)
        above_cells = [r.cells[cell_num] for r in computing_rows]
        if any((c.text for c in above_cells)):
            raise ColumnsException('<%> column is not empty')
        ref_col = cell_num - 1
        if ref_col < 0:
            raise ColumnsException('<%> column has no column to the left to reference')
        ref_cells = [r.cells[ref_col] for r in computing_rows]
        ref_total = sum([c.as_number() for c in ref_cells])
        if ref_total == 0:
            cell.text = cell.text.replace('<%>', '-- %')
        else:
            for index, ref in enumerate(ref_cells):
                if ref.is_number():
                    above_cells[index].text = f'{(ref.as_number() / ref_total):.1%}'
            cell.text = cell.text.replace('<%>', '100.0%')

    def replace_calc_fields(self):
        if self.rows[-1].kind == Kinds.footer and self.rows[-1].has_calculated():
            rows_in_compute = [row for row in self.rows if row.kind == Kinds.data]
            self.calc_row(self.rows[-1], rows_in_compute)

    def find_column_alignments(self):
        alignments = []
        num_columns = len(self.rows[0].cells)
        for c_i in range(num_columns):
            column_of_numeric_data = [row.cells[c_i].is_numeric_column_like()
                                      for row in self.rows
                                      if row.kind == Kinds.data]
            alignments.append(Align.right if all(column_of_numeric_data) else Align.left)
        return alignments


class ColumnsBlockProcessor(BlockProcessor):
    def __init__(self, parser, verbose, style, code_indent):
        self.is_verbose = verbose
        self.code_indent = code_indent
        self.style = style
        self.was_style_emitted = False
        super().__init__(parser)
        self.lines = []

    def verbose(self, reason):
        if self.is_verbose:
            msg = f'Columns: {reason}'
            print(msg, file=stderr)

    def test(self, parent, block):
        # API entry point, just preliminary test to skip some blocks
        return bool(re.search(r'\S {2,}\S', block))  # 2 or more spaces

    @staticmethod
    def get_columns(spaces):
        """ look at array of boolean spaces and return list a (start, end+1) of each
            actual column of False (non-blank), which has two or more spaces
            from next actual text column, excepting the ends.

            That is, a column of non-spaces is a span of False values with no more than
            one True value between them.

            a string s like 'A  AA A ', has spaces [f,t,t,f,f, t,f,t],
            so columns of (0,1), (3,7), with s[0:1] == 'A' and s[3:7] == 'AA A'
            returns list of tuples of text columns
        """
        deb_string = ''.join([('A' if not sp else '_') for sp in spaces])
        text_cols = []
        # states:  0 = not in word (in blank column), 1 = in word, last was character, 2 = in word, last was space
        state_in_blanks, state_in_word, state_saw_one_space = 0, 1, 2
        state = state_in_blanks
        begin_word, end_word = None, None
        for i, space in enumerate(spaces):
            if state == state_in_blanks and not space:
                begin_word = i
                state = state_in_word
            elif state == state_in_word and space:
                end_word = i  # but we won't know until next space
                state = state_saw_one_space
            elif state == state_saw_one_space and space:  # double spaced
                text_cols.append((begin_word, end_word))
                state = state_in_blanks
                begin_word, end_word = None, None
            elif state == state_saw_one_space and not space:
                state = state_in_word
        # end of string
        if state == state_saw_one_space:
            text_cols.append((begin_word, end_word))  # like, '  ff '
        elif state == state_in_word:
            text_cols.append((begin_word, len(spaces)))  # like, '  ff'
        return text_cols

    def find_table_extent(self, blocks):
        """ Find number of blocks used in table, else throw ColumnsException.

            A table extends through one or more blocks where it has columns of two or more
            spaces running vertically through the text.  We check each block
            until one fails, and then return the good matches.
            returns number of blocks used, lines in the table, and list of (start, end) column indices
        """
        spaces = []  # List[Bool], true if table has all spaces in this column
        good_lines = []  # lines known to be part of a table
        good_blocks = 0  # block used to make good_lines
        cols = []
        for current_block, block in enumerate(blocks):
            if current_block == 0:
                lines = []
            elif not block or block[0] == '\n':
                break  # double newline or empty block, end the table
            else:
                lines = ['']  # separator for blank table line
            lines += block.strip('\n').splitlines()
            spaces = self.update_spaces_in_lines(lines, spaces)
            new_cols = self.get_columns(spaces)
            if len(new_cols) < 2:
                break  # not a table, if this block is included.
            if new_cols[0][0] >= self.code_indent:
                self.verbose(f'block #{current_block}.  Table starts too far in and is a code block')
                break
            cols = new_cols
            good_lines.extend(lines)
            good_blocks += 1

        if len(cols) < 2:
            self.verbose(f'Need at least two columns')
            return 0, [], []
        elif len(good_lines) < 2:
            self.verbose(f'Table too short')
            return 0, [], []
        else:
            return good_blocks, good_lines, cols

    def emit_style(self, parent):
        if self.style == 'blue':
            e = etree.SubElement(parent, 'style')
            e.text = """
table.columns {
    font-family: "Times New Roman", Times, serif;
    border: 1px solid #fff;
    text-align: center;
    border-collapse: collapse;
}

table.columns td,
table.columns th {
    border: 1px solid #000;
    padding: 2px 1px;
}

table.columns tbody td {
    font-size: 13px;
}

table.columns span ul {
    margin: 0px;
}

table.columns tr:nth-child(even) {
    background: #d0e4f5;
}

table.columns thead {
    background: #0b6fa4;
    border: 5px solid #000;
}

table.columns thead th {
    font-size: 17px;
    font-weight: bold;
    color: #fff;
    text-align: center;
    border: 2px solid #000;
}


table.columns tfoot {
    font-size: 14px;
    font-weight: bold;
    color: #333333;
    background: #D0E4F5;
    border-top: 3px solid #444444;
}
r
table.columns tfoot td {
    font-size: 14px;
    border: 1px solid #000
}
"""
            print("style emitted")

    @staticmethod
    def update_spaces_in_lines(lines, spaces):
        """
        returns list booleans the max(len(lines), len(spaces)), with true
           meaning both lines and spaces (or just one if only one in length) has a space
        """
        for line in lines:
            line_spaces = [ch == ' ' for ch in line]
            new_spaces = []
            for i in range(max(len(spaces), len(line_spaces))):
                if i < len(spaces) and i < len(line_spaces):
                    new_spaces.append(line_spaces[i] and spaces[i])
                elif i < len(spaces):
                    new_spaces.append(spaces[i])
                else:
                    new_spaces.append(line_spaces[i])
            spaces = new_spaces
        debug_update_spaces_print('\n'.join(lines))
        debug_update_spaces_print(''.join(['-' if space else 'A' for space in spaces]))
        return spaces

    @staticmethod
    def check_list(text):
        #  return is_list, is_ordered, indent, item
        m = re.match(r'(\s*)(?:([*-+])|(?:(\d+)\.))\s+(.*)', text)
        if m:
            return True, bool(m.group(3)), len(m.group(1)), m.group(4).strip()
        else:
            return False, False, 0, ''

    def render_table_into_parent(self, parent, table):
        def style(row_kind, col_num):
            s = 'font-weight: bold;' if row_kind == Kinds.footer else ''
            s += ('text-align: right;' if table.col_aligment[col_num] else 'text-align: left;')
            return {'style': s} if s else {}

        if self.was_style_emitted == False:
            self.emit_style(parent)
            self.was_style_emitted = True

        t_table = etree.SubElement(parent, 'table', {'class': 'columns'})
        for row_num, row in enumerate(table.rows):
            if row.kind == Kinds.blank_sep:
                t_tr = etree.SubElement(t_table, 'tr', {'style': 'border-bottom:1px solid black'})  # And me
                etree.SubElement(t_tr, 'td', {'colspan': "100%"})
            else:
                if row.kind == Kinds.header:
                    t_row = etree.SubElement(etree.SubElement(t_table, 'thead'), 'tr')
                    tag_ = 'th'
                elif row.kind == Kinds.footer:
                    t_row = etree.SubElement(etree.SubElement(t_table, 'tfoot'), 'tr')
                    tag_ = 'td'
                elif row.kind == Kinds.data:
                    t_row = etree.SubElement(t_table, 'tr')
                    tag_ = 'td'
                else:
                    raise ColumnsException(f'Internal error, odd kind: {row.kind} in {row.text}')

                for c_i, c in enumerate(row.cells):
                    align = {'align': ('left' if table.col_alignment[c_i] == Align.left else 'right')}
                    if not c.list_:
                        # normal headers, footers, and non-list data
                        etree.SubElement(t_row, tag_, align).text = c.text if c.text else '&nbsp;'
                    else:
                        # <td><span class="depth2"><ul><ol><li>foo</li></ol></ul></span></td>
                        class_ = f'depth{c.list_.depth}'
                        el = etree.SubElement(t_row, tag_, align)
                        el = etree.SubElement(el, 'span', {'class': class_})
                        for _ in range(c.list_.depth - 1):
                            el = etree.SubElement(el, 'ul')
                        if c.list_.is_ordered:
                            el = etree.SubElement(el, 'ol', {'start': str(c.list_.order_sequence)})
                        else:
                            el = etree.SubElement(el, 'ul')
                        el = etree.SubElement(el, 'li')
                        el.text = c.text if c.text else '&nbsp;'

    def transform_table(self, parent, blocks):
        """
        Transform table from blocks, updating parent.  Returns
        number of blocks used, which may be 0 if not a table.
        """

        # transform table
        try:
            (num_blocks, lines, cols) = self.find_table_extent(blocks)
            if num_blocks > 0:
                table = Table(lines, cols)
                self.render_table_into_parent(parent, table)
            return num_blocks
        except ColumnsException as e:
            self.verbose(str(e))

            return 0  # bail on any problem

    def run(self, parent, blocks):
        """ markdown extension API entry.
            Blocks are each a multi-line, Unicode string; the whole shebang.split('\n\n')
        """
        blocks_used = self.transform_table(parent, blocks)
        if blocks_used == 0:
            return False  # not a table
        else:
            for i in range(blocks_used):
                blocks.pop(0)


class ColumnsExtension(Extension):
    def __init__(self, **kwargs):
        self.config = {
            'verbose': [False, 'print extra information to stdout'],
            'style': ['default', 'style type: default or "blue" table styling']}
        super().__init__(**kwargs)

    def extendMarkdown(self, md):
        md.parser.blockprocessors.register(
            ColumnsBlockProcessor(md.parser,
                                  verbose=self.getConfig('verbose'),
                                  style=self.getConfig('style'),
                                  code_indent=md.tab_length),
            'columns', 125)  # run before code block escapes


# noinspection PyPep8Naming
def makeExtension(**kwargs):
    return ColumnsExtension(**kwargs)


# noinspection PyProtectedMember
def test_utils():
    g1 = ['-$23,123.45', '-23_123.45', '-2312345%']
    g2 = [' .302  ', '   $ 0,000,000,000.302000  ', '  30.2%   ', '30.2 %', ' *23*']
    g3 = ['  n/a  ', 'NA', '--', '', '   ']
    g4 = ['  text ', '234 USD', 'about 23.4', '(23.4)', '23.4-']

    assert all([Cell(s).is_numeric_column_like() for s in [*g1, *g2, *g3]])
    assert not any([Cell(s).is_numeric_column_like() for s in [*g4]])
    assert all([Cell(s).is_number() for s in [*g1, *g2]])
    assert not any([Cell(s).is_number() for s in [*g3, *g4]])
    assert all([Cell(s).as_number() == -23123.45 for s in g1])
    assert all([Cell(s).as_number() == 0 for s in [*g3, *g4]])
    assert all([Cell(s)._try_number() is None for s in [*g3, *g4]])
    assert all([Cell(s)._try_number() is not None for s in [*g1, *g2]])
    assert all([Cell(s).is_countable() for s in [*g1, *g2, *g4]])
    assert not any([Cell(s).is_countable() for s in g3])


# noinspection SpellCheckingInspection
def test_column_block_processor():
    class MockParser:
        class mock1:
            tab_length = 4

        md = mock1()

    def bools(st):
        return [(True if ch in 'tTx' else False) for ch in st]

    c = ColumnsBlockProcessor(MockParser, verbose=True, code_indent=12)
    cq = ColumnsBlockProcessor(MockParser, verbose=False, code_indent=12)
    print("Should print 'is_verbose' once")
    c.verbose("is_verbose")
    cq.verbose("is not verbose")
    with pytest.raises(ColumnsException):
        raise ColumnsException("Failed")
    assert c.test(None, "Column with two spaces   Between them")
    assert not c.test(None, "a b c d")

    assert bools('tft') == [True, False, True]
    assert c.get_columns(bools('ttttttt')) == []
    assert c.get_columns(bools('ttttfttt')) == [(4, 5)]
    assert c.get_columns(bools('t..')) == [(1, 3)]
    assert c.get_columns(bools('t..t')) == [(1, 3)]
    assert c.get_columns(bools('.tt..t.t')) == [(0, 1), (3, 7)]
    assert c.get_columns(bools('t..tt.t.')) == [(1, 3), (5, 8)]

    assert c.update_spaces_in_lines([], []) == []
    assert c.update_spaces_in_lines(['A   C D', 'A B   D'], []) == bools(' x x x ')
    assert c.update_spaces_in_lines(['  '], [False]) == [False, True]

    assert c.find_table_extent([]) == (0, [], [])
    assert c.find_table_extent(['     ']) == (0, [], [])
    assert c.find_table_extent(['a  b']) == (0, [], [])
    assert c.find_table_extent(['             a  b\n             a  b']) == (0, [], [])
    b1 = ['a  b\n1  2', '3  4\n5  6', '\nNot in Table']  # double space
    blocks_used, lines_in_table, cols = cq.find_table_extent(b1)
    assert blocks_used == 2 and lines_in_table == ['a  b', '1  2', '', '3  4', '5  6'] and cols == [(0, 1), (3, 4)]
    b1 = ['a  b\n1  2', '3  4\n5  6', '', 'Not in Table']  # triple space
    blocks_used, lines_in_table, cols = cq.find_table_extent(b1)
    assert blocks_used == 2 and lines_in_table == ['a  b', '1  2', '', '3  4', '5  6'] and cols == [(0, 1), (3, 4)]


def test_table_line():
    t = TableRow('', [])
    assert not t.is_all_decorated() and not t.is_all_separator() and not t.has_calculated()
    t = TableRow('    ', [(0, 1), (3, 4)])
    assert not t.is_all_decorated() and not t.is_all_separator() and not t.has_calculated()
    t = TableRow('a  b', [(0, 1), (3, 4)])
    assert t.text == 'a  b' and t.cells[0].text == 'a' and t.cells[1].text == 'b'
    assert not t.is_all_decorated() and not t.is_all_separator() and not t.has_calculated()
    t = TableRow('One   Space <#> Two', [(0, 3), (5, 21), (30, 35)])
    assert t.cells[0].text == 'One' and t.cells[1].text == 'Space <#> Two' and t.cells[2].text == ''
    assert not t.is_all_decorated() and not t.is_all_separator() and t.has_calculated()
    t = TableRow('_One_    *Space Two*', [(0, 7), (9, 20), (30, 35)])
    assert t.is_all_decorated() and not t.is_all_separator() and not t.has_calculated()
    t = TableRow('-  -', [(0, 1), (3, 4), (15, 16)])
    assert not t.is_all_decorated() and t.is_all_separator() and not t.has_calculated()
    t = TableRow('=   ==', [(0, 1), (3, 5), (15, 16)])
    assert t.is_all_separator()


def test_cell():
    c = Cell('   foo ')
    assert c.text == 'foo' and not c.list_
    c = Cell('  +    bar  ')
    assert c.text == 'bar' and c.list_ and not c.list_.is_ordered and c.list_.indent == 2
    c = Cell('12.  baz')
    assert c.text == 'baz' and c.list_ and c.list_.is_ordered and c.list_.indent == 0


def test_table():
    # test creation and parse
    t1 = Table(['a  b', 'c  d'], [(0, 1), (3, 4)])
    assert t1.rows[0].kind == Kinds.data

    lines1 = ['_Name_     _Amt_',
              '-----',
              'Alice       30',
              'Bob         40',
              '              ',
              'Charlie    -10',
              '--------   ---',
              '<#>;<avg>   <+>    <%>']
    #          01234567890123456789
    cols1 = [(0, 9), (11, 16), (18, 22)]
    t = Table(lines1, cols1)
    assert ''.join((c.text for c in t.rows[0].cells)) == '_Name__Amt_'
    assert len(t.rows[0].cells) == 3

    assert t.rows[0].kind == Kinds.header and t.rows[-1].kind == Kinds.footer
    assert t.rows[1].kind == Kinds.data
    assert t.rows[3].kind == Kinds.blank_sep

    assert t.rows[-1].cells[0].text == '3;--'
    assert t.rows[1].cells[2].text == '50.0%'

    assert t.col_alignment[0] == Align.left and t.col_alignment[1] == Align.right


def test_list_table():
    lines1 = ['_Name_     _Amt_',
              '-----',
              'Alice       30',
              '* Bob       40',
              '  * C2       4  ',
              'Charlie    -10',
              '  1. D2      3 ',
              '--------   ---',
              '<#>;<avg>   <+>    <%>']
    #          01234567890123456789
    cols1 = [(0, 9), (11, 16), (18, 22)]
    t = Table(lines1, cols1)
    assert not t.rows[2].cells[0].list_.is_ordered
    assert t.rows[3].cells[0].list_.depth == 2
    l = t.rows[5].cells[0].list_
    assert l.is_ordered and l.order_sequence == 1


def test_check_list():
    assert ColumnsBlockProcessor.check_list('  * Foobar') == (True, False, 2, 'Foobar')
    assert ColumnsBlockProcessor.check_list('  9.    Foobar') == (True, True, 2, 'Foobar')
    assert ColumnsBlockProcessor.check_list('  Foobar') == (False, False, 0, '')
    assert ColumnsBlockProcessor.check_list('*Foobar') == (False, False, 0, '')


if __name__ == "__main__":
    test_cell()
    test_utils()
    test_table()
    test_list_table()
    test_column_block_processor()
    test_table_line()
    test_check_list()
