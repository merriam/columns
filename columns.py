import re
import xml.etree.ElementTree as etree
from sys import stderr
import pytest
from enum import IntEnum
from collections import UserList
from markdown.blockprocessors import BlockProcessor
from markdown.extensions import Extension


def is_numeric_column_like(string):
    """ true if string is a number, or something belonging in a numeric column """
    other = re.match(r'(?i)^\s*(?:n/?a|-+)?\s*$', string)
    return bool(is_number(string) or other)


def try_number(string):
    """ return float, correcting for percent signs and cruft, or None if not parsable """
    try:
        is_percent = '%' in string
        value = float(re.sub('[ ,$_%]', '', string))
        return value / 100.0 if is_percent else value
    except (ValueError, TypeError):
        return None


def is_number(string):
    """ true is string is a number, including '$' """
    return try_number(string) is not None


def as_number(string):
    """ return string as number (including '$'), or 0 if not parsable """
    value = try_number(string)
    return value if value is not None else 0


def is_countable(string):
    """ true iff string is countable by <#>.
        That is, non-ignorable value, skipping blanks, dashes, and n/a values """
    return not re.match(r'(?i)^\s*(?:n/?a|-+)?\s*$', string)


def tag(name):
    return f'COLTAG:{name.lower()}'  # add stx?


class Kinds(IntEnum):
    tbd = 0
    header = 1
    data = 2
    sep = 3
    subtotal = 4
    footer = 5


class TableLine:
    def __init__(self, text, cols_):
        self.text = text
        self.kind = Kinds.tbd
        self.col_text = [text[start:end] for (start, end) in cols_]
        self.col_used_in_total = [False for _ in cols_]
        self.depth = 0  # how deep in a table is this row.

    def __str__(self):
        return f"TableLine, kind={self.kind}, col_text={'|'.join(self.col_text)}"

    def is_all_decorated(self):
        no_undecorated = all([re.match(r'^\s*(?:([*_]).*\1)?\s*$', col_text) for col_text in self.col_text])
        return self.text.strip() and no_undecorated

    def is_all_separator(self):
        no_non_dash = all([re.match(r'^\s*([#=\-_+]*)\s*$', col_text) for col_text in self.col_text])
        return self.text.strip() and no_non_dash

    def has_calculated(self):
        return bool(re.search(r'<(\+|-|%|#|avg)>', self.text))


class Table(UserList):
    """ A table is a collection of TableLines. """

    def __init__(self, copy_from=None):
        if copy_from is None:
            self.data = []
        else:
            self.data = copy_from.data[:]
        super().__init__()

    @classmethod
    def create(cls, lines, cols):
        t = cls()
        t.data = [TableLine(line, cols) for line in lines]
        return t

    def set_kinds(self):
        if self.data[0].is_all_decorated():
            self.data[0].kind = Kinds.header
        elif self.data[1].is_all_separator():
            self.data[0].kind = Kinds.header
            del self.data[1]

        while not self.data[-1].text:
            del self.data[-1]  # kill trailing blank lines
        if self.data[-1].is_all_decorated() or self.data[-1].has_calculated():
            self.data[-1].kind = Kinds.footer
        elif self.data[-2].is_all_separator():
            self.data[-1].kind = Kinds.footer
            del self.data[-2]

        for row_num, row in enumerate(self.data):
            if row.kind == Kinds.tbd:
                if row.has_calculated():
                    row.kind = Kinds.subtotal
                elif row.text:
                    row.kind = Kinds.data
                else:
                    row.kind = Kinds.sep  # might be bottom of table, but will delete it soon

    @staticmethod
    def calc_row(row, computing_rows):
        """ Fills in calculated fields in a row given a list of rows to calculate from.
            For example, '<#>' in any field would be replaced with the number of countable items
        """
        for col_num, text in enumerate(row.col_text):
            computing_text = [r.col_text[col_num] for r in computing_rows]
            count = sum([1 for t in computing_text if is_countable(t)])
            total = sum([as_number(t) for t in computing_text])
            count_numbers = sum([1 for t in computing_text if is_number(t)])
            if '<#>' in text:
                text = text.replace('<#>', str(count))
            if '<+>' in text:
                text = text.replace('<+>', str(total))
            if '<avg>' in text:
                if count_numbers:
                    text = text.replace('<avg>', str(total / count_numbers))
                else:
                    text = text.replace('<avg>', '--')
            if '<%>' in text:
                # percentages are complicated.
                # rule is replace the '<%>' with 100.0 and then set each computed column
                # to the percentage of the next leftmost column
                if any(computing_text):
                    raise ColumnsException('<%> column is not empty')
                ref_col = col_num - 1
                while ref_col >= 0 and ('%' in row.col_text or not is_number(row.col_text[ref_col])):
                    ref_col -= 1
                if ref_col < 0:
                    raise ColumnsException('<%> column has no column to reference')
                for compute_row in computing_rows:
                    if is_number(compute_row.col_text[ref_col]):
                        compute_row.col_text[col_num] = f'{(compute_row.col_text[ref_col] / total):.1%}'
                text = '100.0%'
            row.col_text[col_num] = text

    def replace_calc_fields(self):
        for row_number, row in enumerate(self.data):
            if row.kind == Kinds.subtotal:
                self.replace_subtotal_calc_fields(row_number)

        if self.data[-1].kind == Kinds.footer:
            rows_in_compute = [row for row in self.data
                               if not row.has_calculated and row.kind in (Kinds.subtotal, Kinds.header)]
            self.calc_row(self.data[-1], rows_in_compute)

    def replace_subtotal_calc_fields(self, row_number):
        # One and only one row below it should have a list.
        if row_number >= len(self.data):
            raise ColumnsException('Subtotal on last line.  Remember to emphasize or separate your footer.')
        pass


class ColumnsException(Exception):
    pass


class ColumnsBlockProcessor(BlockProcessor):
    def __init__(self, parser, verbose, code_indent):
        self.is_verbose = verbose
        self.code_indent = code_indent
        super().__init__(parser)
        self.lines = []

    def verbose(self, reason):
        if self.is_verbose:
            msg = f'Columns: {reason}'
            print(msg, file=stderr)

    def fail(self, reason):
        self.verbose(reason)
        raise ColumnsException(reason)

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
            # print(f"blocks processed: {good_blocks}; new data fields:")
            # for l in lines:
            #     print('|' + '|'.join([l[slice(*c)] for c in new_cols]) + "|")

        if len(cols) < 2:
            self.verbose(f'Need at least two columns')
            return 0, [], []
        elif len(good_lines) < 2:
            self.verbose(f'Table too short')
            return 0, [], []
        else:
            return good_blocks, good_lines, cols

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
        print('\n'.join(lines))
        print(''.join(['-' if space else 'A' for space in spaces]))
        return spaces

    def transform_table(self, parent, blocks):
        """
        Transform table from blocks, updating parent.  Returns
        number of blocks used, which may be 0 if not a table.
        """

        def style(row_kind, col_num):
            # row emphasis
            if row_kind == Kinds.subtotal:
                s = 'font-style: italic;'
            elif row_kind == Kinds.footer:
                s = 'font-weight: bold;'
            else:
                s = ''
            # col formatting
            column = [(row.col_text[col_num] if col_num < len(row.col_text) else '')
                      for row in table]
            if all([is_numeric_column_like(col) for col in column]):  # numberish
                s += 'text-align: right;'
                # line up decimal points?  It's a pain.
            return {'style': s} if s else {}

        def update_parent_with_table(table):
            t_table = etree.SubElement(parent, 'table', {'class': 'paleBlueRows'})
            for row in table:
                if row.kind == Kinds.sep:
                    t_tr = etree.SubElement(t_table, 'tr', {'style': 'border-bottom:1px solid black'})
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
                    elif row.kind == Kinds.subtotal:
                        t_row = etree.SubElement(t_table, 'tr', {'style': 'font-style: italic;'})
                        tag_ = 'td'
                    else:
                        self.fail(f'Internal error, odd kind: {row.kind} in {row.text}')

                    for col, text in enumerate(row.col_text):
                        etree.SubElement(t_row, tag_, style(row.kind, col)).text = text

        # transform table
        try:
            (num_blocks, lines, cols) = self.find_table_extent(blocks)
            if num_blocks > 0:
                table = Table.create(lines, cols)
                table.set_kinds()
                table.replace_calc_fields()
                update_parent_with_table(table)
            return num_blocks
        except ColumnsException:
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
            'style': ['default', 'style type: default, bare, or stylesheet filename']}
        super().__init__(**kwargs)

    def extendMarkdown(self, md):
        md.parser.blockprocessors.register(
            ColumnsBlockProcessor(md.parser, self.getConfig('verbose'), code_indent=md.tab_length),
            'columns', 125)  # run before code block escapes


def makeExtension(**kwargs):
    return ColumnsExtension(**kwargs)


def test_utils():
    g1 = ['-$23,123.45', '-23_123.45', '-2312345%']
    g2 = [' .302  ', '   $ 0,000,000,000.302000  ', '  30.2%   ', '30.2 %']
    g3 = ['  n/a  ', 'NA', '--', '', '   ']
    g4 = ['  text ', '234 USD', 'about 23.4', '*23*', '(23.4)', '23.4-']

    assert all([is_numeric_column_like(s) for s in [*g1, *g2, *g3]])
    assert not any([is_numeric_column_like(s) for s in [*g4]])
    assert all([is_number(s) for s in [*g1, *g2]])
    assert not any([is_number(s) for s in [*g3, *g4]])
    assert all([as_number(s) == -23123.45 for s in g1])
    assert all([as_number(s) == 0 for s in [*g3, *g4]])
    assert all([try_number(s) is None for s in [*g3, *g4]])
    assert all([try_number(s) is not None for s in [*g1, *g2]])
    assert all([is_countable(s) for s in [*g1, *g2, *g4]])
    assert not any([is_countable(s) for s in g3])


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
        c.fail("Failed")
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
    b1 = ['a  b\n1  2', '3  4\n5  6', '\nNot in Table'] # double space
    blocks_used, lines_in_table, cols = cq.find_table_extent(b1)
    assert blocks_used == 2 and lines_in_table == ['a  b', '1  2', '', '3  4', '5  6'] and cols == [(0, 1), (3, 4)]
    b1 = ['a  b\n1  2', '3  4\n5  6', '', 'Not in Table']  # triple space
    blocks_used, lines_in_table, cols = cq.find_table_extent(b1)
    assert blocks_used == 2 and lines_in_table == ['a  b', '1  2', '', '3  4', '5  6'] and cols == [(0, 1), (3, 4)]


def test_table_line():
    t = TableLine('', [])
    assert not t.is_all_decorated() and not t.is_all_separator() and not t.has_calculated()
    t = TableLine('    ', [(0, 1), (3, 4)])
    assert not t.is_all_decorated() and not t.is_all_separator() and not t.has_calculated()
    t = TableLine('a  b', [(0, 1), (3, 4)])
    assert t.text == 'a  b' and t.col_text[0] == 'a' and t.col_text[1] == 'b'
    assert not t.is_all_decorated() and not t.is_all_separator() and not t.has_calculated()
    t = TableLine('One   Space <#> Two', [(0, 3), (5, 21), (30, 35)])
    assert t.col_text[0] == 'One' and t.col_text[1] == ' Space <#> Two' and t.col_text[2] == ''
    assert not t.is_all_decorated() and not t.is_all_separator() and t.has_calculated()
    t = TableLine('_One_    *Space Two*', [(0, 7), (9, 20), (30, 35)])
    assert t.is_all_decorated() and not t.is_all_separator() and not t.has_calculated()
    t = TableLine('-  -', [(0, 1), (3, 4), (15, 16)])
    assert not t.is_all_decorated() and t.is_all_separator() and not t.has_calculated()
    t = TableLine('=   ==', [(0, 1), (3, 5), (15, 16)])
    assert t.is_all_separator()


if __name__ == "__main__":
    test_utils()
    test_column_block_processor()
    test_table_line()
