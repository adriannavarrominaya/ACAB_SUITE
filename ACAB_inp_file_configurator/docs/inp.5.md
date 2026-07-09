# V. Input Description

An ACAB run is specified by means of the INPUT file. In the current version of the ACAB code, the input data are read in FORTRAN free format. This version is fully portable to all computers.

ACAB input data is structured in data blocks, each one containing interrelated data. The input file consists of Blocks #1, #2, …, #14. Each block may consist of one or more cards. The word “card” is used to describe a single line of input with one or more parameters.

Comments may be included throughout an ACAB input file. The comments must be denoted by the symbol < in the first column of any card (line). A comment card can only be provided in front of a numerical card. It can have any arbitrary length. In addition you can make comments at the end of any numerical card.

Some of the conventions used throughout the input description that follows is the use of numbers in [ ] for dimensions of the vector or matrix being described. Expressions in { } represent conditions that must be fulfilled in order to correctly enter input. Recommended values for input are specified in ( ).

First versions of the ACAB code used the FIDO free format to read some input data. The blocks read in FIDO free format were #1, #2, #3, #5, #6, #7, #8 and #9. In these FIDO format blocks, all cards starting with number$$ accepted integer values, and those starting with number** required floating point values. Any FIDO format block ended with a “T”. Comments were denoted by a single quote (‘) in the first column of any line. This version was computer-dependent.

The FORTRAN input file in the current version differs from the FIDO/FORTRAN input file in only two aspects: The number\$\$ or the number\*\* starting all the FIDO cards in the FIDO/FORTRAN file must not appear, and the “T” signaling termination of a FIDO block must also not appear. Thus, if an user wants to turn a a FIDO/FORTRAN input file into a FORTRAN input file, he/she needs only delete all the number\$\$, number\*\*, and  “T” appearing in the FIDO/FORTRAN file.

We will now go through the ACAB input one block at a time. For each card, an example will be given.

[A. Block#1](Block%231.md)
[B. Block#2](Block%232.md)
[C. Block#3](Block%233.md)
[D. Block#4](Block%234.md)
[E. Block#5](Block%235.md)
[F. Block#6](Block%236.md)
[G. Block#7&#8](Block%237&%238.md)
[H. Block#9](Block%239.md)
[I. Block#10](Block%2310.md)
[J. Block#11](Block%2311.md)
[K. Block#12](Block%2312.md)
[L. Block#13](Block%2313.md)
[M. Block#14](Block%2314.md)
[N. PROCACAB](PROCACAB.md)