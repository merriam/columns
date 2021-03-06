
sample1 = """
    
Notice the trend here?



California     39.5   40
0123456789     3456   0123
Texas *Ya!*   29.0   26.2

Antarctica     0.0    -


This is not part of the table because it is a two line break from above.  

Notice that:

* California has a *much* bigger number than Texas both times!
* No title or footer rows
* Texas *Ya!* has emphasized text in the table
* Separator line between Texas and Antarctica


"""
sample2 = """
I have headers and footers using separators 

State            Population
                 ---------------------
California         39.5
Texas              29.0
                  ++++
Total (million)    68.5 
"""
sample3 = """
  I have headers and footers with punctuation
  
  *State*        *Population*
  California     39.5
  Texas          29.0
  _Total_        _68.5 (million)_"""
sample4 = """
I am not a table

I'm not a table because I am indented too far.

      *State*        *Population*
      California     39.5
      Texas          29.0
      _Total_        _68.5 (million)_
      
and I'm not because my fields overlap.

  *State*        *Population*
  California Republic    39.5
  Texas          29.0
  _Total_        _68.5 (million)_
  
And I'm not because I didn't skip a space, so fields overlap.
California     39.5
Texas          29.0
_Total_        _68.5 (million)_

And I'm not because I only have one column
California    
Texas         
_Total_

And I'm too short

California     39.5

And I have a total outside the footer:

State       <+>
California Republic    39.5
Texas          29.0


California Republic    39.5   <%>
Texas          29.0

"""
sample5 = """
I have computed fields in my footer

California        39.5
Texas             29.0
-------------
_<#> States_      _<+> (average <avg>)_   <%>
"""
sample6 = """
I have blank lines and numeric alignment

Washington    12.5
  Oregon         2.5
California    39.5

Texas         29.0
Arkansas      13.4"""
sample7 = """
I have lists and commas in my totals

California          
* Born US Citizen  28883435
* Foreign Born     10628788
Texas               
* Born US Citizen  24066582
* Foreign Born     4929300
_Total_            _<+> (avg <avg>)_              <%>
"""
sample8 = """
I have crazy alignment.

                                Total
                              --
California                     39.5
        Texas                     29.0
              Rhode Island  1.0
"""
sample9 = """
Dashes are tricky

               2nd column title indented like code block
-
Dash above is  title line separator
-              dash is 'no-value' for counting
Dash below is  footer line separator
-
2 items (<#>)  <+>=0 from no numbers
"""
sample10 = """
Tables have outlines

First Label                             Second Label
-----------                             -------
Top level                               9.  ordered
* Down one                              10. more 
  * Two                                     and I'm just indented as if I'm part of it.
* One again                             * Now bullet
  * Two more                            1.  back to numbers
    + Three                                 1.  nums in nums
  2. Two some more                           2.  in nums
        * Three just indented more      3.  out numbes
Top Again
        + One just under indented more
        
Notice how outlines are independent.  Once in a list, switching the symbol, or between ordered and unordered, is ignored.
        
"""
del1 = """
First line of the block.
This is --strike one--.
This is --strike two--.
End of the block.
"""
box1 = """
You could create zombies by mixing lime and coconut.

!!!!!
Never do that!

Everyone might **die**!
!!!!!

Let's not.
"""
nesting_bad = """
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
nesting_good = """
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

tutorial1 = """
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
deflist1 = """

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