# L. Block #13

This block is addressed to control the output, and contains three cards that are read by ACAB as FORTRAN free format. It must not appear if IUNC=1.This block tells ACAB the time sets for printing of results by zone. The time sets for output by interval should be selected only from the output-by zone sets, by setting to 1 the corresponding IOUT parameter of the set (see block #7). This capability is especially appropriate for problems involving a very large number of temporal cycles. In these cases there may be a huge number of time sets [NTSEQ*(NOPUL+1) + (NOTTS-NTSEQ)], and consequently the output for all of them will be very voluminous.

## Card #1

Card #1 specifies if some output information is desired for the temporal cycles and the final series of sets used in modeling the irradiation/cooling history.

|#|Parameter|Description|
|-|---------|-----------|
|1|NCYO|Number of cycles for which some output information is desired (NCYO ≤ NOPUL+1). If NOPUL = 0, NCYO must be set to zero.|
|2|IFSO|Output option for the final series of arbitrary time sets.<br>- **0** No effect.<br>- **1** Output for some or all time sets of the final series|

## Card #2

Card #2 only appears if NCYO ≠ 0. It is used to select and specify the cycles for which output associated to some or all time sets of a cycle is desired.

|#|Parameter|Description|
|-|---------|-----------|
|1|ICYO|Integer numbers corresponding to the ordinal number of the cycles are used for cycle specification. [NCYO ].|

## Card #3
Card #3 is used to select and specify the time sets within the cycles and within the final series for which output is required.

|#|Parameter|Description|
|-|---------|-----------|
|1|ITSO|Specify the time sets for which output is required. [NOTTS]<br>- **0** No effect, i.e., no print by zone nor by interval.<br>- **1** Print the activation responses by zone. Output by interval of the zone will be performed if the parameter IOUT is also set to 1.

### Example #1

```plaintext

< First time set. The first two sets are within a unit.
    1 2 1 2   4 0   1 0  MMN MOUT NGO MSUB IUNIT MFEED IOUT IPLOT
    1. 1.5
< Second time set
    1 2 1 2   4 0   0 0                 IOUT
    2. 1.7
< Third time set. The last three sets are within the final series of sets
    1 2 1 2   4 0   0 0      .......... IOUT
    2. 1.8
< Forth time set
    1 2 1 2   4 0   0 0                 IOUT
    2. 1.9
< Fifth time set
    1 2 0 2   4 0   1 0                 IOUT
    2. 1.95

4   2   5   0       NOPUL NTSEQ NOTTS NVFL

< Block #13
  2  1                   NCYO IFSO
  2 5                   (ICYO(I), I=1,NCYO)
  1 0 1 0 1             (ITSO(I), I=1,NOTTS)
```

As NOPUL is set to 4 the number of cycles involved in the problem is 5. There are 2 time sets in each cycle, as set by NTSEQ. After the five temporal cycles, there is a series of 3 additional sets (NOTTS-NTSEQ). Some of the time sets selected for output belong to 2 temporal cycles. These are the second and filth of the 5-cycle series. Only one time set of these cycles is selected for output, this is the first time set (also refereed as set #1). Time sets #3 and 5 that does not belong to any cycle, i.e., they belong to the final series of sets, are also selected for output. Consequently activation responses will be printed by zone for a total of 4 time sets.

Of these four time sets, in only tree will be active the option of output by interval (parameter IOUT). For the time set #1 the option is active (this leads to output for two time sets, one of the cycle #2, and the other of cycle #5), and also for time set #5 (leading to output for the last time set of the final-set series).

### Example #2

```plaintext
< First time set
1 2 1 2   4 0   1 0  MMN MOUT NGO MSUB IUNIT MFEED IOUT IPLOT
    1. 1.5
< Second time set
    1 2 1 2   4 0   0 0                 IOUT
    2. 1.7
< Third time set.
    1 2 0 2   4 0   0 0      .......... IOUT
    2. 1.8

0   0   3   0        NOPUL NTSEQ NOTTS NVFL
< Block #13
0  1                          NCYO IFSO
< CARD #2 is omitted, NCYO=0
1  3                         (ITSO(I), I=1,NOTTS)
```

No cycles are involved in this case (NOPUL=0), thus NCYO is set to zero, and card #2 of the block is omitted. As IFSO is set to 1, output for some time sets of the final-set is desired. First and third sets of the series are selected for output by zone. Only the first set is selected for output by interval.
