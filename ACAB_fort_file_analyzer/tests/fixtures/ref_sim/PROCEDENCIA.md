# Procedencia de ref_sim

Copia congelada de: `ACAB_fort_file_analyzer\simulaciones\simulaciones 1er Exp\Simulacion v.5 - info thesis` Verificada idéntica al original (SHA256): 2026-07-22 SHA256 fort.6: 3c3bfb3984202521b0b4a5128908ec5e61935a8f3de5772a2962061571372a74
Caso: pulso 10 s, blanco 0,1231 g TeO2, espectro de la tesis (info thesis).

Es la REFERENCIA CANÓNICA de caso del tablón (README.md de la suite): las firmas de F1 (P(t)), F2/F2b (A_esp) y B1 (línea de 364 keV) se calculan sobre ella.

No modificar: cualquier re-congelación exige re-verificar los valores oro que dependen de este fichero y anotarlo en el tablón.

NOTA: el fort.6 de "Simulacion v.7 - DECAY" es una variante del mismo pulso con XSECTION distinto (I127/I129 ~15-20x mayores por el cociente de capturas Te-128/Te-130); NO es fixture. Si algún test futuro necesita un caso de espectro alternativo, congelarlo entonces con su propia PROCEDENCIA.md.

## Advertencia sobre la validez física

Este fixture procede de una configuración con el colapso de tres grupos posteriormente identificado como defectuoso, en la que solo cinco secciones eficaces fueron corregidas a mano. En consecuencia, **solo la cadena de producción del ¹³¹I es físicamente representativa**: las impurezas, la pureza y la actividad específica que se derivan de este fichero están sesgadas por órdenes de magnitud (verificado: el ¹²⁹I aparece suprimido un factor 19 respecto de la configuración correcta, lo que eleva artificialmente la fracción másica del ¹³¹I del 73 % real al 98 %).

Esto NO invalida su papel: el fixture existe para verificar que la herramienta calcula de forma correcta y estable a partir de un `fort.6` dado, y eso es independiente de la física que generó ese fichero. Las firmas del tablón ancladas aquí son verificaciones DE LA HERRAMIENTA.

**Ninguna cifra de este fixture puede citarse como resultado físico en la memoria.**