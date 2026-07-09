# G. Block #7 and #8

Blocks #7 and #8 are used to specify the irradiation and post-irradiation temporal history. Here, the user selects the timesteps that will be used to reach the desired irradiation time and the specific post-irradiation (cooling) times at which the full output is generated. ACAB starts its internal clock at zero when the calculation begins. Whenever an irradiation period ends, the clock is reset to zero. Whenever an irradiation period begins, however, the clock is not reset. It continues from the previous cooling period (or zero if the calculation has just begun).

Due to the nature of the computational solution (the matrix exponential method), it is recommended that the irradiation times ramp up by factors of two and the cooling times ramp up by factors of three (see example).

A “set” is defined as a grouping of two blocks: block #7 and block #8. The block #7 gives ACAB information about the number of irradiation and/or cooling timesteps, and the block #8 provides the actual timesteps. Up to 10 timesteps may be specified within a set. For more than 10 timesteps, multiple sets are required. Each set may consist entirely of irradiation, entirely of cooling, or of irradiation followed by cooling. Since the clock is initially set to zero, only the ending times of the timesteps must be provided.

Sets may be grouped into a “unit” that gets repeated a specified number of times and may be followed by additional sets. The use of units makes the definition of complex irradiation/cooling histories easier. A complete explanation of the use of units is given in block #11, card #3. Here (for purpose of better explanation of blocks #7 and #8) only mention that the first parameter of this card, NOPUL, defines if the unit capability is used. It is not used when NOPUL is zero.

## Block #7

It consists of only one card, with 8 integer parameters in free-format.

### Card #1

|#|Parameter|Description|
|-|---------|-----------|
|1|MMN|Number of irradiation timesteps on this card. [≤ 10].|
|2|MOUT|Number of total timesteps ( irradiation + cooling) on this card.[≤ 10].|
|3|NGO|Computation flow control:<br>- **0** No additional sets provided. That is, this is the final set.<br>- **1** Additional sets provided. That is, the present calculation will be continued.|
|4|MSUB|Timestep in last set considered as starting point of new set:<br>• No effect if there is no prior set, or sets are not grouped into a unit (that is, if parameter NOPUL of block #11 is equal to zero).<br>• Usually, MSUB is selected to point to the last timestep in the previous set. In the case of NOPUL not set to zero, MSUB for the first set of the unit must point to the last timestep on the last set of the unit (see block #11, card #3).
|5|IUNIT|Physical unit of the timesteps:<br>&nbsp;&nbsp;&nbsp;1 Seconds<br>&nbsp;&nbsp;&nbsp;2 Minutes<br>&nbsp;&nbsp;&nbsp;3 Hours<br>&nbsp;&nbsp;&nbsp;4 Days<br>&nbsp;&nbsp;&nbsp;5 Years<br>&nbsp;&nbsp;&nbsp;6 Here it is not considered.<br>&nbsp;&nbsp;&nbsp;7 10<sup>3</sup> years<br>&nbsp;&nbsp;&nbsp;8 10<sup>6</sup> years<br>&nbsp;&nbsp;&nbsp;9 10<sup>9</sup> years|
|6|MFEED|Continuous feed option:<br>&nbsp;&nbsp;&nbsp;0 No effect.<br>&nbsp;&nbsp;&nbsp;1 Continuous feed used in current set.|
|7|IOUT|Output option (no effect if IUNC=1):
0
No effect.
1
Print output tables by spatial interval.|
|8|IPLOT|Preparation of data for plotting -generation of unit 11 (no effect
if IUNC=1):<br>&nbsp;&nbsp;&nbsp;0 No effect - unit 11 is not generated.<br>&nbsp;&nbsp;&nbsp;1 Output tables by interval.<br>&nbsp;&nbsp;&nbsp;2 Output tables by zone.|

## Block #8

It consists of one card which contains up to 10 real free-format values.

### Card #1
|#|Parameter|Description|
|-|---------|-----------|
|1|TIMES|Ending times of each timestep. Note that the clock is set to zero when the calculation begins and is reset to zero whenever an irradiation period ends (shutdown). [MOUT].|

Blocks #7 and #8 must be repeated for all time sets of interest.|

**Example**

```plaintext
<Block 7
10 10 1 0   1   0   0   0
<Block 8
1.0000E+0 2.0000E+0 4.0000E+0 8.0000E+0 1.6000E+1
3.2000E+1 6.4000E+1 1.2800E+2 2.5600E+2 5.1200E+2
<Block 7
10 10 1 10  1   0   0   0
<Block 8
1.0240E+3 2.0480E+3 4.0960E+3 8.1920E+3 1.6384E+4
3.2768E+4 6.5536E+4 1.3107E+5 2.6214E+5 5.2429E+5
<Block 7
10 10 1 10  1   0   0   0
<Block 8
1.0486E+6 2.0972E+6 4.1943E+6 8.3886E+6 1.6777E+7
3.3554E+7 6.7109E+7 1.3422E+8 2.6844E+8 5.3687E+8
<Block 7
3  3  1 10  1   0   0   0
<Block 8
7.0000E+8 8.2500E+8 9.4608E+8
<Block 7
0 10  1 3   1   0   0   0
<Block 8
1.0000E+0 3.0000E+0 1.0000E+1 3.0000E+1 1.0000E+2
3.0000E+2 1.0000E+3 3.0000E+3 1.0000E+4 3.0000E+4
<Block 7
0 10  1 10  1   0   0   0
<Block 8
1.0000E+5 3.0000E+5 1.0000E+6 3.0000E+6 1.0000E+7
3.0000E+7 3.1536E+7 6.3072E+7 1.5768E+8 3.1536E+8
<Block 7
0 6   0 10  1   0   0   0
<Block 8
6.3072E+8 1.5768E+9 3.1536E+9 6.3072E+9 1.5768E+10
3.1536E+10
```

In this example, the irradiation lasts for a total of 9.4608 × 10<sup>8</sup> seconds (30 years). The irradiation timesteps ramp up by factors of 2 from 1 second to 30 years.
The last irradiation time occurs on the 4<sup>th</sup> set. The cooling times begin on the 5<sup>th</sup> set and increase in most cases by factors of 3. Occasionally, the ratio between two cooling times is less than 3, because a  specific cooling time is desired. For example, the 6<sup>th</sup> set has successive cooling times of 3.0 × 10<sup>7</sup> seconds and 3.1536 × 10<sup>7</sup> seconds. The latter time was selected as it corresponds to 1 year of cooling.

In this example, the irradiation and cooling times were kept on separate cards in order to make them easier to understand. This is not required. The first 7 cooling times from the 5<sup>th</sup> set could have been placed on the end of the 4<sup>th</sup> set. This results in the 4<sup>th</sup> set looking like this:

```plaintext
<Block 7
3 10 1 10  1   0   0   0
<Block 8
7.0000E+8 8.2500E+8 9.4608E+8 1.0000E+0 3.0000E+0
1.0000E+1 3.0000E+1 1.0000E+2 3.0000E+2 1.0000E+3
```

Note that the cooling times are still given relative to the end of the irradia-tion period, because the clock is reset to zero when the irradiation period ends.
