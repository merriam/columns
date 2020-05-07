# Columns - Tables in Markdown

Columns adds tables to your markdown when you write them in the 
same way you normally would in email or any other text.
It does a simple job well.

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


You can add headers and footers using lines of punctuation 
(`-`, `=`, `+`, or `#`) or using bold or underline on each column:

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

## Getting fancy

Wouldn't it be nice to keep the totals up to date when putting more states in the table?   
You can use `<+>`, `<#>`, `<%>` and `<avg>` in the footer lines:

    California        39.5
    Texas             29.0
    _<#> States_      _<+> (average <avg>)_   <%>


California        39.5
Texas             29.0
_<#> States_      _<+> (average <avg>)_   <%>

You can add occasional blank lines:
    
    Washington    12.5
    Oregon         2.5
    California    39.5
    
    Texas         29.0
    Arkansas      13.4

You can use ordered and unordered lists:

    California          
    * Born US Citizen  28883435
    * Foreign Born     10628788
    Texas              
    1.  Born US Citizen  24066581
    1. Foreign Born     4929300
    _Total_            _<+> (avg <avg>)_              <%>

California          <+>                <%>
* Born US Citizen  28883435
* Foreign Born     10628788
Texas               <+>                <%>
* Born US Citizen  24066581
* Foreign Born     4929300
_Total_            _<+> (avg <avg>)_              <%>


## Getting Technical

Knowing what makes a table helps when it doesn't render as you 
expect.   A table is at least one blank line, optional headers, optional data,
an optional total line, and, finally, at least two blank lines.  The table
must be at least rows, including header and footer.  It also needs least two columns.

A columns are made by having multiple spaces running top to bottom.  If 
the whole table is indented it can become a Markdown code block.  Columns are 
forgiving about alignment because spaces don't change rendering outside of lists.  
For example, this table is just two columns:

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


You can overwrite the default styling by using an html escape to set a \<style> to 
overwrite styles starting with the class `columns_table`.   Columns make simple tables
which humans would intuit from the text.  For a fancier table, use a \<table> html-escape 
instead.
