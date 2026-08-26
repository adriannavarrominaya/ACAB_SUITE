# `sweep_manifest.json` — cálculo paramétrico de espectro, 9 reactores (PRE-renombrado)

## Qué es

Copia **byte-idéntica** del `sweep_manifest.json` REAL del cálculo paramétrico
de espectro de nueve reactores del TFG, generado el **2026-07-13** con la
versión de la app anterior al renombrado terminológico
«barrido paramétrico» → «cálculo paramétrico».

Origen: `…/TFG/Documentacion/ACAB/barridos/Barrido 5/sweep_manifest.json`
(nueve espectros CONDERC del OIEA: LANL-OWR, Cf252, MURR-G1, HFR-C3, Phenix,
ITER-DT, HFIR-VXF3-AD, SCK-BR2, LR-0-Void).

## Para qué sirve

Es el **caso oro de compatibilidad hacia atrás** del renombrado. Un análisis ya
generado tiene que seguir abriéndose sin avisos ni migraciones, así que este
fichero congela la forma que escribía la app ANTES del cambio:

- nombre de fichero `sweep_manifest.json` (no se renombró),
- clave `sweep_type` con el valor `"spectrum"` (identificadores internos en
  inglés: `flux` / `mass` / `time` / `spectrum`, tampoco se renombraron),
- `description` en la terminología antigua (`"Barrido de expectro"`, con la
  errata del original: se conserva tal cual, es un dato real del usuario),
- **sin** la clave `excluded_base_files` (es anterior a C4 del BACKLOG), que la
  vista debe degradar a `[]` sin romper.

Consumido por `tools/test_sweep_manifest_view.py`
(`ManifiestoRealPreRenombradoTests`). La copia hermana del analyzer
(`ACAB_fort_file_analyzer/tests/fixtures/sweep_pre_renombrado/`) cubre el otro
lector del mismo fichero (`leer_sweep_manifest` + pestaña Optimización); se
duplica en vez de compartirse porque la suite de cada repo es autocontenida
(misma regla que `tests/fixtures/COLL.inp`).

## No editar

Si se edita, deja de ser un manifiesto real anterior al cambio y el test deja
de probar lo que dice probar. Para casos nuevos, añade fixtures aparte.
