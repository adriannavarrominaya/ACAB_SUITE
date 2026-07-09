#F. Block #6

Block #6 consists of two cards: card #1 (IDNUM array, integer free-format), and card #2 (XFEED array, real free-format). This block is used to specify materials that are subject to continuous feed. This block must be repeated if more than one zone undergoes continuous feed. That is, the total number of times block #6 must appear is equal to number of components of array ISOZO not set to zero. This block is only required if INFD > 0.

|Card #|Parameter|Description|
|------|---------|-----------|
|1|IDNUM|Identification of the element or isotope with continuous feed. [ISOZO].|
|2|XFEED|Feed rates in g−atoms (moles) per second. [ISOZO]{INDFD > 0}.|

**Example**

```plaintext
<IDNUM
260000
<XFEED
1.00E+00
```

This example indicates that natural iron is continuously fed at a rate of 1 g−atoms/s.