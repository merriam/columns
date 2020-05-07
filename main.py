import os
import time

import markdown
from markdown.extensions import Extension
from markdown.inlinepatterns import InlineProcessor
from markdown.blockprocessors import BlockProcessor
from markdown.inlinepatterns import SimpleTagInlineProcessor
import xml.etree.ElementTree as etree
import re
import webbrowser
from tempfile import NamedTemporaryFile

from samples import tutorial1, deflist1, sample1, sample2, sample3, sample4, sample5, sample6, sample7, sample8, \
    sample9, del1, box1, nesting_bad


def run_tutorial():
    txt = tutorial1
    print(markdown.markdown(txt, extensions=['tutorial']))
    print(markdown.markdown(txt,
                            extensions=['tutorial'],
                            extension_configs={
                                'tutorial': {'ins_del': True}
                            }))


def run_def_list():
    txt = deflist1
    print(markdown.markdown(txt, extensions=['def_list']))


def show_page(titles, inps, outs):
    o = ''
    for title, inp, out in zip(titles, inps, outs):
        o += f'''
<link rel="stylesheet" href="file:///Users/charlesmerriam/p/columns/blue.css" type="text/css">
        <h1>{title}</h1>\n
        <h4>Render:</h4>\n
        {out}\n
        <h3>Input:</h3>\n
        <pre>{inp}</pre><hr>\n
        <h3>Output:</h3>\n
        <h4>Source:</h4>\n
        <code><pre>{out.replace('<', '&lt;')}</pre></code><hr>\n
        <hr><hr>'''
    f = NamedTemporaryFile(mode='w', suffix='.html', delete=False)
    f.write(o)
    f.close()
    webbrowser.open('file://' + f.name)
    time.sleep(5)
    os.unlink(f.name)

def test_columns():
    out = markdown.markdown(sample1, extensions=['columns'])
    assert '<table' in out

def play_columns():
    texts = [sample1, sample2, sample3, sample4, sample5, sample6, sample7, sample8, sample9]
    texts = [sample1, sample7, sample8, sample9]
    outs = []
    titles = []
    for text in texts:
        titles.append(text.strip().splitlines()[0])
        outs.append(markdown.markdown(text,
                                      extensions=['columns'],
                                      extension_configs={
                                          'columns': {'verbose': True}
                                      }))
    show_page(titles, texts, outs)


def play_inline_del_short():
    class DelExtension(Extension):
        def extendMarkdown(self, md):
            md.inlinePatterns.register(
                SimpleTagInlineProcessor(r'()--(.*?)--', 'del'),
                'del', 175)

    txt = del1
    print(markdown.markdown(txt, extensions=[DelExtension()]))


def play_inline_del_long():
    DEL_PATTERN = r'--(.*?)--'  # like --del--

    class DelInlineProcessor(InlineProcessor):
        def handleMatch(self, m, data):
            el = etree.Element('del')
            el.text = m.group(1)
            return el, m.start(0), m.end(0)

    class DelExtension(Extension):
        def extendMarkdown(self, md):
            md.inlinePatterns.register(DelInlineProcessor(DEL_PATTERN, md), 'del', 175)

    txt = del1
    print(markdown.markdown(txt,
                            extensions=[DelExtension()],
                            extension_configs={
                                'columns': {'verbose': True}
                            }))


def play_box_processor():
    class BoxBlockProcessor(BlockProcessor):
        RE_FENCE_START = r'^ *!{3,} *\n'  # start line, e.g., `   !!!! `
        RE_FENCE_END = r'\n *!{3,}\s*$'  # last non-blank line, e.g, '!!!\n  \n\n'

        def test(self, parent, block):
            return re.match(self.RE_FENCE_START, block)

        def run(self, parent, blocks):
            original_block = blocks[0]
            blocks[0] = re.sub(self.RE_FENCE_START, '', blocks[0])

            # Find block with ending fence
            for block_num, block in enumerate(blocks):
                if re.search(self.RE_FENCE_END, block):
                    # remove fence
                    blocks[block_num] = re.sub(self.RE_FENCE_END, '', block)
                    # render fenced area inside a new div
                    e = etree.SubElement(parent, 'div')
                    e.set('style', 'display: inline-block; border: 1px solid red;')
                    self.parser.parseBlocks(e, blocks[0:block_num + 1])
                    # remove used blocks
                    for i in range(0, block_num + 1):
                        blocks.pop(0)
                    return True  # or could have had no return statement
            # No closing marker!  Restore and do nothing
            blocks[0] = original_block
            return False  # equivalent to our test() routine returning False

    class BoxExtension(Extension):
        def extendMarkdown(self, md):
            md.parser.blockprocessors.register(BoxBlockProcessor(md.parser), 'box', 175)

    text = box1
    print(markdown.markdown(text,
                            extensions=[BoxExtension()]))


def play_break():
    print(markdown.markdown(nesting_bad, extensions=['extra']))


if __name__ == '__main__':
    test_columns()
    play_columns()
