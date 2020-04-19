import markdown
from markdown.extensions import Extension
from markdown.inlinepatterns import Pattern
import xml.etree.ElementTree as etree

# note, group 2 is expected to be the 'meat'
DEL_RE = r'(--)(.*?)--'  # for --del--
INS_RE = r'(__)(.*?)__'  # for __ins__
STRONG_RE = r'(\*\*)(.*?)\*\*' # for **strong88
EMPH_RE = r'(\/\/)(.*?)\/\/'   # for //emphasis//
STRONG_EM_RE = r'([*/]{2})(.*?)\2'  # for **strong** or //emphasis//
INS_DEL_RE = r'([_-]{2})(.*?)\2'    # for __ins__ or --del--

class MultiPattern(Pattern):
    def handleMatch(self, m):
        # note match is group (1), the text before the match, group (2) the punctuation, group(3) inside
        if m.group(2) == '**':
            tag = 'strong'  # bold
        elif m.group(2) == '//':
            tag = 'em'  # Italics
        elif m.group(2) == '__':
            tag = 'ins'  # underline
        else:  # m.group(2) == '--'
            tag = 'del'  # strike

        # Create the element
        el = etree.Element(tag)
        el.text = m.group(3)
        return el


class ConfigExtension(Extension):
    def __init__(self, **kwargs):
        # define options and defaults
        self.config = {
            'ins_del': [False, 'enable Insert and Delete syntax']
        }
        # call parent to config the options
        super().__init__(**kwargs)

    def extendMarkdown(self, md):
        # Delete the old patterns
        del md.inlinePatterns['em_strong']
        del md.inlinePatterns['em_strong2']
        del md.inlinePatterns['not_strong']
        md.inlinePatterns['strong_em'] = MultiPattern(STRONG_EM_RE)
        if self.getConfig('ins_del'):
            md.inlinePatterns['ins_del'] = MultiPattern(INS_DEL_RE)


def makeExtension(*args, **kwargs):
    return ConfigExtension(*args, **kwargs)
