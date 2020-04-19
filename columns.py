from sys import stderr

from markdown.extensions import Extension
from markdown.postprocessors import Postprocessor
from markdown.preprocessors import Preprocessor
import re


def tag(name):
    return f'COLTAG:{name.lower()}'  # add stx?


class ColumnsException(Exception):
    pass


class ColumnsPreprocessor(Preprocessor):
    def __init__(self, verbose, code_indent):
        self.verbose = verbose
        self.code_indent = code_indent
        super().__init__()
        self.lines = []

    def fail(self, reason):
        msg = f'Columns: {reason}'
        if self.verbose:
            print(msg, file=stderr)
        raise ColumnsException(msg)

    @staticmethod
    def get_columns(spaces):
        """ look at array of boolean spaces and return list a (start, end) of each
            actual text column, which is two or more spaces from next actual text column.

            for .=True, x=False, "x..xx.x." gives (0,0), (3,6)
            returns list of (start, end) tuples of text columns
        """
        starts = [i for (i, sp) in enumerate(spaces)
                  if sp and (i == 0 or not spaces[i - 1])]
        ends = [i for (i, sp) in enumerate(spaces)
                if sp and (i == len(spaces) - 1 or not spaces[i + 1])]
        space_cols = [(start, end) for (start, end) in zip(starts, ends)
                      if end - start > 0]
        text_cols = []
        if space_cols and space_cols[0][0] > 0:
            text_cols.append((0, space_cols[0][0] - 1))  # text starting at zero
        for i in range(1, len(space_cols)):
            text_cols.append((space_cols[i - 1][1] + 1, space_cols[i][0] - 1))
            # (one after last column, to one before next column), 0 width OK
        if space_cols and space_cols[-1][1] < len(spaces):
            text_cols.append((space_cols[-1][1] + 1, len(spaces) - 1))
            # (one after final column, to end of line)
        return text_cols

    def find_table_extent(self, start_line_num, lines):
        """ Find last line of table and column numbers for text in that table, else throw ColumnsException.

            Table ends with two blank lines or the end of the file.

            returns (last_line, List[Tuple[start_col, end_col]])
        """
        spaces = []  # List[Bool], true if table has all spaces in this column
        line_num = start_line_num
        was_last_blank = False
        while line_num < len(lines):
            line = lines[line_num].rstrip()
            if line:
                was_last_blank = False
                spaces = [ch == ' ' and (i > len(spaces) or spaces[i])
                          for (i, ch) in enumerate(line)]
            else:
                if was_last_blank:
                    break  # two lines, return whatever we found so far
                was_last_blank = True
            line_num += 1
        if line_num >= len(lines):
            line_num = len(lines) - 1  # ends on last line
        cols = self.get_columns(spaces)
        if len(cols) < 2:
            self.fail(f'Need at least two columns, lines:{start_line_num}-{line_num}')
        if line_num - start_line_num < 2:
            self.fail(f'table too short, lines {start_line_num}-{line_num}')
        if cols[0][0] >= self.code_indent:
            self.fail(f'table starts too far in and is a code block, lines {start_line_num}-{line_num}')
        return line_num, cols

    def transform_table(self, line_num, lines):
        """
        Tries to transform a table starting at line_num in lines.
        :return: (ending_line_of_table, transformed_table_lines) if table started here, else (None, [])
        """

        class TableLine:
            def __init__(self, text, cols_):
                self.text = text
                self.kind = 'tbd'
                self.col_text = [text[start:end + 1] for (start, end) in cols_]

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
            for line in table:
                if line.kind == 'tbd':
                    if line.has_calculated():
                        line.kind = 'calc'
                    if line.text:
                        line.kind = 'data'
                    else:
                        line.kind = 'sep'  # might be bottom of table, but will delete it soon

        def fix_calculated():
            # just totals for now.
            for line in table:
                for col_text in line.col_text:
                    if '<+>' in col_text:
                        pass

        def emit_lines():
            out = [tag('start_table')]
            for line in table:
                if line.kind in ('header', 'data', 'footer', 'calc'):
                    out.append(tag(f'start_{line.kind}'))
                    the_tag = tag(f'col_{line.kind}')
                    for col_text in line.col_text:
                        out.append(f"{the_tag} {col_text}")
                    out.append(tag(f'end_{line.kind}'))
                elif line.kind == 'sep':
                    out.append(tag('sep'))
                else:
                    self.fail(f'Internal error, odd kind: {line.kind} in {line.text}')
            return out

        after_space = line_num == 0 or not lines[line_num - 1].strip()
        has_spaces = '  ' in lines[line_num].rstrip()
        if after_space and has_spaces:  # skip common not-a-table case
            try:
                (ending_line, cols) = self.find_table_extent(line_num, lines)
                if ending_line > len(lines):
                    raise Exception(f"Da fuq?  line {ending_line}")
                table = [TableLine(line, cols) for line in lines[line_num: ending_line]]
                mark_headers()
                mark_body()
                mark_footers()
                fix_calculated()
                new_lines = emit_lines()
                return ending_line, new_lines
            except ColumnsException:
                pass  # not a table, just fall through
        return None, []  # bail on most common case

    def run(self, lines):
        """ markdown extension API entry.  Gets big string, returns transformed big string """
        out = []
        line_num = 0
        while line_num < len(lines):
            (ending_line, table_lines) = self.transform_table(line_num, lines)
            if ending_line is not None:
                out.extend(table_lines)
                line_num = ending_line + 1
            else:
                out.append(lines[line_num])
                line_num += 1
        return '\n\n'.join(out).splitlines()



class ColumnsPostprocessor(Postprocessor):
    def __init__(self, verbose, style):
        self.verbose = verbose
        self.style = style
        super().__init__()

    def run(self, text):
        replacements = {
            'start_table': '<table>',
            'end_table': '</table>',
            'start_data': '<tr>',
            'end_data': '</tr>',
            r'col_data ([^\n]*)': r'<td>\1</td>'
        }
        for pattern, rep in replacements.items():
            text = re.sub(tag(pattern), rep, text)
        return text


class ColumnsExtension(Extension):
    def __init__(self, **kwargs):
        self.config = {
            'verbose': [False, 'print extra information to stdout'],
            'style': ['default', 'style type: default, bare, or stylesheet filename']}
        super().__init__(**kwargs)

    def extendMarkdown(self, md):
        md.preprocessors.register(
            ColumnsPreprocessor(self.getConfig('verbose'), code_indent=md.tab_length),
            'columns', 25)  # run after normalizing text but before html
        md.postprocessors.register(
            ColumnsPostprocessor(self.getConfig('verbose'), self.getConfig('style')), 'columns', 35)  # first


def makeExtension(**kwargs):
    return ColumnsExtension(**kwargs)
