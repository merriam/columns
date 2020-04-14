import markdown
from columns import MultiExtension

txt = """
This is __ins__ text
This is --strike-- or --del-- text
This is **bold** text
This is //italics//, versus *old italics* text
This is *old italics*, **old bold** and ***old confusing*** text
"""
o = markdown.markdown(txt, extensions=[MultiExtension()])
print(o)
