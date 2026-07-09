# A. Block #1

The block #1 consists of three cards:

* card #1 (80 character format).
* card #2 (1 parameter in integer free-format).
* card #3 (17 integer parameters in freeformat).

## Card #1

The ACAB input file begins with a title card that gives a general description of the calculation being performed. This card may contain character information and be up to 80 characters in length.
**Example:**
Activation of alumina first wall coating on NIF - single, 20 MJ yield

## Card #2

It is used to define if the run is aimed to compute inventory and activation related responses, or to compute uncertainties in the activation calculations due to the uncertainties in the activation cross sections by means of a Monte Carlo approach. If the uncertainty mode is activated, a group of cards (within the last block of the input, block #14) should be given, and the output will be only control by this block. Otherwise the output will be control by different parameters appearing along the input as well as by the output-controlling block #13. This card contains one integer parameter [1].

|#|Parameter|Description|
|-|---------|-----------|
|1|IUNC|Mode of operation: option for uncertainty calculations.  <br> • **0** Address the activation problem, but without uncertainties calculations.  <br> • **1** Address the problem of computing uncertainties in the activation calculations. Block #14 must be given.|

## Card #3

This is a “catch-all” that gives much of the general information about what type of calculation is being performed. It contains all integer parameters [21].

|#|Parameter|Description|
|-|---------|-----------|
|1|ITMAX|Number of nuclides in the decay data library.|
|2|IZMAX|Number of nonzero elements in the Transition Matrix (≈ITMAX x average number of nuclear processes for each nuclide ≈ 250000, when fission products are not considered. When they are considered, IZMAX should be ≈ 800000).|
|3|MPCTAB|Output option: <br> - **0** No effect. <br> - **1** Print radioactive concentration guides and must be specified to perform calculation of biological hazard potentials (see JTO).|
|4|IR|Output option:<br> - **0** No effect.<br> - **1** Print all elements of the Transition Matrix.|
|5|JTO|Output option (see Table V.1):<br> - **0** Print all available tables for all isotopes, elements, and most important isotopes for post-irradiation periods. BHPs are provided only if MPCTAB=1. If NTABLE=1, only tables for the most important isotopes are printed.<br> - **1** Only selected output tables are printed. Tables are selected using the 8 card of block #2.|
|6|NTABLE|Output option:<br> - **0** No effect. Tables for all isotopes are provided.<br> - **1** Only output tables for most important isotopes. No tables for all isotopes, and no tables for elements. Cutoff points are selected using MSTAR and CUTOFF (card #7 of block #2).|
|7|MSTAR|Timestep used to select the most important isotopes. This timestep is chosen from the post-irradiation periods. Only isotopes with values greater than the thresholds given in CUTOFF are printed.<br> Note: If NTABLE = 0, MSTAR has no effect.|
|8|INPT|Input option (see NUCZO on card #4 of block #2, and block #5). No effect if activated the restart option (see block #4):<br> - **1** Read initial concentrations as elements. <br> - **2** Read initial concentrations as isotopes. <br> - **3** Read initial concentrations as elements in g/cc.|
|9|INFD|Input option (see ISOZO on card #5 of block #2, and block #6):<br>- **0** No effect.<br> - **1** Read continuous feed data for elements.<br> - **2** Read continuous feed data for isotopes.|
|10|NOGG|Number of energy groups for gammas emitted by decay.|
|11|NGRP|Number of energy groups for neutrons (protons or deuterons) (see block #3).<br>If IUNC=0 and IGFP=1 (computing of fission product inventory, see block #10), NGRP must be 1.<br>If IUNC=0 and IGFP=0, the user can choice the number of energy groups according with the cross section library provided.<br>If IUNC=1, the collapsed cross section & uncertainty data library (XSUNC.dat file) should be used, and NGRP must be set to 1.
|12|IGRP|Number of energy groups for gammas used in previous transport calculations. IGRP will be nonzero only when flux files obtained from coupled neutron-gamma transport calculations are provided (see block #3). The current version does not include this capacity.|
|13|IGE|Type of geometry:<br>* One-dimensional:<br>  - **1** planar<br>  - **2** cylindrical<br> - **3** spherical<br>*Two-dimensional:<br>  - **1** x-y <br>  - **2** r-z<br>  - **3** r-q <br>* Three dimensional (coupling to Monte Carlo transport codes):<br>  - **4** It is recommended for flux spatial distributions from Monte Carlo neutron transport codes.|
|14|IZM|Number of material zones.|
|15|IM| Number of spatial intervals in 1-D, in 3-D, or number of 1st dimension spatial intervals in 2-D calculations.
|16|JM|Number of 2nd dimension spatial intervals in 2-D calculations. Set to zero for 1-D or 3-D (from Monte Carlo codes) geometry.|
|17|IFLU|Input option:<br> - **0** No effect.<br> - **1** Flux in free format.<br> - **2** Flux in binary tape.|
|18|IPRT|Output option:<br> - **0** No effect.<br> - **1** Print energy-group scalar neutron fluxes.|
|19|ILIB|Output option (no effect in IUNC=1):<br> - **0** No effect.<br> - **1** Print photon production data per disintegration, and photon mean energy for all isotopes in NOGG-group structure.|
|20|IRAD|Output option (no effect in IUNC=1):<br> - **0** No effect.<br> - **1** Print concentrations (number of atoms) during irradiation times for all isotopes.|
|21|IPUN|Option for generation of unit 9 (no effect in IUNC=1):<br> - **0** No effect.<br> - **1** Print photon release rates (photons/cm3–s) in a NOGG-group structure. Spatial dependence is included. This option is useful as a source term for subsequent photon transport calculations.|

Example:
```plaintext
1373 25000 0 0 1 0 1 1 0 18 175 0 4 1 1 0 1 0 0 1 0
```
This card indicates that there are up to 1373 isotopes in the decay library and up to 25000 nonzero elements in the Transition Matrix. The first timestep is used to determine the list of most important isotopes. Initial concentrations are read as elements. The neutron flux is in 175 groups and gammas produced by activation are to be divided into 18 groups. The geometry is 3-D from a Monte Carlo transport problem. There is one material zone that has only a single interval. The flux is given in free format, and concentrations are requested for all isotopes during the irradiation period. The additional spacing between some values is not required but helps in reading of input files.