# Columns - Tables in Markdown

Columns lets you add tables to your markdown in the 
same way you add tables to email or any other text.
It does a simple job well and leaves corner cases to html escapes.

## What's a table?

A table has columns of at least two spaces running from top to bottom. A document like this:

```
Notice the trend here?

California   39.5   40
Texas        29.0   26.2


Calfornia has a bigger number than Texas both times!
```   
It renders as:

Notice the trend here?

California   39.5   40
Texas        29.0   26.2


Calfornia has a bigger number than Texas both times!


You can add headers and footers using lines of punctuation (`-`, `=`, `+`, or `#`) or using bold or underline one each column:

    State          Population
                   ---------------------
    California     39.5
    Texas          29.0
                   ++++
    Total          68.5 (million)


State           Population
                ---------------------
California      39.5
Texas           29.0
                ++++
Total           68.5 (million)


or

    *State*        *Population*
    California     39.5
    Texas          29.0
    _Total_        _68.5 (million)_

  *State*        *Population*
  California     39.5
  Texas          29.0
  _Total_        _68.5 (million)_


Wouldn't it be nice to keep the totals up to date when putting more states in the table?   You can use `<+>`, `<#>`, `<%>` and `<avg>` in the total lines:

    California        39.5
    Texas             29.0
    _<#> States_      _<+> (average <avg>)_   <%>


California        39.5
Texas             29.0
_<#> States_      _<+> (average <avg>)_   <%>

## Getting fancy

You can add occasional blank lines:
    
    Washington    12.5
    Oregon         2.5
    California    39.5
    
    Texas         29.0
    Arkansas      13.4

If you want to get fancy, you can use lists and subtotals:

    California          <+>                <%>
    * Born US Citizen  28883435
    * Foreign Born     10628788
    Texas               <+>                <%>
    * Born US Citizen  24066581
    * Foreign Born     4929300
    _Total_            _<+> (avg <avg>)_              <%>

California          <+>                <%>
* Born US Citizen  28883435
* Foreign Born     10628788
Texas               <+>                <%>
* Born US Citizen  24066581
* Foreign Born     4929300
_Total_            _<+> (avg <avg>)_              <%>




Notice that `<+>` on subtotal lines add up the numbers in the sublists, but on the total line it adds up the numbers not already subtotaled.  Also, the `<%>` is always a new column of the first real (not `<%>` or `<avg>`) numbers on the left, so it needs two columns for perecentages.

## Getting Technical

It can be good to know what makes a table for the times when it doesn't render like you 
expect.   A table is at least one blank line, optional headers, two or more rows of 
data with no more than one blank line between rows, an optional total line, and, finally, 
at least two blank lines.  You need at least two lines, including headers and footers.  
You need at least two columns, meaning multiple spaces running top to bottom.

Columns are really forgiving about alignment, as long as they overlap somewhere.  
The only trick is that the first column cannot be indented so much it becomes a Markdown 
code block:

                                    Total
                                 --
    California                     39.5
            Texas                     29.0
                  Rhode Island  1.0


                                Total
                              --
California                     39.5
        Texas                     29.0
              Rhode Island  1.0


If you really want, you can overwrite the default styling by using an html escape to 
set a \<style> to overwrite styles starting with `col_style_`.   If you want to do 
fancy things like number formatting or values spanning multiple columns, you should 
use a \<table> html-escape instead.
