# E. Block #5

Block #5 is used to specify the initial material composition in a non-restart run.
This block must be omitted for a restart run. The nuclide identifier is defined as:

```plaintext
NUCLID = 10000 × Z + 10 × A + IS
```

where:

- Z = atomic number,
- A = atomic mass of nuclide, and
- IS = state indicator (0 = ground state, 1 = first isomeric state, and 2 = second isomeric state)

The identifier for an element follows the pattern set by the nuclide identifier:

```plaintext
ELEMID = 10000 × Z.
```

The block #5 consists of two cards: card #1 (INUCL array, integer free-format), and card #2 (XCOMP array, real free-format). This block must be repeated if more than one material zone is to be considered. That is, the total number of times block #5 must appear is equal to number of components of array NUCZO (set in block #2) not set to zero.

|Card #|Parameter|Description|
|------|---------|-----------|
|1|INUCL|Identifiers of the initial elements or isotopes. [NUCZO].|
|2|XCOMP|Concentrations of the initial elements or isotopes given in units of atoms/barn–cm. [NUCZO].<br>If INPT=3, initial elements in units g/cc.|


**Example #1**

```plaintext
<INUCL
80000 120000 130000
<XCOMP
6.09E-02 1.52E-02 3.05E-02
```

This example specifies that the elements oxygen, magnesium, and aluminum are the initial constituents of the material being irradiated. They are present in 6.09 × 10<sup>22</sup>, 1.52 × 10<sup>22</sup>, and 3.05 × 10<sup>22</sup> atoms/cc, respectively    (10<sup>24</sup> atoms/cc = 1 atom × barn<sup>-1</sup> × cm<sup>-1</sup>).

**Example #2:**

```plaintext
<INUCL
741860
<XCOMP
6.00E-02
```

The second example is for the irradiation of <sup>187</sup>W. It is present at an atomic density of 6.00 × 10<sup>22</sup> atoms/cc.