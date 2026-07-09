# B. Block #2

The second input block may consist of eight cards: card #1 (XRR array, real free-format), card #2 (YZT array, real free-format), card #3 (MA array, integer free-format), card #4 (NUCZO array, integer free-format), card #5 (ISOZO array, integer free-format), card #6 (EGRP array, real free-format), card #7 (CUTOFF array, real free-format), and card #8 (NTO array, integer free-format).

This block contains detailed information about the current calculation. The user can elect to receive zonal results by solving the transmutation equations by interval or by using a spatially-averaged flux for the entire zone. The spatially-averaged flux, φ<sub>g</sub>, for a zone κ is defined by the following equation:

$$\sum_{l \in \kappa} \frac{\phi_{g, l} \Delta V_l}{V_\kappa}$$
where:
${\phi_{g, l}}$ is the scalar neutron flux in energy group g and interval l in zone κ,
${\Delta V_l}$ is the volume of interval l in zone κ, and
${V_\kappa}$ is the volume of zone κ.

|Card #:|Parameter|Description|
|-------|---------|-----------|
|1|XRR|Boundaries for 1<sup>st</sup> dimension intervals in cm. For 3-D (IGE = 4) configurations, this card gives the volume of each zone in cm<sup>3</sup> and must end with an additional nonzero value. [IM + 1].|
|2|YZT|Boundaries for 2<sup>nd</sup> dimension intervals in cm. This card is omitted when 1-D or 3-D geometry is chosen by the IGE parameter. [JM + 1] {JM > 0}.|
|3|MA|Zone number identification of each spatial interval, going from left to right and bottom to top. [IM] or [IM × JM].|
|4|NUCZO|Number of initial elements or isotopes per zone. Negative values are used when zone averaged fluxes are used. A zero (0) must be included to omit a zone. [IZM].
5|ISOZO|Number of elements or isotopes per zone for continuous feed.<br>[IZM] {INDF > 0}.|
|6|EGRP|Energy boundaries for gammas produced by activation.<br>These boundaries are given in order of decreasing energy in MeV. [NOGG + 1] {NOGG > 0}.|
|7|CUTOFF|Threshold values for different output tables. Any isotopes whose value in the timestep MSTAR falls below CUTOFF will be omitted from the corresponding output table. One threshold value must be given for each of the six types of tables. These six types of output tables are described in Table V.1 [6].<br>*Note 1*: If no cutoff, components of this array must set to zero.<br>*Note 2*: In the first ACAB versions, 6 types of tables were used.In the current version, only the first 4 are active. The output for most of the response funtions are now controlled by block #11.|
|8|NTO|Allows selection of desired output tables. The 18 values correspond to the 18 tables (three of each type) described in Table V.1. [18] {JTO = 1}.<br> - **0** No effect.<br>- **1** Print output table.<br>Note: the last 6 values must be set to zero as they are not active.|

**Example #1:**

```plaintext
<XRR array
1.3684E+5 1.0
<MA array
1
<NUCZO array
3
<EGRP array
11.0 8.0 6.0   4.0 3.0 2.5   2.0 1.5 1.0   0.7 0.45 0.3
0.15 0.1 0.07   0.045 0.03 0.02   0.0
<CUTOFF array
1.0E+0 1.0E-6 1.0E+0 1.0E-3 1.0E+0 1.0E+0
<NTO array
0 0 0   0 0 1   0 0 1   0 0 0   0 0 0   0 0 0
```

This example is for a 3-D geometry description. Only a single zone is included with a volume of 1.3684E+5 cc (a nonzero value ends the 1st card). The zone is numbered as zone #1 and three initial elements will be given. A total of 19 energies are given creating an 18-group structure for gamma-rays produced by activation.
Only 2 of the 18 tables have been requested (table #4 is grams of the most important isotopes and table #7 is activity in Bq of the most important isotopes).
Cutoff values have been specified for each of the table types.

**Example #2:**

```plaintext
<MA array
111  2222  33
<NUCZO array
3      3       6
```

This example is for a case with three zones. There are three intervals in the first zone, four intervals in the second zone, and two intervals in the third zone. The transmutation equations will be solved by intervals for all three zones, because all values of NUCZO are positive. The number of nuclides or elements in each zone is 3, 3, and 6, respectively.

**Example #3:**

```plaintext
<MA array
111  2222  33
<NUCZO array
3      0      -6
```
Again, three zones are included in this example. This time, the transmutation equations are solved by interval in the first zone, the second zone is ignored, and results for the third zone are calculated using a zone-averaged flux. The first zone contains three nuclides or elements and the third zone contains six.
**Table V.1. Type of tables that are output by ACAB**

<table>
  <thead>
    <tr>
      <th>Output Table #</th>
      <th>Table Type</th>
      <th>Output Quantity</th>
      <th>Output Scope</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td align="center">1</td>
      <td rowspan="3" align="center">1</td>
      <td rowspan="3">gram-atoms (moles)</td>
      <td>all isotopes</td>
    </tr>
    <tr>
      <td align="center">2</td>
      <td>all elements</td>
    </tr>
    <tr>
      <td align="center">3</td>
      <td>most important isotopes</td>
    </tr>
    <tr>
      <td align="center">4</td>
      <td rowspan="3" align="center">2</td>
      <td rowspan="3">mass (grams)</td>
      <td>all isotopes</td>
    </tr>
    <tr>
      <td align="center">5</td>
      <td>all elements</td>
    </tr>
    <tr>
      <td align="center">6</td>
      <td>most important isotopes</td>
    </tr>
    <tr>
      <td align="center">7</td>
      <td rowspan="3" align="center">3</td>
      <td rowspan="3">activity (Bq)</td>
      <td>all isotopes</td>
    </tr>
    <tr>
      <td align="center">8</td>
      <td>all elements</td>
    </tr>
    <tr>
      <td align="center">9</td>
      <td>most important isotopes</td>
    </tr>
     <tr>
      <td align="center">10</td>
      <td rowspan="3" align="center">4</td>
      <td rowspan="3">afterheat (W)</td>
      <td>all isotopes</td>
    </tr>
    <tr>
      <td align="center">11</td>
      <td>all elements</td>
    </tr>
    <tr>
      <td align="center">12</td>
      <td>most important isotopes</td>
    </tr>
     <tr>
      <td align="center">13</td>
      <td rowspan="3" align="center">5</td>
      <td rowspan="3">No effect</td>
      <td>all isotopes</td>
    </tr>
    <tr>
      <td align="center">14</td>
      <td>all elements</td>
    </tr>
    <tr>
      <td align="center">15</td>
      <td>most important isotopes</td>
    </tr>
     <tr>
      <td align="center">16</td>
      <td rowspan="3" align="center">6</td>
      <td rowspan="3">No effect</td>
      <td>all isotopes</td>
    </tr>
    <tr>
      <td align="center">17</td>
      <td>all elements</td>
    </tr>
    <tr>
      <td align="center">18</td>
      <td>most important isotopes</td>
    </tr>
  </tbody>
</table>

**Note**: The 12 ACAB output tables that are active in ACAB (see Table V.1) can be categorized into four types according to the quantity that is indicated (grams-atoms, mass, activity, afterheat). Each of the four types may be generated for all isotopes, all elements, and most important isotopes. Tables to be generated are specified on the card #8, block #2. If most important isotopes are to be outputted, cutoffs must be specified on the card #7, block #2. In addition to these 12 responses ACAB can provide other activity-related quantities, such as waste disposal ratings, contact dose rates, decay heat from different types of radiation, offsite doses and consequences (see block #11).