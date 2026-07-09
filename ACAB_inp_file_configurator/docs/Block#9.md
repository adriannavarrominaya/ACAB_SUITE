# H. Block #9

It consists of only one card, including two values in real free-format. Block #9 tells ACAB what truncation error is allowable and allows the user to scale the total flux (so that all of the fluxes don’t have to be multiplied by 75%, for example).

## Card #1

|#|Parameter|Description|
|-|---------|-----------|
|1|ERR|Truncation error (10<sup>-25</sup>).|
|2|XNORM|Normalization factor (1.0). If XNORM is negative, a test printout of the neutron-induced transmutation rates by interval or zone will be given. The resulting output may be quite voluminous.|

**Example**

```plaintext
< ERR   XNORM
1.0E-25 7.50E-01
```

This example uses the standard truncation error, but tells ACAB to scale all of the fluxes by a factor of 0.75. This might be done if the user desired to simulate 40 years of operation at 75% of capacity, for example.
