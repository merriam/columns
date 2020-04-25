import re
import xml.etree.ElementTree as etree
from sys import stderr

from markdown.blockprocessors import BlockProcessor
from markdown.extensions import Extension


def tag(name):
    return f'COLTAG:{name.lower()}'  # add stx?


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
        # API entry point, just preliminary test
        return bool(re.search(r'\S {2,}\S', block))

    @staticmethod
    def get_columns(spaces):
        """ look at array of boolean spaces and return list a (start, end+1) of each
            actual column of False (non-blank), which has two or more spaces
            from next actual text column.

            for .=True, x=False, "x..xx.x." gives (0,1), (3,7)
            returns list of tuples of text columns
        """
        starts = [i for (i, sp) in enumerate(spaces)
                  if sp and (i == 0 or not spaces[i - 1])]
        ends = [i for (i, sp) in enumerate(spaces)
                if sp and (i == len(spaces) - 1 or not spaces[i + 1])]
        space_cols = [(start, end) for (start, end) in zip(starts, ends)
                      if end - start > 0]
        text_cols = []
        if space_cols and space_cols[0][0] > 0:
            text_cols.append((0, space_cols[0][0]))  # text starting at zero
        for i in range(1, len(space_cols)):
            text_cols.append((space_cols[i - 1][1] + 1, space_cols[i][0]))
            # (one after last column, to one before next column), 0 width OK
        if space_cols and space_cols[-1][1] < len(spaces):
            text_cols.append((space_cols[-1][1] + 1, len(spaces)))
            # (one after final column, to end of line)
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
            elif block[0] == '\n':
                break  # double newline, end the table
            else:
                lines = ['']  # separator for blank table line
            lines += block.strip('\n').splitlines()
            spaces = self.update_spaces_in_lines(lines, spaces)
            cols = self.get_columns(spaces)
            for l in lines:
                print('|' + '|'.join([l[slice(*c)] for c in cols]) + "|")

            if cols[0][0] >= self.code_indent:
                self.verbose(f'block #{current_block}.  Table starts too far in and is a code block')
                break
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

    def update_spaces_in_lines(self, lines, spaces):
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
        print(''.join([' ' if space else 'x' for space in spaces]))
        return spaces

    def transform_table(self, parent, blocks):
        """
        Transform table from blocks, updating parent.  Returns
        number of blocks used, which may be 0 if not a table.
        """

        class TableLine:
            def __init__(self, text, cols_):
                self.text = text
                self.kind = 'tbd'
                self.col_text = [text[start:end + 1] for (start, end) in cols_]

            def __str__(self):
                return f"TableLine, kind={self.kind}, col_text={'|'.join(self.col_text)}"

            def is_all_decorated(self):
                return all([re.match(r'^\s*([*_]).*\1\s*$', col_text) for col_text in self.col_text])

            def is_all_punctuation(self):
                # all columns are a line of punctuation or blank, with at least one non-blank
                return (any([col_text for col_text in self.col_text]) and
                        all([re.match(r'^\s*([#=\-_+]*)\s*$', col_text) for col_text in self.col_text]))

            def has_calculated(self):
                return bool(re.search(r'<(\+|-|%|#|avg)>', self.text))

        def mark_headers():
            if table[0].is_all_decorated():
                table[0].kind = 'header'
            elif table[1].is_all_punctuation():
                table[0].kind = 'header'
                del table[1]

        def mark_footers():
            while not table[-1].text:
                del table[-1]  # kill trailing blank lines
            if table[-1].is_all_decorated():
                table[-1].kind = 'footer'
            elif table[-2].is_all_punctuation():
                table[-1].kind = 'footer'
                del table[-2]

        def mark_body():
            for row in table:
                if row.kind == 'tbd':
                    if row.has_calculated():
                        row.kind = 'subt'
                    if row.text:
                        row.kind = 'data'
                    else:
                        row.kind = 'sep'  # might be bottom of table, but will delete it soon

        def fix_calculated():
            # fix calculated <+>, <%>, <avg>.
            pass

        def style(row_kind, col_num):
            # row emphasis
            if row_kind == 'subt':
                s = 'font-style: italic;'
            elif row_kind == 'footer':
                s = 'font-weight: bold;'
            else:
                s = ''
            # col formatting
            numberish = r'^\s*(?:([+-]?\s*\d+\.?\d*)|n\/a|N\/A|-+)?\s*$'  # like, '5', '- 23.2', ' ', '-', 'n/a'
            column = [(row.col_text[col_num] if col_num < len(row.col_text) else '')
                      for row in table]
            if all([re.match(numberish, col) for col in column]):  # numberish
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
                        t_row = t_row = etree.SubElement(t_table, 'tr')
                        tag_ = 'td'
                    else:
                        self.fail(f'Internal error, odd kind: {row.kind} in {row.text}')

                    for col, text in enumerate(row.col_text):
                        etree.SubElement(t_row, tag_, style(row.kind, col)).text = text

        # transform table
        try:
            (num_blocks, lines, cols) = self.find_table_extent(blocks)
            if num_blocks > 0:
                table = [TableLine(line, cols) for line in lines]
                mark_headers()
                mark_footers()
                mark_body()
                fix_calculated()
                update_parent_with_table()
            return num_blocks
        except ColumnsException:
            return 0  # bail on any problem

    def run(self, parent, blocks):
        """ markdown extension API entry.
            Blocks are each a multi-line, Unicode string where
            all blank lines have been stripped (no '\n  \n'),
            and there are no double blank lines (no '\n\n').  """
        blocks_used = self.transform_table(parent, blocks)
        if blocks_used == 0:
            return False  # not a table
        else:
            for i in range(blocks_used):
                blocks.pop(0)


# class ColumnsPostprocessor(Postprocessor):
#     def __init__(self, verbose, style):
#         self.verbose = verbose
#         self.style = style
#         super().__init__()
#
#     def run(self, text):
#         replacements = {
#             'start_table': '<table>',
#             'end_table': '</table>',
#             'start_data': '<tr>',
#             'end_data': '</tr>',
#             r'col_data ([^\n]*)': r'<td>\1</td>'
#         }
#         for pattern, rep in replacements.items():
#             text = re.sub(tag(pattern), rep, text)
#         return text


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
