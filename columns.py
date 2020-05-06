import re
import xml.etree.ElementTree as etree
from sys import stderr
import pytest
from enum import IntEnum

from markdown.blockprocessors import BlockProcessor
from markdown.extensions import Extension


def number_like(string):
    """ true if string is a number, or something belonging in a numeric column """
    number_like_re = r'^[-+$,.0-9 ]*$'  # "$ -23.43" or "--", but also "$$$----", meh.
    m = re.match(rf'{number_like_re}|n/a|N/A', string)
    return bool(m)


def is_number(string):
    """ true is string is a number, including '$' """
    s = re.sub('[ ,$]', '', string)
    m = re.match(r'[-+]?(?:\d+\.?|\d*\.\d+)$', s)  # like -32, +32., 32.1, or .1
    return bool(m)


def number_like_value(string):
    """ float of string, or 0 """
    try:
        return float(re.sub('[ ,$_]', '', string))
    except (ValueError, TypeError):
        return 0


def is_blank_like(string):
    """ true iff string is an ignored value (blank, '--', 'n/a') """
    blank_like_re = r'(?i)^(?:[ -]*|n/?a)$'
    return re.match(blank_like_re, string)


def tag(name):
    return f'COLTAG:{name.lower()}'  # add stx?


class TableLine:
    def __init__(self, text, cols_):
        self.text = text
        self.kind = 'tbd'
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
        state = 0
        begin_word, end_word = None, None
        for i, space in enumerate(spaces):
            if state == 0 and not space:
                begin_word = i
                state = 1
            elif state == 1 and space:
                end_word = i  # but we won't know until next space
                state = 2
            elif state == 2 and space:  # doublespace
                text_cols.append((begin_word, end_word))
                state = 0
                begin_word, end_word = None, None
            elif state == 2 and not space:
                state = 1
        # end of string
        if state == 2:
            text_cols.append((begin_word, end_word))  # like, '  ff '
        elif state == 1:
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

    def update_spaces_in_lines(self, lines, spaces):
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

    def set_table_kinds(self, table):
        if table[0].is_all_decorated():
            table[0].kind = 'header'
        elif table[1].is_all_separator():
            table[0].kind = 'header'
            del table[1]

        while not table[-1].text:
            del table[-1]  # kill trailing blank lines
        if table[-1].is_all_decorated():
            table[-1].kind = 'footer'
        elif table[-2].is_all_separator():
            table[-1].kind = 'footer'
            del table[-2]

        for row_num, row in enumerate(table):
            if row.kind == 'tbd':
                if row.has_calculated():
                    row.kind = 'subtotal'
                elif row.text:
                    row.kind = 'data'
                else:
                    row.kind = 'sep'  # might be bottom of table, but will delete it soon

    def transform_table(self, parent, blocks):
        """
        Transform table from blocks, updating parent.  Returns
        number of blocks used, which may be 0 if not a table.
        """

        def mark_body():
            for row_num, row in enumerate(table):
                for col_num, text in enumerate(row.col_text):
                    if m := re.match(r'^( )*([*+-]|\d\.)', text):
                        # OK, figure out depth of this row, and fix up text to display.
                        if row.depth != 0:
                            self.fail('Another column already set the depth')
                        spaces = len(m.group(1))
                        mark = m.group(2) if not m.group(2)[0].isdigit() else '1.'

                        # Walk up table trying to find a sibling.
                        for walk_row_num in range(row_num - 1, -1, -1):
                            walk_row = table[walk_row_num]
                            walk_text = walk_row.col_text[col_num]
                            if not walk_text:
                                continue  # skip blank line in table without breaking count
                            new_m = re.match(r'^( )*((?:[*+-]|\d\.)?)', walk_text)  # always match, but may be empty
                            if new_m:
                                new_spaces = len(new_m.group(1))
                                new_mark = new_m.group(2)
                                if spaces > new_spaces:
                                    continue  # skip some deeper child
                                elif spaces == new_spaces:
                                    # sibling level; possibly continuing ordered list
                                    row.depth = walk_row.depth
                                    if mark[0].isdigit() and new_mark[0].isdigit():
                                        # continuing ordered list, fix the number
                                        next_num = int(float(new_mark)) + 1
                                        text = text.replace(mark, f'{next_num}.')
                                    elif mark[0].isdigit():
                                        # switching to ordered list, fix the number
                                        text = text.replace(mark, '1.')
                        else:
                            # No appropriate parent, make depth = 1, first of its line
                            row.depth = 1
                        # walk up, finding a sibling or parent
                        # walk up, until same or lower depth

        def fix_calculated():
            def get_cumputing_row_indices(r_num, c_num):
                """ gets indices of rows that should be used to compute row r_num, column c_num """
                if table[r_num].kind == 'footer':
                    indices = [row_num
                               for (row_num, row_) in enumerate(table[:r_num])
                               if row_.kind == "data"]  # items above
                    return indices
                # raise ValueError('Only works with footers')
                return []

            def get_column(r_num, c_num):
                """ gets column text for summary at row r_num, column c_num """
                return [table[r].col_text[c_num] for r in get_cumputing_row_indices(r_num, c_num)]

            def fmt_percent(n):
                return f"{n:.1%}"

            # fix calculated <#> <+>, <%>, <avg>.
            for row_num, row in enumerate(table):
                if row.has_calculated() and row.kind == 'footer':
                    for col_num in range(len(row.col_text)):
                        column = get_column(row_num, col_num)
                        count = sum([1 for t in column if not is_blank_like(t)])
                        total = sum([number_like_value(t) for t in column])

                        text = row.col_text[col_num]
                        if '<#>' in text:
                            text = text.replace('<#>', str(count))
                        if '<+>' in text:
                            text = text.replace('<+>', str(total))
                        if '<avg>' in text:
                            s = str(total / count) if count else '-'
                            text = text.replace('<avg>', s)
                        if '<%>' in text:
                            if not all([is_blank_like(c) for c in column]):
                                self.fail('% column not empty')
                            if col_num == 0:
                                self.fail('% column has no left members')
                            left_indices = get_cumputing_row_indices(row_num, col_num - 1)
                            left_column = get_column(row_num, col_num - 1)
                            left_count = sum([1 for t in left_column if is_number(t)])
                            left_total = sum([number_like_value(t) for t in left_column])
                            percentages = [
                                (fmt_percent(number_like_value(left_column[ti]) / left_total) if left_total else '')
                                for ti in left_indices]
                            text = '100.0 %'
                            for ci in left_indices:
                                if is_number(left_column[ci]):
                                    x = (fmt_percent(
                                        number_like_value(left_column[ci]) / left_total) if left_total else '')
                                    table[ci].col_text[col_num] = (fmt_percent(
                                        number_like_value(left_column[ci]) / left_total) if left_total else '')

                            # walk back to actual numbers
                            # copy number strings into each spot
                            text = text.replace('<%>', '100.0 %')
                            pass
                        row.col_text[col_num] = text

        def style(row_kind, col_num):
            # row emphasis
            if row_kind == 'subt':
                s = 'font-style: italic;'
            elif row_kind == 'footer':
                s = 'font-weight: bold;'
            else:
                s = ''
            # col formatting
            column = [(row.col_text[col_num] if col_num < len(row.col_text) else '')
                      for row in table]
            if all([number_like(col) for col in column]):  # numberish
                s += 'text-align: right;'
                # line up decimal points?  It's a pain.
            return {'style': s} if s else {}

        def update_parent_with_table():
            t_table = etree.SubElement(parent, 'table', {'class': 'paleBlueRows'})
            for row in table:
                if row.kind == 'sep':
                    t_tr = etree.SubElement(t_table, 'tr', {'style': 'border-bottom:1px solid black'})
                    etree.SubElement(t_tr, 'td', {'colspan': "100%"})
                else:
                    if row.kind == 'header':
                        t_row = etree.SubElement(etree.SubElement(t_table, 'thead'), 'tr')
                        tag_ = 'th'
                    elif row.kind == 'footer':
                        t_row = etree.SubElement(etree.SubElement(t_table, 'tfoot'), 'tr')
                        tag_ = 'td'
                    elif row.kind == 'data':
                        t_row = etree.SubElement(t_table, 'tr')
                        tag_ = 'td'
                    elif row.kind == 'subt':
                        t_row = etree.SubElement(t_table, 'tr', {'style': 'font-style: italic;'})
                        tag_ = 'td'
                    else:
                        self.fail(f'Internal error, odd kind: {row.kind} in {row.text}')

                    for col, text in enumerate(row.col_text):
                        etree.SubElement(t_row, tag_, style(row.kind, col)).text = text

        # transform table
        table = []  # make pycharm happier
        try:
            (num_blocks, lines, cols) = self.find_table_extent(blocks)
            if num_blocks > 0:
                table = [TableLine(line, cols) for line in lines]
                self.set_table_kinds(table)
                fix_calculated()
                update_parent_with_table()
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
    assert all([is_number(s) for s in ['$23.23', '   -$23.23', '   $  -2,124.23', '23', '0.']])
    assert not any([is_number(s) for s in ['', '-', 'String', '   String', ' ____', '(23.0)', '23.4-', '*23*']])
    assert all([is_blank_like(s) for s in ['', '   ', '-', '--', '---', 'n/a', 'NA', 'N/A']])
    assert not any([is_blank_like(s) for s in ['.', '==', '***', '     ---  foo --- ']])


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
    b1 = ['a  b\n1  2', '3  4\n5  6', 'Not in Table']
    blocks_used, lines_in_table, cols = cq.find_table_extent(b1)
    assert blocks_used == 2 and lines_in_table == ['a b', '1 2', '3 4', '5 6'] and cols == [(0, 1), (3, 4)]


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


if __name__ == "__main__":
    test_utils()
    test_column_block_processor()
    test_table_line()
