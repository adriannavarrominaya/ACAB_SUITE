# K. Block #12

The fifteen cards are read by ACAB as free format. This block tells ACAB first whether instantaneous feed of material is used. If this capability is active, a group of cards tell the code about the number of materials fed, composition of each material, where the composition of each material is read from, and if that is provided for the constituent elements or isotopes of each material. The last group of cards tells about the feed time schedule, that is, feed times for the different materials.

## Card #1

|#|Parameter|Description|
|-|---------|-----------|
|1|IIFD|Input option: material is fed instantaneously into the system.<br>- **0** No effect<br>- **1** No more than one feed is allowed in any temporal set (cards of block #7 and block #8).<br>- **2** There can be more than one feed per set.|

The **rest of the cards of the block** must be omitted if IIFD = 0. Thus, the condition for input of next cards is {IIFD ≠ 0}.

## Card #2

|#|Parameter|Description|
|-|---------|-----------|
|1|NMAIFD|Number of different materials that are fed into the system. The maximum number of materials that can be specified is 5.|

## Card #3

|#|Parameter|Description|
|-|---------|-----------|
|1|IRMAIFD|Indicator to specify where the compositions of the different fed materials are read from. [NMAIFD]<br>**1** Read composition data for elements from the standard input (UNIT 5)<br>**2** Read composition data for isotopes from the standard input (UNIT 5)<br>**3** Read composition data for isotopes from a binary tape (UNIT 81) output from a previous ACAB run.<br>**Note # 1:** First components of the array IRMAIFD must make reference (if needed) to the standard input, and the last  components (if neded) to UNIT 81.<br>**Note # 2**: The number of the IRMAIFD array components with value = 1, should be ≤ 1. The number of the IRMAIFD array components with value = 2, should be  also ≤ 1.

Next card, **card #4**, must appear only if {any of the components of array IRMAIFD is = 3}

## Card #4

|#|Parameter|Description|
|-|---------|-----------|
|1|NISFDTP|Number of isotopes for which the quantity (in gram-atoms) is given in UNIT 81.<br>**Note:** UNIT 81 consists of some binary records  All the records has the same length, which is set by NISFDTP. The number of binary records is equal to the number of IRMAIFD components set to 3. Each record contains the composition data for one material. Each of the records is output by ACAB in previous runs (UNIT 37), and they are put together into UNIT 81 by a straightforward utility program.


The next **set** of cards, **cards #5, #6, and #7**, must appear only if {any of the
components of array IRMAIFD is = 1}

## Card #5
|#|Parameter|Description|
|-|---------|-----------|
|1|NELFD|Number of elements for which the quantity (in atoms/barn) is given in the standard input unit. {if any of the components of array IRMAIFD is = 1}.

## Card #6

|#|Parameter|Description|
|-|---------|-----------|
|1|IELIFD|Identifiers of the elements  The identifier is specified using the format defined in Block #5.|

## Card #7

|#|Parameter|Description|
|-|---------|-----------|
|1|XCOMEFD|Amount of each element in units of atoms/barn.|

The next set of cards, **cards #8, #9, and #10**, must appear only if {any of the
components of array IRMAIFD is = 1}

## Card #8

|#|Parameter|Description|
|-|---------|-----------|
|1|NISFD|Number of isotopes for which the quantity (in atoms/barn) is given in the standard input UNIT 5.|

## Card #9

|#|Parameter|Description|
|-|---------|-----------|
|1|IISIFD|Identifiers of the isotopes  Format of the identifier is that defined in Block #5.|

## Card #10

|#|Parameter|Description|
|-|---------|-----------|
|1|XCOMISFD|Amount of each isotope in units of atoms/barn.|

The next set of cards, **cards #11, and #12**, must appear only if {IIFD is = 1}.
They specifies the time feed schedule when the maximum number of feeds allowed per temporal set is 1.

## Card #11

|#|Parameter|Description|
|-|---------|-----------|
|1|ITFDSET|Array to specify temporal sets in which feed is used as well as the feed time in each set [NOTTS].<br>The feed time in each temporal set is specified by telling the code the timestep at which instantaneous feed is used. The code understands that feed occurs at the beginning time of the timestep. Thus a ith-component of ITFDSET array = 0 means no feed in the corresponding ith-set, a ith component set to 1 means instantaneous feed at the beginning of the first timestep in the ith set, and so on.

## Card #12

|#|Parameter|Description|
|-|---------|-----------|
|1|IMASET|Specify the material fed in each set [NOTTS].<br>If a component i of ITFDSET is zero, the corresponding component i of IMASET is ignored, and can take any value.<br>Here, the identifier of the material is a number from 1 to NMAIFD, corresponding to the turn in which the composition of the material is read. That is, composition read in first turn is the composition of material #1, composition read in second turn is that of material #2, and so on.|

The next set of cards, **cards #13, #14, and #15**, must appear only if {IIFD is
= 2}. They specifies the time feed schedule when the maximum number of feeds
allowed per temporal set is 9.

## Card #13

|#|Parameter|Description|
|-|---------|-----------|
|1|NFDSET|Number of instantaneous feeds in each set. [NOTTS].<br>{NFDSET ≤ MOUT - 1}|

The next two cards, **cards #14 and #15**, form a **subset** that must be provided as many times as the number of NFDSET components not set to zero.

## Card #14

|#|Parameter|Description|
|-|---------|-----------|
|1|ITSFDSET|Timesteps in set i at which instantaneous fed is used [NFDSET(i)].  **Note:** Feed times are taken at the beginning times of the timesteps.|

## Card #15

|#|Parameter|Description|
|-|---------|-----------|
|1|IMASSET|Specifies the materials fed in set i [NFDSET(i)].|

### Example #1

```plaintext
<Block 12
1             IIFD
3             NMAIFD
3 3 3         IRMAIFD
1874           NISFDTP
3 3 3 3 3 3
3 3 3 3 3 3
3 3 3 3 3 3
3 3 3 3 3 3
3 3 3 3 3 3
3 3 3 3 3 3
3 3 3 3 3 3
3 3 3 3 3 3
3 0 0 0 0 0
0 0 0 0 0 0
0 0 0 0 0 0
0
1 1 1 1 2 1 1
1 1 3 1 1 1
1 2 1 1 1 1
3 1 1 1 1 2
1 1 1 1 3 1
1 1 1 2 1 1
1 1 3 1 1 1
1 2 1 3 1 1
0 0 0 0 0 0
0 0 0 0 0 0
0 0 0 0 0 0
```

Following the parameters of block #12 we can see firstly that no more than one feed per set is allowed. Three different materials are fed into the chamber. The composition of these three materials are read from unit 81, which consequently should have three records, and each of the records contains inventory data corresponding to 1874 isotopes.

According with the number of components of the array ITDFSET, a total of 67 sets must be involved in this case. The ITDFSET array tells us that feed occurs only in the first 49 sets, and that the feed in each of these sets takes place at the beginning of timestep #3.

The IMASET array specifies which material is fed in each set. Materials 1#, #2, and #3 have the composition written in records 1#, #2, and #3 of unit 81, respectively.

More examples are described in detail in Section VI, subsection D.
