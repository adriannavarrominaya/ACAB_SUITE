# M. Block #14

This block must be given if IUNC (see block #1, card #2) is equal to one, i.e., if the option for computing uncertainties in the activation calculations is chosen. Uncertainties in the concentration of a particular number of nuclides, as well as in some activation-related quantities (total activity, decay heat, etc.) are computed. A group of cards of this block tells ACAB about the times at which computing of uncertainties should be performed. The last group of cards specifies the nuclides for which concentration uncertainties are required. Cards of the block are read by ACAB as FORTRAN free format.

## Card #1

Card #1 provides the number of histories used in the Monte Carlo calculations, and parameters used to specify times and nuclides of interest. It tells if times of interest are included in the temporal cycles and the final series of sets used in modeling the irradiation/cooling history.

|#|Parameter|Description|
|-|---------|-----------|
|1|NMOHI|Number of histories used in computing uncertainties by the Monte Carlo method in the activation calculations. (NCYCO ≤ NOPUL+1).
|2|NTIMES|Number of times at which inventory uncertainties are required.|
|3|NCYU|Number of temporal cycles including some of the times of interest. (NCYU ≤ NOPUL+1). If NOPUL = 0, NCYU must be set to zero.|
|4|IFSU|Tells if times of interest are included in the final-set series.<br>- **0** No effect.<br>- **1** Uncertainties for some or all time sets of the final series.|
|5|NNUCU|Number of nuclides for which ACAB is required to calculate uncertainties in the number of atoms.

## Card #2

Card #2 only appears if NCYU ≠ 0. It is used to specify the cycles containing times of interest for uncertainty analysis.

|#|Parameter|Description|
|-|---------|-----------|
|1|ICYU|Integer numbers corresponding to the ordinal number of the cycles are used for cycle specification. [NCYU].

## Card #3

Card #3 is used to select and specify the time sets within the cycles and within the final-set series that contain the times of interest for uncertainty analysis.

|#|Parameter|Description|
|-|---------|-----------|
|1|ITSU|Specify the number of times of interest in each set. [NOTTS]|

## Card #4

This card must be provided as many times as the number of components of the array ITSU that are not set to zero. It is used for specification of the time of interest.

|#|Parameter|Description|
|-|---------|-----------|
|1|ITIMEU|Integer numbers corresponding to the ordinal number of the timesteps within a set are used for specification of the times of interest. The code understands that the ending times of these timesteps are the actual times of interest. [ITSU(I)].|

## Card #5

|#|Parameter|Description|
|-|---------|-----------|
|1|INUCU|Identifiers of the nuclides. The format of the identifier is that defined in block #5. [NNUCU]|

Example:

```plaintext
Example for computing uncertainties
1                                                              IUNC
1875 80000 0 0   1 0 2 2   0 0 1 0   4 1 1 0   1 0 0 1   0     NGRP
1.0 1.0      XRR
1           MA
< Total energy-integrated neutron flux. (Only one interval IM=1)
3.5083E+15         A single value per interval since IUNC=1
10 5 7 0     NOPUL NTSEQ NOTTS NVFL
< Block #14: Uncertainties block
1000   21   4   1   6   NMOHI   NTIMES   NCYU   IFSU   NNUCU
2   3   9   11          ICYU
1   0   1   0   2   2   3            ITSU
1               ITIMEU for  first set
10              ITIMEU for third set
9   10          ITIMEU for fifth set
9   10          ITIMEU for sixth set
8   9   10      ITIMEU for seventh set


60140  130260  260540  551370  771922 942390          INUCU
```

The option for Monte Carlo uncertainty calculations is active. The number of histories used in the analysis is 1000. Twenty ones times are of interest for uncertainty analysis. Some of these times of interest are included in cycles #2, 3, 9, and 11. As for these cycles, these times correspond to the ending time of the first timestep /interval for the first set, to the ending time of the tenth timestep for the third set, and to the ending times of the 9<sup>th</sup> and 10<sup>th</sup> timesteps for the 5th time set. In addition some times of interest are not included in any temporal cycle. As for the final-set series the times of interest correspond to the ending times of the 9<sup>th</sup> and 10th timesteps for the 6<sup>th</sup> time set, and to the ending times of the 8<sup>th</sup>, 9<sup>th</sup>, and 10<sup>th</sup> timesteps for the 7<sup>th</sup> time set. In addition, the desired nuclides to compute uncertainties in their concentrations are <sup>14</sup>C, <sup>26</sup>Al, <sup>54</sup>Fe, <sup>137</sup>Cs, <sup>192n</sup>Ir, and <sup>239</sup>Pu.

Finally, this example shows that only one-group scalar flux is given, as there is only one interval, and when IUNC=1, it must appears the total scalar flux by spatial interval.