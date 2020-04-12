# Columns - Tables in Markdown

Columns lets you add tables to your markdown in the same way you add tables to email or any other text.  It does a simple job well and leaves corner cases to html escapes.

## What's a table?

A table has columns of at least two spaces running from top to bottom. You write it:

    California   39.5
    Texas        29.0

It renders as:

California   39.5
Texas        29.0

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

If you want to get fancy, you can use lists and subtotals:

    California          <+>                <%>
    * Born US Citizen
    * Foreign Born
    Texas               <+>                <%>
    * Born US Citizen
    * Foreign Born
    _Total_            _<+> (avg <avg>)_              <%>


California          <+>                <%>
* Born US Citizen
* Foreign Born
Texas               <+>                <%>
* Born US Citizen
* Foreign Born
_Total_            _<+> (avg <avg>)_              <%>




Notice that `<+>` on subtotal lines add up the numbers in the sublists, but on the total line it adds up the numbers not already subtotaled.  Also, the `<%>` is always a new column of the first real (not `<%>` or `<avg>`) numbers on the left, so it needs two columns for perecentages.

## Getting Technical

It can be good to know what makes a table for the times when it doesn't render like you expect.   A table is at least one blank line, optional headers, two or more rows of data with no more than one blank line between rows, an optional total line, and, finally, at least two blank lines.  A
row of data needs at least two columns, meaning at least two columns of two or more spaces from the headers, through all the data, and through the footer.  Columns are really forgiving about alignment, as long as they overlap somewhere.  The only trick is that the first line cannot be indented so much it becomes a Markdown code block, so use a `\<space>` at the front:

    \                                Total
                                 --
    California                     39.5
            Texas                     29.0
                  Rhode Island  1.0


\                                Total
                              --
California                     39.5
        Texas                     29.0
              Rhode Island  1.0


If you really want, you can overwrite the default styling by using an html escape to set a \<style> to overwrite styles starting with `col_style_`.   If you want to do fancy things like number formatting or values spanning multiple columns, you should use a \<table> html-escape instead.
