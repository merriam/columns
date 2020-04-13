from markdown.extensions import Extension
from markdown.inlinepatterns import  SimpleTagPattern


# note, group 2 is expected to be the 'meat'
DEL_RE = r'(--)(.*?)--'
INS_RE = r'(__)(.*?)__'

class Columns(Extension):
    def extendMarkdown(self, md, md_globals):
        # create the del pattern
        del_tag = SimpleTagPattern(DEL_RE, 'del')
        # Insert del pattern into markdown parser
        md.inlinePatterns.add('del', del_tag, '>not_strong')

        ins_tag = SimpleTagPattern(INS_RE, 'ins')
        md.inlinePatterns.add('ins', ins_tag, '>del')




