import markdown
from columns import Columns

o = markdown.markdown('foo --deleted-- bar', extensions=[Columns()])
print(o)