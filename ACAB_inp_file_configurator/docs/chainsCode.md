# VII. Pathways analysis. CHAINS Code

## CHAINS Description

The purpose of the CHAINS code is to generate and output the possible pathways for the formation of a particular nuclide. All possible pathways that require up to a specified number of steps are ranked according to their estimated importance to the total production of the nuclide. The user gives an importance cutoff that is used to truncate the list of possible pathways.

CHAINS has been modified to include in the pathway analysis all the nuclear processes implemented in the present version of ACAB (in particular, generation of fission products).

CHAINS can be executed in three different modes. In the first mode (IFLAG = 1), the code calculates all transmutation sequences that results in the formation of a particular radionuclide (variable IFINAL) with a maximum number of steps (variable NMAX) in the chain. No initial nuclide is specified when operating in this mode. In addition to giving the actual chains, the code outputs the coefficients (transmutation rates or probability per nucleus per unit time) of neutron reaction or radioactive decay corresponding to each step of the chain. The CHAINS output is given in order of increasing number of steps of each chain. That is, all two-step chains are given before three-step chains are listed.

In the second mode of operation (IFLAG=2), CHAINS calculates all pathways starting from a specified parent nuclide (INITIAL) that result in a specified daughter nuclide (IFINAL) and take no more than NMAX steps. CHAINS also estimates the relative importance of each pathway. This is accomplished through the use of a "pseudo probability" for each pathway. The pseudo probabilities are summed over all pathways that are possible in NMAX or less steps. This sum is the total pseudo probability. Each pseudo probability may be divided by the total pseudo probability to get an estimate of the relative importance of each pathway.

This relative importance may not be an actual ranking of the relative contributions from each pathway, but they are useful for distinguishing those pathways that may be important from those that may be negligible.

As output for the second mode of operation, CHAINS writes the pathways in order of decreasing relative importance. The user specifies a cutoff value with the PCNT variable. Pathways that contribute less than PCNT percent to the total pseudo probability are omitted. The coefficients associated with each step in a pathway are also given.

The following example illustrates the concept of pseudo probability rankings described above. Assuming that there are two possible pathways for the production of nuclide F from nuclide I, the pathways might be written as:

$$
\begin{aligned}
(1) \quad & \text{I} \xrightarrow{a_{\text{AI}}} \text{A} \xrightarrow{a_{\text{BA}}} \text{B} \xrightarrow{a_{\text{CB}}} \text{C} \xrightarrow{a_{\text{FC}}} \text{F} \\
(2) \quad & \text{I} \xrightarrow{a_{\text{DI}}} \text{D} \xrightarrow{a_{\text{ED}}} \text{E} \xrightarrow{a_{\text{FE}}} \text{F}
\end{aligned}
$$

where:

$$
a_i = \lambda_i + \sum_{j} \sigma_{i \to j}
$$

and:

$a_i$ are the coefficients of the transition matrix that give the reaction ($\sigma\phi$) or decay ($\lambda$) probability per nucleus per unit time,

$\sigma$  is the energy-averaged reaction cross section,

$\phi$ is the energy-averaged neutron flux,

$\lambda$ is the radioactive decay constant, and

The pseudo probabilities can be written as:

$$
\begin{aligned}
P_1 &= \frac{a_{\text{AI}}}{a_{\text{I}}} \times \frac{a_{\text{BA}}}{a_{\text{A}}} \times \frac{a_{\text{CB}}}{a_{\text{B}}} \times \frac{a_{\text{FC}}}{a_{\text{C}}} \\

P_2 &= \frac{a_{\text{DI}}}{a_{\text{I}}} \times \frac{a_{\text{ED}}}{a_{\text{D}}} \times \frac{a_{\text{FE}}}{a_{\text{E}}}
\end{aligned}
$$

The total and relative pseudo probabilities can be written as:

$$
\begin{aligned}
P_{\text{tot}} &= P_1 + P_2 \\
P_{\text{R } 1} &= \frac{P_1}{P_{\text{tot}}} \\
P_{\text{R } 2} &= \frac{P_2}{P_{\text{tot}}}
\end{aligned}
$$

The relative importances would be written into the CHAINS output file in order of decreasing importance. If either of the relative importances is less than the value of PCNT, it would be omitted from the output.

In the third mode of operation (IFLAG=3), CHAINS searches for all cyclic pathways or "loops" that include a user-specified final nuclide IFINAL. All pathways are included that are possible within NMAX steps. As in the first mode of operation, the pathways are listed in order of increasing number of steps and the transmutation rates are given for each step within a pathway.

<u>**CHAINS Support Files**</u>

In addition to a standard input file, CHAINS requires two ACAB-produced files for its operation. UNIT 22 is a binary file that contains the identifiers of the nuclides found in the decay library and the elements of the transition matrix. Each element of the transition matrix contains the identifier corresponding to the neutron reaction or decay process occurring within that element. UNIT 22 is generated by running ACAB with IWP = 1.

UNIT 24 is a binary file that contains the transition matrix transformation rates. It also contains the diagonal elements that give the total depletion rates. UNIT 24 is generated by running ACAB with IMTX = 1 or 2.

UNIT 23 is a temporary binary file that is created during a CHAINS run. This file contains all possible pathways that are later ordering according to their relative pseudo probabilities. This file may become quite large but may be deleted after CHAINS execution.

<u>**CHAINS Input/Output**</u>

A CHAINS input file consists of five cards. Some card may be omitted for certain types of operation. The structure of the CHAINS input file is now described.

|Card|Variable|Format|Description|
|----|--------|------|-----------|
|1|IFLAG|І3|Indicates mode CHAINS operation mode:<br>1. Pathways to produce nuclide IFINAL.<br>2. Pathways to produce nuclide IFINAL from nuclide INITIAL.<br>3. Cyclic pathways to produce nuclide IFINAL.|
|2|INITIAL|I6|Identifier for the first initial nuclide.<br>• The nuclide identifier is defined in the same manner as NUCLID in ACAB (10000 × Z + 10 x A+ IS). INITIAL is omitted if IFLAG≠2. |
|3|IFINAL|I6|Identifier for the final nuclide. The identifier is defined in the same manner as INITIAL.|
|4|NMAX|ІЗ|Maximum number of steps considered for possible pathways. {NMAX ≤ 10}.|
|5|PCNTF|6.2|Output option: only pathways with relative pseudo probabilities greater than or equal to PCNT will be printed.<br>• PCNT is omitted if IFLAG≠2. {0≤PCNT ≤ 100}.|

Some example input and output are now given. First, a sample input file for the first mode of operation.

Example #1:

```text
1       IFLAG
110240  IFINAL Na-24
2       NMAX
```

In this example, all pathways that result in the production of 24Na that require two or less steps will be given. A portion of the output from this problem is given below:

```text
NUMBER OF ENCOUNTERED CHAINS, NCHAIN= 69
**********************************************************************
                CHAINS WITH 2 LINKS
**********************************************************************
MG 27 (B-) AL 27 (n,a) NA 24
MG 27 (B-) AL 27 DELTA=1.2214E-03
AL 27 (n,a) NA 24 XSEC=1.6121E-13
**********************************************************************
SI 27 (B+) AL 27 (n,a) NA 24
SI 27 (B+) AL 27 DELTA=1.6503E-01
AL 27 (n,a) NA 24 XSEC=1.6121E-13
**********************************************************************
AL 26 (n,g) AL 27 (n,a) NA 24
AL 26 (n,g) AL 27 XSEC=2.7887E-13
AL 27 (n,a) NA 24 XSEC=1.6121E-13
**********************************************************************
...
**********************************************************************
MG 26 (n,H) NE 24 (B-) NA 24
MG 26 (n,H) NE 24 XSEC=0.0000E+00
NE 24 (B-) NA 24 DELTA=3.4179E-03
**********************************************************************
MG 28 (n,na) NE 24 (B-) NA 24
MG 28 (n,na) NE 24 XSEC=5.0353E-16
NE 24 (B-) NA 24 DELTA=3.4179E-03
            ******JOB FINISHED******
```

Each pathway is listed along with the reaction ($\sigma\phi$) or decay ($\lambda$) probabilities per nucleus per unit time.

The second example demonstrates the operation of CHAINS in mode #2.

Example #2:

```text
2 IFLAG
130270 INITIAL Al-27
110240 IFINAL Na-24
4 NMAX
0.1 PCNT
```

This input file will cause CHAINS to output all possible pathways for the production 24Na from 27 Al that require up to 4 steps and contribute at least 0.1% to the total pseudo probability. An excerpt of the output from this problem is given below:

```text
NUMBER OF ENCOUNTERED CHAINS NCHAIN= 194
NUMBER OF CHAINS WITH RELATIVE PROBABILITY HIGHER THAN PCNT, NCH= 13
TOTAL PROB.= 20.2428
**********************************************************************
P= 55.34
AL 27 (n,a) NA 24
AL 27 (n,a) NA 24 XSEC=1.6121E-13
**********************************************************************
P= 24.74
AL 27 (n,a-m) NA 24M(IT) NA 24
AL 27 (n,a-m) NA 24M XSEC=7.2424E-14
NA 24M(IT) NA 24 DELTA=3.4143E+01
**********************************************************************
P= 5.11
AL 27 (n,np) MG 26 (n,a) NE 23 (B-) NA 23 (n,g) NA 24
AL 27 (n,np) MG 26 XSEC=5.2098E-13
MG 26 (n,a) NE 23 XSEC=1.5283E-13
NE 23 (B-) NA 23 DELTA=1.8633E-02
NA 23 (n,g) NA 24 XSEC=2.4667E-13
**********************************************************************
P= 3.96
AL 27 (n,na) NA 23 (n,g-m) NA 24M(IT) NA 24
AL 27 (n,na) NA 23 XSEC=2.8631E-14
NA 23 (n,g-m) NA 24M XSEC=7.3444E-13
NA 24M(IT) NA 24 DELTA=3.4143E+01
**********************************************************************
...
**********************************************************************
P= 0.22
AL 27 (n,2n) AL 26 (n,a) NA 23 (n,g-m) NA 24M(IT) NA 24
AL 27 (n,2n) AL 26 XSEC=1.7618E-14
AL 26 (n,a) NA 23 XSEC=2.3787E-13
NA 23 (n,g-m) NA 24M XSEC=7.3444E-13
NA 24M(IT) NA 24 DELTA=3.4143E+01
**********************************************************************
P= 0.19
AL 27 (n,D) MG 26 (n,2n) MG 25 (n,2n) MG 24 (n,p) NA 24
AL 27 (n,D) MG 26 XSEC=3.0214E-14
MG 26 (n,2n) MG 25 XSEC=4.1518E-13
MG 25 (n,2n) MG 24 XSEC=1.1279E-13
MG 24 (n,p) NA 24 XSEC=2.5837E-13
        ******JOB FINISHED******
```

Note that the first line of output indicates that a total of 194 pathways that result in the production of $^{24}Na$ from $^{27}Al$ within 4 steps were identified. The second line of output indicates, however, that only 13 of these possible pathways make a contribution of at least 0.1% to the total pseudo probability. Several of these pathways are listed in the output above. For each pathway, the total percentage contribution to the total pseudo probability is given. This is followed by a listing of the pathway and the reaction or decay probabilities per nucleus per unit time for each step in the pathway.

The next example, that also addresses the operation of CHAINS in mode number #2, is intended to show how the present version of CHAINS includes the fission channel in the pathway analysis.

Example #3:

```text
2 IFLAG
922380 INITIAL U-238
551370 IFINAL CS-137
4 NMAX
0.1 PCNT
```

This input file will cause CHAINS to output all possible pathways for the production Cs-137 from U-238 that require up to 4 steps and contribute at least 0.1% to the total pseudo probability.

The complete output from this problem is given below:

```text
NUMBER OF ENCOUNTERED CHAINS NCHAIN =2327
NUMBER OF CHAINS WITH RELATIVE PROBABILITY HIGHER THAN PCNT, NCH= 4
PTOT= 2.0273
**********************************************************************
P= 97.81
U238 (n,g) U239 (B-) NP239 (B-) PU239 (N,F) CS137
U238 (n,g) U239 XSEC=5.4317E-09
U239 (B-) NP239 DELTA=4.9229E-04
NP239 (B-) PU239 DELTA=3.4061E-06
PU239 (N,F) CS137 XSEC=2.6494E-10
**********************************************************************
P= 1.11
U238 (N,F) XE137 (B-) CS137
U238 (N,F) XE137 XSEC=1.2398E-12
XE137 (B-) CS137 DELTA=3.0255E-03
**********************************************************************
P= .64
U238 (N,F) I136M(B-) XE136 (n,g) XE137 (B-) CS137
U238 (N,F) I136M XSEC=2.7891E-12
I136M(B-) XE136 DELTA=1.5403E-02
XE136 (n,g) XE137 XSEC=7.4160E-12
XE137 (B-) CS137 DELTA=3.0255E-03
**********************************************************************
P= .30
U238 (N,F) I136 (B-) XE136 (n,g) XE137 (B-) CS137
U238 (N,F) I136 XSEC=1.3291E-12
I136 (B-) XE136 DELTA=8.2518E-03
XE136 (n,g) XE137 XSEC=7.4160E-12
XE137 (B-) CS137 DELTA=3.0255E-03
        ******JOB FINISHED******
```

The final example demonstrates the operation of CHAINS in mode #3.

Example #4:

```text
3 IFLAG
110240 INITIAL Na-24
4 NMAX
```

This example causes CHAINS to output all possible pathways for the production of 24Na from an original 24Na atom. All pathways that require up to 4 steps are given. These are called cyclical pathways. An excerpt of the output is given below:

```text
NUMBER OF ENCOUNTERED CHAINS NCHAIN= 42
******CYCLIC CHAINS******
**********************************************************************
CHAINS WITH 2 LINKS
**********************************************************************
NA 24 (B-) MG 24 (n,p) NA 24
NA 24 (B-) MG 24 DELTA=1.2853E-05
MG 24 (n,p) NA 24 XSEC=2.5837E-13
**********************************************************************
NA 24 (n,2n) NA 23 (n,g) NA 24
NA 24 (n,2n) NA 23 XSEC=8.1295E-13
NA 23 (n,g) NA 24 XSEC=2.4667E-13
**********************************************************************
NA 24 (n,n`) NA 24M(IT) NA 24
NA 24 (n,n`) NA 24M XSEC=3.5792E-13
NA 24M(IT) NA 24 DELTA=3.4143E+01
**********************************************************************
NA 24 (n,p) NE 24 (B-) NA 24
NA 24 (n,p) NE 24 XSEC=6.1945E-14
NE 24 (B-) NA 24 DELTA=3.4179E-03
**********************************************************************
CHAINS WITH 3 LINKS
**********************************************************************
NA 24 (B-) MG 24 (n,g) MG 25 (n,D) NA 24
NA 24 (B-) MG 24 DELTA=1.2853E-05
MG 24 (n,g) MG 25 XSEC=9.8661E-14
MG 25 (n,D) NA 24 XSEC=1.3629E-14
**********************************************************************
NA 24 (n,g) NA 25 (B-) MG 25 (n,D) NA 24
NA 24 (n,g) NA 25 XSEC=5.9161E-14
NA 25 (B-) MG 25 DELTA=1.1630E-02
MG 25 (n,D) NA 24 XSEC=1.3629E-14
**********************************************************************
...
**********************************************************************
CHAINS WITH 4 LINKS
**********************************************************************
NA 24 (B-) MG 24 (n,g) MG 25 (n,g) MG 26 (n,T) NA 24
NA 24 (B-) MG 24 DELTA=1.2853E-05
MG 24 (n,g) MG 25 XSEC=9.8661E-14
MG 25 (n,g) MG 26 XSEC=3.5518E-13
MG 26 (n,T) NA 24 XSEC=0.0000E+00
**********************************************************************
NA 24 (n,g) NA 25 (B-) MG 25 (n,g) MG 26 (n,T) NA 24
NA 24 (n,g) NA 25 XSEC=5.9161E-14
NA 25 (B-) MG 25 DELTA=1.1630E-02
MG 25 (n,g) MG 26 XSEC=3.5518E-13
MG 26 (n,T) NA 24 XSEC=0.0000E+00
**********************************************************************
NA 24 (n,n`) NA 24M(B-) MG 24 (n,g) MG 25 (n,D) NA 24
NA 24 (n,n`) NA 24M XSEC=3.5792E-13
NA 24M(B-) MG 24 DELTA=1.7157E-01
MG 24 (n,g) MG 25 XSEC=9.8661E-14
MG 25 (n,D) NA 24 XSEC=1.3629E-14
**********************************************************************
```

The first line of output indicates that a total of 42 pathways were identified. Note, however, that the first two pathways with 4 steps both end with the 26Mg (n,t) 24Na reaction. This reaction has an energy-averaged cross section of 0 barns (the threshold is 14.7 MeV but the flux is 0 above 14.1 MeV). When operated in mode #3, CHAINS makes no attempt to extract possible pathways that will not contribute to the overall production.

In Section VI, Example #15 is devoted to assess the transmutation of Fe in IFMIF. The possible pathways for the formation of particular nuclides of interest have been addressed with the CHAINS code. The ACAB inputs needed to compute the two required files for CHAINS code (UNIT 22 and UNIT 24) have been presented in such example. The corresponding input file to CHAINS has also been included in such Example #15.

**CHAINS Availability**
The CHAINS utility currently operates on Unix workstations and PC platforms under Windows and Linux. As ACAB, CHAINS is written in standard FORTRAN 77. Thus, porting of CHAINS onto other machines should not be difficult.
