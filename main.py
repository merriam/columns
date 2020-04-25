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

tutorial_text = """
&!&!this&!&!
        
This is __ins__ text
This is --strike-- or --del-- text
This is **bold** text
This is //italics//, versus *old italics* text
This is *old italics*, **old bold** and ***old confusing*** text

* list
* list
   *  four deep
    * five deep

        """

deflist_text = """
    
This is a [reference][here] thing
[here]:  https://thing 'this thing'    
    
This is a [two line reference][there] thing
[there]:  https://thing
    "optional title"
    
We should make *DEFLISTS*
It would be fun.
This has a plus <+> and avg <avg>

This is the line before

: Here is a *paragraph* starting with a colon
but doing nothing else interesting.

This paragraph is like the previous one but has
: the colon line
in the middle

Word
:   def 1
:   def 2
    : def 3

But should be:

A
    : is for apple
B   : is for bear
    : is for bitch


: this is _just_ a paragraph

Apple
:   An apple
    A Computer
    
See how cool that is?
That is very cool.
:   So cool

Yes that is
: so cool

See
"""
col1_text = """
    
Notice the trend here?



California   39.5   40
0123456789   3456   0123
Texas *X*    29.0   26.2

Antartica     0.0    -


Not table

California has a *much* bigger number than Texas both times!

** bold works **
Nothing changes
"""
del_text = """
First line of the block.
This is --strike one--.
This is --strike two--.
End of the block.
"""
box_text = """
You could create zombies by mixing lime and coconut.

!!!!!
Never do that!

Everyone might **die**!
!!!!!

Let's not.
"""
bad_nesting_text = """
<div class="row" markdown="1">
<div class="col-md-6" markdown="1">
**SomeText**
</div>

<div class="col-md-6" markdown="1">

**bold text**  

<small>(<i class="fa fa-arrow-left"></i> small)</small>

<div class="barchart" markdown="1">
* item1
* item2
</div>

more text

</div>
</div>
"""
good_nesting_text = """
<div class="row" markdown="1">
    <div class="col-md-6" markdown="1">
        **SomeText**
    </div>
    <div class="col-md-6" markdown="1">
        **bold text**  
        <small>(<i class="fa fa-arrow-left"></i> small)</small>
        <div class="barchart" markdown="1">
            * item1
            * item2
        </div>
        more text
    </div>
</div>
"""


def run_tutorial():
    txt = tutorial_text
    print(markdown.markdown(txt, extensions=['tutorial']))
    print(markdown.markdown(txt,
                            extensions=['tutorial'],
                            extension_configs={
                                'tutorial': {'ins_del': True}
                            }))


def run_def_list():
    txt = deflist_text
    print(markdown.markdown(txt, extensions=['def_list']))


def show_page(titles, inps, outs):
    o = ''
    for title, inp, out in zip(titles, inps, outs):
        o += f'''
<link rel="stylesheet" href="file:///Users/charlesmerriam/p/columns/blue.css" type="text/css">
<h1>{title}</h1>\n
        <h3>Input:</h3>\n
        <pre>{inp}</pre><hr>\n
        <h3>Output:</h3>\n
        <h4>Source:</h4>\n
        <code><pre>{out.replace('<', '&lt;')}</pre></code><hr>\n
        <h4>Render:</h4>\n
        {out}<hr><hr>\n'''
    f = NamedTemporaryFile(mode='w', suffix='.html', delete=False)
    f.write(o)
    f.close()
    webbrowser.open('file://' + f.name)
    time.sleep(5)
    os.unlink(f.name)


def run_columns():
    texts = [col1_text]
    outs = []
    for text in texts:
        outs.append(markdown.markdown(text,
                                      extensions=['columns'],
                                      extension_configs={
                                          'columns': {'verbose': True}
                                      }))
    show_page("Basic Columns", texts, outs)


def test_inline_del_short():
    class DelExtension(Extension):
        def extendMarkdown(self, md):
            md.inlinePatterns.register(
                SimpleTagInlineProcessor(r'()--(.*?)--', 'del'),
                'del', 175)

    txt = del_text
    print(markdown.markdown(txt, extensions=[DelExtension()]))


def test_inline_del_long():
    DEL_PATTERN = r'--(.*?)--'  # like --del--

    class DelInlineProcessor(InlineProcessor):
        def handleMatch(self, m, data):
            el = etree.Element('del')
            el.text = m.group(1)
            return el, m.start(0), m.end(0)

    class DelExtension(Extension):
        def extendMarkdown(self, md):
            md.inlinePatterns.register(DelInlineProcessor(DEL_PATTERN, md), 'del', 175)

    txt = del_text
    print(markdown.markdown(txt,
                            extensions=[DelExtension()],
                            extension_configs={
                                'columns': {'verbose': True}
                            }))


def test_box_processor():
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

    text = box_text
    print(markdown.markdown(text,
                            extensions=[BoxExtension()]))


def test_break():
    print(markdown.markdown(bad_nesting_text, extensions=['extra']))


if __name__ == '__main__':
    run_columns()
