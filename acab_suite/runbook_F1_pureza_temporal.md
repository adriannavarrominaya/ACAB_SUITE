# Runbook F1 — Pureza radionucleídica como serie temporal P(t)

Ítem F1 del BACKLOG (analyzer, A/M). Objetivo: pasar la pureza de escalar a serie temporal durante el enfriamiento, con umbral farmacéutico y ventana de administración. Produce una figura nueva.
## Decisiones de diseño (fijadas, no improvisar)

- **Definición**: P(t) = A(¹³¹I, t) / Σ A(isótopos de yodo, t). Pureza  radionucleídica en base ACTIVIDAD (no átomos). Impurezas = los demás  isótopos de yodo — criterio ya validado. El umbral es 99,9 %.
- **Dominio**: desde el fin de la irradiación (solo fase de enfriamiento). Los datos por timestep ya están parseados; se trata de extender `calcular_pureza` de escalar a serie, no de re-parsear nada.
- **Instante de cruce**: primer timestep de enfriamiento con P(t) ≥ 99,9 %. Entre el último timestep por debajo y el primero por encima, interpolar para estimar t_cruce (interpolación log-lineal sobre las actividades, no sobre P directamente), pero mostrar SIEMPRE los puntos reales; el valor interpolado se etiqueta como estimación. No asumir monotonicidad de P(t) en el código aunque la física la predice (impurezas de yodo decaen más rápido que el ¹³¹I): comprobar que P se mantiene ≥ umbral en los timesteps posteriores al cruce y avisar si no.
- **Casos borde** (ambos deben quedar cubiertos por tests):
  - P ya ≥ 99,9 % al fin de la irradiación → t_cruce = 0, indicarlo.
  - P nunca alcanza el umbral en la ventana simulada → mensaje "umbral no  alcanzado en la ventana de enfriamiento simulada" (sin extrapolar; la acción correcta es alargar el enfriamiento en el inp.5).
- **Ventana de administración**: emparejar P(t) con A(¹³¹I, t). El entregable numérico es: t_cruce, A(¹³¹I) en t_cruce y esa actividad como fracción de la actividad de pico. La lectura física: cuánta actividad queda cuando el producto alcanza calidad farmacéutica.
- **El badge escalar de umbral pendiente queda absorbido** por esta feature (el escalar pasa a ser P(t) evaluada en el instante que corresponda; no mantener dos cálculos de pureza separados).
- **Fuera de alcance**: actividad específica con I-127/I-129 como diluyentes (eso es F2, no mezclarlo aquí).

## Fase 0 — Baseline

- Despachar C5 si sigue abierto (rutas rotas tras la reorg de examples/).
- Suite completa del analyzer (Python + node) en verde, sin excepciones.

## Fase 1 — Backend: serie P(t)

- Extender `calcular_pureza` (o función hermana que la reutilice) para devolver la serie {t, P(t)} de la fase de enfriamiento + el escalar derivado, manteniendo compatible el uso existente.
- Cálculo de t_cruce con la interpolación y los casos borde definidos arriba.
- **Verificación (tests oro)**: sobre un fort.6 congelado del proyecto, verificar A MANO una única vez P(t) en tres timesteps (uno temprano, uno cercano al cruce, uno tardío) y fijarlos como valores esperados. Tests de los dos casos borde con fort.6 sintéticos mínimos. Suite en verde.

## Fase 2 — API

- Exponer la serie, t_cruce y los valores de la ventana de administración en el endpoint que consume la pestaña de optimización (o el que corresponda; decidir en sesión mirando cómo fluyen hoy las métricas escalares).
- **Verificación**: test de endpoint contra el mismo caso oro de la Fase 1.

## Fase 3 — Frontend

- Gráfica P(t) en enfriamiento: línea de umbral en 99,9 %, marcador de t_cruce con etiqueta ("tiempo mínimo de enfriamiento para calidad farmacéutica"). Eje y con zoom razonable (P vive entre ~90 % y 100 %; una escala 0–100 % aplasta la información).
- Emparejar con A(¹³¹I, t): mismo eje temporal (doble eje o gráfica apilada, decidir en sesión con lo que ya use la pestaña), con el marcador de t_cruce cruzando ambas para leer la ventana de administración.
- Los dos casos borde renderizan sus mensajes, no gráficas vacías.
- i18n completa (es/en) de todas las claves nuevas — que no nazca otro optim.type_spectrum.
- **Verificación**: tests node de las utilidades JS nuevas; revisión visual con el caso oro y con un barrido para confirmar que no rompe la vista multi-simulación.

## Fase 4 — Cierre

- Retirar/absorber el badge escalar antiguo.
- Docs de la app actualizadas (la pestaña ganó una capacidad).
- Suite completa en verde. Commits con prefijo analyzer: (+ suite: para el  backlog). Marcar F1 ✅ con fecha.

## Verificación humana (tablón)

Con el caso de referencia: comprobar a mano en el fort.6 el timestep de cruce (localizar en el texto el primer paso de enfriamiento donde la actividad del ¹³¹I supera 999× la suma de los demás yodos) y confirmar que coincide con el timestep que la gráfica marca. Anotar t_cruce y A(t_cruce) como firma numérica del control.
