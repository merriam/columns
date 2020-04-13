import markdown
from columns import Columns

o = markdown.markdown('foo __ins__ --deleted-- __ins__ bar', extensions=[Columns()])
print(o)