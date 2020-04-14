from markdown.extensions import Extension
from markdown.inlinepatterns import Pattern
import xml.etree.ElementTree as etree

# note, group 2 is expected to be the 'meat'
DEL_RE = r'(--)(.*?)--'
INS_RE = r'(__)(.*?)__'
STRONG_RE = r'(\*\*)(.*?)\*\*'
EMPH_RE = r'(\/\/)(.*?)\/\/'
MULTI_RE = r'([*/_-]{2})(.*?)\2'


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


class MultiExtension(Extension):
    def extendMarkdown(self, md):
        # Delete the old patterns
        del md.inlinePatterns['em_strong']
        del md.inlinePatterns['em_strong2']
        del md.inlinePatterns['not_strong']
        multi = MultiPattern(MULTI_RE)
        md.inlinePatterns['multi'] = multi


