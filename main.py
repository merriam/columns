import markdown
from columns import Columns

txt = """
This is __ins__ text
This is --strike-- or del text
This is **bold** text
This is //italics// text
This is *old italics*, **old bold** and ***old confusing*** text
"""
o = markdown.markdown(txt, extensions=[Columns()])
print(o)
