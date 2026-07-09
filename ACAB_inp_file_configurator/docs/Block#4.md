# D. Block #4

It consists of only one card that is read in integer free-format. Block #4 allows for a RESTART OPTION, and is currently implemented for one material zone and one interval. The restart option can be very useful for calculations under pulsed irradiation regimes characteristc of conceptual IFE reactors., and it works as follows.
ACAB produces in all inventory calculation runs the UNIT37, which contains the composition in g-atom for all isotopes in the last time step of the problem. This UNIT can be used as input of new initial material composition if you want to continue the calculation in a new run.

## Card #1

|#|Parameter|Description|
|-|---------|-----------|
|1|IREST|Indicator for restart option.<br> - **0** No effect.<br> - **1** The initial material composition is read from UNIT 37, instead of using BLOCK #5 (this is used as explained next, for a non-restart case).|

**Example**

```plaintext
<IREST
0
```

A non-restart case is considered, and UNIT 37 is not read. Initial composition must be given in block #5.