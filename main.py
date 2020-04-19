import markdown


def run_tutorial():
    txt = """
&!&!this&!&!
        
This is __ins__ text
This is --strike-- or --del-- text
This is **bold** text
This is //italics//, versus *old italics* text
This is *old italics*, **old bold** and ***old confusing*** text
        """
    print(markdown.markdown(txt, extensions=['tutorial']))
    print(markdown.markdown(txt,
                            extensions=['tutorial'],
                            extension_configs={
                                'tutorial': {'ins_del': True}
                            }))


def run_columns():
    txt = """
** bold works **
Nothing changes
"""
    print(markdown.markdown(txt,
                            extensions=['columns'],
                            extension_configs={
                                'columns': {'verbose': True}
                            }))


if __name__ == '__main__':
    run_columns()
