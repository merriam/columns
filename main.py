import markdown


def run_tutorial():
    txt = """
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
    print(markdown.markdown(txt, extensions=['tutorial']))
    print(markdown.markdown(txt,
                            extensions=['tutorial'],
                            extension_configs={
                                'tutorial': {'ins_del': True}
                            }))

def run_def_list():
    txt= """
We should make *DEFLISTS*
It would be fun.

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
    print(markdown.markdown(txt, extensions=['def_list']))

def run_columns():
    txt = """
Notice the trend here?

California   39.5   40
Texas *X*    29.0   26.2


Calfornia has a *much* bigger number than Texas both times!

** bold works **
Nothing changes
"""
    print(markdown.markdown(txt,
                            extensions=['columns'],
                            extension_configs={
                                'columns': {'verbose': True}
                            }))


if __name__ == '__main__':
    run_def_list()
    # run_columns()
