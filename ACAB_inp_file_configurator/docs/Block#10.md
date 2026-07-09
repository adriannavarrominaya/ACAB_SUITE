# I. Block #10

It consists of only one card that is read in integer free-format. This block is used to control the computing of fission product inventory.

## Card #1

|#|Parameter|Description|
|-|---------|-----------|
|1|IGFP|Option to calculate the inventory of fission products if actinides were initially present.<br>- **0** No effect. All nuclear reactions, including fission, are considered in the calculation. But fission yield data are assumed to be zero (UNIT 96 is not read).<br>- **1** Fission products are included in inventory calculations. (UNIT 96 must be given).|
|2|IWFYD|Type of effective fission yield cross section library (UNIT 96).<br>No effect if IGFP is equal to zero.<br>- **0** Weighted fission yield cross sections (or weighted fission yield data) for all fissionable nuclides included in the basic fission yield data library are read.<br>- **1** Effective fission yield cross  sections (or effective fission yield data) for all fissionable nuclides included in the activation library (UNIT 4) are read.
|3|IFORT96|Type of effective fission yield library (UNIT 96).<br>- **0** Effective fission product yield <$\gamma$>, FY.dat.<br>- **1** Effective fission yield cross section <$\gamma\sigma$>, FYXS.dat.|

**Example #1**

```plaintext
1         1        1
```

This card tells ACAB to read UNIT 96 that includes fission yield cross sections
from all the fissionable nuclides in the activation library.

**Example #2**

```plaintext
0         1        0/1
```

The UNIT 96 is not read, so ACAB does not deal with fission products. It does not matter the value of the second parameter.
