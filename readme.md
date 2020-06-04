# Columns - Tables in Markdown

Columns adds tables to your markdown when you write them in the 
same way you normally would in email or any other text.
It does a simple job well.

## What's a table?

A table is text with at least two columns of at least two spaces running from top to bottom. A document like this:

    California   39.5   40
    Texas        29.0   26.2
    
is a table that renders as:

California   39.5   40
Texas        29.0   26.2


You can add headers and footers using lines of punctuation 
(`-`, `=`, `+`, or `#`) after the first line or before the last line:

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

## Getting fancy

Tables written text have a few fancy bits:  totals, blank lines, and lists.  Totals, counts, percentages, and averages
can be used in the footer by having `<+>`, `<#>`, `<%>` or `<avg>` respectively.  Skipping a single line makes a 
blank table line.  You can use lists in columns, just write like you would in markdown.  Finally, note that columns
are really forgiving about aligning things perfectly.

That means we make this table:

**Selected Populations**

Country                     Population (Millions)
-----
* Asia
    - China                   1,439
    - India                   1,379
    - Indonesia              273
    
* Americas
    * North America
        - United States       330
        - Mexico              129
    * South America
        - Brazil              212
                            <+> (in <#> countries)     <%>


comes typing:

    **Selected Populations**
    
    Country                 Population (Millions)
    -----
    * Asia
        - China                   1,439
        - India                   1,379
        - Indonesia              273
        
    * Americas
        * North America
            - United States       330
            - Mexico              129
        * South America
            - Brazil              212
                                <+> (in <#> countries)     <%>

## Getting More Fancy

You might want to get more fancy:  different fonts; ; subtotals.  You can use 
use an html style tags for some flair.  For more control, just escape to html
and build your own table. *Columns* is only useful for simple tables, not for making a rendering
language.

## Getting Technical

Knowing what makes a table helps when it doesn't render as you 
expect.   A table is at least one blank line, optional headers, optional data,
an optional total line, and, finally, at least two blank lines.  The table
must be at least rows, including header and footer.  It also needs least two columns.

A column is made by having multiple spaces running top to bottom through the whole block 
of text.  You can indent the first line, e.g., column headers.  If the whole table is indented,
though, it can become a Markdown code block.