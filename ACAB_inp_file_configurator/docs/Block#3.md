# C. Block #3

Block #3 consists of only one card (in real free-format) which inputs the energy- and spatially-dependent fluxes. Block #3 is needed only if IFLU = 1. When IUNC=1, for each spatial interval a single value corresponding to the total energy-integrated neutron flux must be given.

## Card #1

|#|Parameter|Description|
|-|---------|-----------|
|1|FLUX|Multigroup scalar fluxes of neutrons (or protons) and gammas (n/cm<sup>2</sup>–s).<br>[(NGRP + IGRP) × IM] for JM = 0, or<br>[(NGRP + IGRP) × IM × JM] for JM > 0.|

i.e. JM = 0,
```plaintext
** neutrons **
1st group - spatial intervals from 1 to IM.
2nd group - spatial intervals from 1 to IM.
...
...
...
NGRP group - spatial intervals from 1 to IM.
** gammas **
NGRP + 1 group - spatial intervals from 1 to IM.
...
...
...
NGRP + IGRP - spatial intervals from 1 to IM.
```

**Example**

```plaintext
<FLUX array
0.00000E+00 0.00000E+00 0.00000E+00 0.00000E+00 0.00000E+00 0.00000E+00
0.00000E+00 0.00000E+00 0.00000E+00 0.00000E+00 2.24560E+12 1.28748E+09
9.36590E+09 1.09117E+11 5.71239E+10 2.29345E+10 2.24553E+10 2.21273E+10
2.07259E+10 2.42329E+10 1.93205E+10 2.33644E+10 3.29684E+10 3.10372E+10
2.67600E+10 2.73849E+10 2.78341E+10 3.11134E+10 2.99179E+10 4.24145E+10
4.27637E+10 5.38507E+10 4.97128E+10 5.60370E+10 6.80981E+10 5.99109E+10
7.02953E+10 8.36346E+10 9.05295E+10 1.14939E+11 1.06675E+11 1.57469E+11
1.41095E+11 1.46795E+11 1.70587E+11 1.77039E+11 1.96036E+11 2.06424E+11
2.20851E+11 2.64793E+11 2.26939E+11 3.27008E+11 3.53680E+11 2.67274E+11
1.86971E+11 1.85623E+11 1.61273E+11 1.04622E+11 2.06572E+11 1.62587E+11
1.40515E+11 2.66758E+11 3.28667E+11 5.34534E+10 1.36869E+11 2.55764E+11
1.80476E+11 8.37936E+10 2.71935E+10 1.90595E+11 2.07160E+11 1.67033E+11
1.51164E+11 1.10752E+11 8.90825E+10 1.05012E+11 3.98039E+10 3.85728E+10
3.90367E+10 3.37028E+10 3.35326E+10 5.06135E+10 6.28872E+10 6.67807E+10
6.35506E+10 4.52059E+10 3.19280E+10 4.79158E+10 3.39836E+10 1.50696E+10
1.88315E+10 3.65922E+10 1.72076E+10 5.67439E+10 2.29198E+10 4.53192E+10
8.10556E+10 1.58072E+10 1.52956E+10 1.53275E+10 1.60421E+10 1.56105E+10
1.49453E+10 1.95372E+10 1.23915E+10 1.68609E+10 1.69424E+10 1.87165E+10
1.77789E+10 1.13412E+10 3.76854E+09 8.06483E+09 7.66558E+09 7.87956E+09
1.42777E+10 9.44282E+09 8.04090E+09 4.57391E+09 8.45258E+09 1.32726E+10
4.45566E+09 1.27853E+10 4.53097E+09 8.68020E+09 9.08462E+09 1.53207E+10
5.39231E+09 1.53635E+10 1.13034E+10 9.46579E+09 1.11856E+10 5.90132E+09
1.59676E+10 5.75868E+09 1.03850E+10 1.12432E+10 1.70752E+10 1.86777E+10
1.80729E+10 1.41357E+10 6.93439E+09 1.64552E+10 1.38189E+10 1.68749E+10
1.51662E+10 2.35880E+10 2.36985E+10 1.64662E+10 2.58199E+10 1.63296E+10
2.85504E+10 4.01943E+10 3.27129E+10 3.57419E+10 4.94656E+10 3.82529E+10
4.33785E+10 6.86971E+10 5.28651E+10 5.69083E+10 6.72074E+10 5.57159E+10
8.78042E+10 7.18004E+10 3.50706E+10 4.01719E+10 4.58855E+10 4.78985E+10
5.17701E+10 5.87309E+10 6.69443E+10 3.50314E+10 9.78391E+11 0.00000E+00
0.00000E+00 T
```

This example gives the 175-group energy-dependent neutron fluxes for a single zone as calculated from a 14.1 MeV point source without inclusion of gammas. Note that 14.1 MeV lies within group #11, and thus, the first 10 energy groups have fluxes of zero. Special attention must be paid to the fact that the fluxes for the highest energy group must be given for each zone or interval before the 2<sup>nd</sup> group begins.

It is worth noting that in a general case, the energy dependent fluxes should be given consistently with the cross section activation library. If cross sections are given as a function of decreasing/increasing energy, the neutron spectrum must be given following the same structure, that is, as a function of decreasing/increasing energy.
