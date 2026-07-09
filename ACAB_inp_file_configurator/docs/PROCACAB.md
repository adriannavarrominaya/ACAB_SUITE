# N. Post-processing code PROCACAB

In order to handle the uncertainty output in a friendly way, a post-processing code named **PROCACAB** is included. This utility program is used to process the binary files with the uncertainty information (*.mon) output by ACAB.
The user must specify the binary file to be processed, as well as the information to be extracted from that binary file (nuclides and times of interest):

|#|Parameter|Description|
|-|---------|-----------|
|1|FILE|Name of the binary file to be processed.|
|2|NNUCL|Number of nuclides for which uncertainty information is to be extracted.|
|3|INUCL|Nuclide identifier (the format of the identifier is that defined in block #5). The total number of times this card must appear is equal to NNUCL (INUCL(I), I=1,NNUCL).|
|4|NTIME|Number of time steps for which uncertainty information is required.|
|5|NTIM|Identifier of the time step in the ACAB input. The total number of times this card must appear is equal to NTIME (NTIM(I), I=1,NTIME).|

PROCACAB reads that information (directly from the keyboard or from an input file), writes the requested uncertainty data into ASCII format in a file named montecarlo.out and computes the mean value, standard deviation and relative error of the data in a file named statistics.out. Before running PROCACAB again, those output files should be renamed.
Example of the input to PROCACAB code:
```plaintext
concentration.mon
2
10010
20040
3
1
2
3
```

With this input file, PROCACAB extracts in a file named *montecarlo.out* the inventory prediction (file concentration.mon), for only 2 isotopes (<sup>1</sup>H and <sup>4</sup>He), in 3 time steps (from 1 to 3), computed for the NMOHI histories specified in the Monte Carlo uncertainty calculation. Then, in a file named statistics.out, the computed mean value, standard deviation and relative error are printed.
Example of *montecarlo.out* file:

```plaintext
10010               1              2              3
0.473673E+15   0.947346E+15   0.189469E+16
0.484952E+15   0.969903E+15   0.193981E+16
0.450400E+15   0.900799E+15   0.180160E+16
…
…       [NMOHI histories]
…
0.438310E+15   0.876621E+15   0.175324E+16
0.423977E+15   0.847954E+15   0.169591E+16
0.516860E+15   0.103372E+16   0.206744E+16
20040               1              2              3
0.940494E+14   0.188099E+15   0.376198E+15
0.106149E+15   0.212298E+15   0.424596E+15
…
…       [NMOHI histories]
…
0.936538E+14   0.187308E+15   0.374615E+15
0.967991E+14   0.193598E+15   0.387197E+15
0.105702E+15   0.211404E+15   0.422809E+15
```

Example of *statistics.out* file:

```plaintext
10010              1           2           3
         4.63798E+14 9.27596E+14 1.85519E+15      [Mean values]
         2.77238E+13 5.54475E+13 1.10896E+14      [Standard deviation]
         5.97755E+00 5.97755E+00 5.97759E+00      [Relative error]
20040              1           2           3
         9.87000E+13 1.97400E+14 3.94800E+14      [Mean values]
         4.92755E+12 9.85514E+12 1.97105E+13      [Standard deviation]
         4.99245E+00 4.99247E+00 4.99252E+00      [Relative error]
```