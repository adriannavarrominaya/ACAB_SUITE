"""Tests del análisis de contribución por cadenas (F9 del BACKLOG, Fases 2-3).

    C:\\venv\\acab-venv\\Scripts\\python.exe tools/test_chains_analysis.py

Cubre: chains_inventory.py (códec ZZAAAS + parser del inventario inicial,
con un extracto sintético de fort.6 autocontenido -- el fort.6 real de
referencia vive en el repo del analyzer, no se duplica aquí solo para estos
tests unitarios), chains_analysis.py (generación: patch monoisotópico del
Bloque #5 + ajuste NUCZO, patches de tapes, validaciones, tests de bytes
contra los casos oro de tests/fixtures/chains/ construidos en Fase 0/2) y
build_chains_pipeline_jobs (estructura de jobs de la Fase 3).
"""

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import chains_analysis as ca                      # noqa: E402
import chains_inventory as ci                      # noqa: E402
from acab_parser import ACABParser                 # noqa: E402
from app import _write_inp5                        # noqa: E402
from sweep_writer import SweepError                # noqa: E402

FIXTURES = Path(__file__).resolve().parents[1] / 'tests/fixtures/chains'

# Extracto sintético mínimo del formato NUMBER OF ATOMS del fort.6 (mismas
# columnas que ref_sim/fort.6 del analyzer, ver docstring del módulo):
# cabecera + H (elemento de una letra, símbolo/masa en tokens separados) +
# O16/O17/O18 (blanco TeO2) + TE130 + TOTAL.
_SYNTHETIC_FORT6 = """1Activation of tellurium oxide
0NUCLIDE IDENTIFIERS, INITIAL CONCENTRATIONS(ATOMS/CCM)
0                                        NUMBER OF ATOMS
                                                    INTERVAL  1

         INITIAL  2.78E-03
  H  1  0.000E+00 4.611E+06
  O 16  9.267E+20 9.267E+20
  O 17  3.530E+17 3.530E+17
  O 18  1.858E+18 1.858E+18
 TE128  1.472E+20 1.472E+20
 TE130  1.570E+20 1.570E+20
 TOTAL  2.314E-03 2.314E-03
"""


class ChainsInventoryTests(unittest.TestCase):

    def test_leer_concentraciones_iniciales_synthetic(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / 'fort.6'
            f.write_text(_SYNTHETIC_FORT6, encoding='utf-8')
            c = ci.leer_concentraciones_iniciales(str(f))
        # H1 tiene C_i=0 (INITIAL) -> excluido; O16/O17/O18/TE128/TE130 > 0.
        self.assertNotIn('H1', c)
        self.assertAlmostEqual(c['O16'], 9.267e20, delta=1e15)
        self.assertAlmostEqual(c['O17'], 3.530e17, delta=1e12)
        self.assertAlmostEqual(c['O18'], 1.858e18, delta=1e13)
        self.assertAlmostEqual(c['TE128'], 1.472e20, delta=1e15)
        self.assertAlmostEqual(c['TE130'], 1.570e20, delta=1e15)
        self.assertNotIn('TOTAL', c)

    def test_nombre_a_zzaaas_casos_directos(self):
        self.assertEqual(ci.nombre_a_zzaaas('TE130'), 521300)
        self.assertEqual(ci.nombre_a_zzaaas('I131'), 531310)
        self.assertEqual(ci.nombre_a_zzaaas('TE131M'), 521311)
        self.assertEqual(ci.nombre_a_zzaaas('te131m'), 521311)

    def test_nombre_a_zzaaas_invalido(self):
        with self.assertRaises(ValueError):
            ci.nombre_a_zzaaas('no es un isotopo')
        with self.assertRaises(ValueError):
            ci.nombre_a_zzaaas('ZZ999')


class ChainsAnalysisGenerationTests(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='chains_analysis_test_'))
        self.ref = self.tmp / 'ref'
        self.ref.mkdir()
        shutil.copy(FIXTURES / 'inp.5_original', self.ref / 'inp.5')
        self.root = self.tmp / 'out'

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _payload(self, **overrides):
        payload = {
            'root': str(self.root),
            'reference_folder': str(self.ref),
            'isotopes': [{'name': 'TE130', 'c_i': 1.57e20}],
            'ifinal': 'I131',
            'pcnt': 0.01,
            'nmax': 5,
        }
        payload.update(overrides)
        return payload

    # ── Camino feliz: bytes exactos contra los casos oro congelados ──────

    def test_tape22_matches_frozen_fixture(self):
        ca.generate_chains_analysis(self._payload(), _write_inp5)
        got = (self.root / 'tape22' / 'inp.5').read_text(encoding='utf-8')
        want = (FIXTURES / 'inp.5_tape22').read_text(encoding='utf-8')
        self.assertEqual(got, want)

    def test_tape24_matches_frozen_fixture(self):
        ca.generate_chains_analysis(self._payload(), _write_inp5)
        got = (self.root / 'tape24' / 'inp.5').read_text(encoding='utf-8')
        want = (FIXTURES / 'inp.5_tape24').read_text(encoding='utf-8')
        self.assertEqual(got, want)

    def test_iso_monoisotopic_matches_frozen_fixture(self):
        # Caso oro de la Fase 2: firma numérica de la Fase 0 (Σ C_i(Te) ->
        # XCOMP_i = C_i * 1e-24) para TE130, C_i=1.57E20 át/cm³ (mismo
        # valor leído del fort.6 real de referencia). INPT=2 ("read as
        # isotopes") desde F9e -- el fixture original (INPT=1 heredado de
        # la referencia) codificaba el bug de causa raíz que expandía a
        # Te natural en vez del isótopo puro (ver PROCEDENCIA.md).
        ca.generate_chains_analysis(self._payload(), _write_inp5)
        got = (self.root / 'iso_TE130' / 'inp.5').read_text(encoding='utf-8')
        want = (FIXTURES / 'inp.5_iso_TE130').read_text(encoding='utf-8')
        self.assertEqual(got, want)

    def test_iso_monoisotopic_nuczo_and_block5_content(self):
        res = ca.generate_chains_analysis(self._payload(), _write_inp5)
        data = ACABParser().read_inp5(self.root / 'iso_TE130' / 'inp.5')
        self.assertEqual(data['block1']['INPT'], 2)
        self.assertEqual(data['block2']['NUCZO'], [1])
        self.assertEqual(data['block5'], [{'INUCL': [521300], 'XCOMP': [1.57e-4]}])
        iso = res['manifest']['isotopes'][0]
        self.assertEqual(iso['zzaaas'], 521300)
        self.assertAlmostEqual(iso['xcomp'], 1.57e-4)

    def test_tape_patches_do_not_touch_inpt(self):
        # F9e: solo el patch monoisotópico fija INPT=2 -- tape22/tape24
        # reutilizan la composición de referencia SIN modificar y deben
        # conservar el INPT de la referencia (INPT=1 en inp.5_original).
        ca.generate_chains_analysis(self._payload(), _write_inp5)
        for folder in ('tape22', 'tape24'):
            data = ACABParser().read_inp5(self.root / folder / 'inp.5')
            self.assertEqual(data['block1']['INPT'], 1, folder)

    def test_input_chain_txt_matches_frozen_fixture(self):
        ca.generate_chains_analysis(self._payload(), _write_inp5)
        got = (self.root / 'chains_TE130' / 'input_chain.txt').read_text(encoding='utf-8')
        want = (FIXTURES / 'input_chain_generated_TE130_to_I131.txt').read_text(encoding='utf-8')
        self.assertEqual(got, want)

    def test_chains_exe_copied_if_present_in_reference(self):
        (self.ref / 'chains.exe').write_text('fake chains exe', encoding='utf-8')
        ca.generate_chains_analysis(self._payload(), _write_inp5)
        self.assertTrue((self.root / 'chains_TE130' / 'chains.exe').is_file())

    def test_chains_exe_absent_does_not_fail_generation(self):
        # chains.exe puede añadirse a mano más tarde; su ausencia en la
        # referencia no debe impedir generar (solo fallaría el pre-check de
        # ejecución, Fase 3).
        ca.generate_chains_analysis(self._payload(), _write_inp5)
        self.assertFalse((self.root / 'chains_TE130' / 'chains.exe').exists())

    def test_reference_acab_exe_and_decay_dat_copied_to_all_run_folders(self):
        (self.ref / 'acab.exe').write_text('fake acab', encoding='utf-8')
        (self.ref / 'DECAY.dat').write_text('fake decay', encoding='utf-8')
        ca.generate_chains_analysis(self._payload(), _write_inp5)
        for folder in ('tape22', 'tape24', 'iso_TE130'):
            self.assertTrue((self.root / folder / 'acab.exe').is_file(), folder)
            self.assertTrue((self.root / folder / 'DECAY.dat').is_file(), folder)

    # ── F9c: sembrado de REACTIONS.dat/DECAY.dat en chains_<isótopo> ──────

    def test_reactions_dat_and_decay_dat_seeded_into_chains_folder(self):
        # Sin esto chains.exe aborta al arrancar (unit 122, ver
        # chains_analysis.CHAINS_SEED_DATA_FILES) -- bug real de la primera
        # ejecución (evidencia en run.log: "forrtl: severe (24):
        # end-of-file during read, unit 122, REACTIONS.dat").
        (self.ref / 'REACTIONS.dat').write_text('fake reactions', encoding='utf-8')
        (self.ref / 'DECAY.dat').write_text('fake decay', encoding='utf-8')
        ca.generate_chains_analysis(self._payload(), _write_inp5)
        self.assertEqual((self.root / 'chains_TE130' / 'REACTIONS.dat').read_text(encoding='utf-8'),
                         'fake reactions')
        self.assertEqual((self.root / 'chains_TE130' / 'DECAY.dat').read_text(encoding='utf-8'),
                         'fake decay')

    def test_reactions_dat_absent_in_reference_does_not_fail_generation(self):
        # Como chains.exe (ausencia solo rompe el pre-check de ejecución,
        # no la generación).
        ca.generate_chains_analysis(self._payload(), _write_inp5)
        self.assertFalse((self.root / 'chains_TE130' / 'REACTIONS.dat').exists())

    # ── F9c: exclusión de salidas obsoletas del material base ─────────────

    def test_stale_fort_outputs_excluded_from_tapes_and_iso_folders(self):
        # La carpeta de referencia real usada en la primera ejecución
        # llevaba fort.22/23/24 (de una ejecución sin relación con este
        # pipeline) y un fort.17 de 0 bytes -- confunden la traza de qué
        # tape pertenece a ESTE análisis (patrón C4).
        for name in ('fort.17', 'fort.22', 'fort.23', 'fort.24'):
            (self.ref / name).write_text('stale', encoding='utf-8')
        res = ca.generate_chains_analysis(self._payload(), _write_inp5)
        for folder in ('tape22', 'tape24', 'iso_TE130'):
            for name in ('fort.17', 'fort.22', 'fort.23', 'fort.24'):
                self.assertFalse((self.root / folder / name).exists(), f'{folder}/{name}')
        excluded = set(res['manifest']['excluded_base_files'])
        for name in ('fort.17', 'fort.22', 'fort.23', 'fort.24'):
            self.assertIn(name, excluded)

    def test_manifest_written(self):
        res = ca.generate_chains_analysis(self._payload(), _write_inp5)
        import json
        manifest = json.loads((self.root / 'chains_manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['ifinal'], 'I131')
        self.assertEqual(manifest['ifinal_zzaaas'], 531310)
        self.assertEqual(manifest['tape22_folder'], 'tape22')
        self.assertEqual(manifest['tape24_folder'], 'tape24')
        self.assertEqual(len(manifest['isotopes']), 1)
        self.assertEqual(res['manifest'], manifest)

    def test_multiple_isotopes(self):
        res = ca.generate_chains_analysis(self._payload(isotopes=[
            {'name': 'TE130', 'c_i': 1.57e20},
            {'name': 'TE128', 'c_i': 1.472e20},
        ]), _write_inp5)
        self.assertEqual(res['n_isotopes'], 2)
        self.assertTrue((self.root / 'iso_TE128' / 'inp.5').is_file())
        self.assertTrue((self.root / 'chains_TE128' / 'input_chain.txt').is_file())
        data = ACABParser().read_inp5(self.root / 'iso_TE128' / 'inp.5')
        self.assertEqual(data['block5'][0]['INUCL'], [521280])

    # ── Validaciones ──────────────────────────────────────────────────────

    def test_missing_root(self):
        with self.assertRaises(SweepError):
            ca.generate_chains_analysis(self._payload(root=''), _write_inp5)

    def test_missing_reference_inp5(self):
        empty_ref = self.tmp / 'empty_ref'
        empty_ref.mkdir()
        with self.assertRaises(SweepError):
            ca.generate_chains_analysis(
                self._payload(reference_folder=str(empty_ref)), _write_inp5)

    def test_no_isotopes(self):
        with self.assertRaises(SweepError):
            ca.generate_chains_analysis(self._payload(isotopes=[]), _write_inp5)

    def test_invalid_isotope_name(self):
        with self.assertRaises(SweepError):
            ca.generate_chains_analysis(
                self._payload(isotopes=[{'name': 'no es un isotopo', 'c_i': 1.0}]),
                _write_inp5)

    def test_invalid_ifinal(self):
        with self.assertRaises(SweepError):
            ca.generate_chains_analysis(self._payload(ifinal='???'), _write_inp5)

    def test_invalid_pcnt_nmax(self):
        with self.assertRaises(SweepError):
            ca.generate_chains_analysis(self._payload(pcnt=0), _write_inp5)
        with self.assertRaises(SweepError):
            ca.generate_chains_analysis(self._payload(nmax=0), _write_inp5)

    def test_collision_without_overwrite_raises_409(self):
        ca.generate_chains_analysis(self._payload(), _write_inp5)
        try:
            ca.generate_chains_analysis(self._payload(), _write_inp5)
            self.fail('se esperaba SweepError 409')
        except SweepError as exc:
            self.assertEqual(exc.status, 409)

    def test_overwrite_regenerates(self):
        ca.generate_chains_analysis(self._payload(), _write_inp5)
        res = ca.generate_chains_analysis(self._payload(overwrite=True), _write_inp5)
        self.assertEqual(res['n_isotopes'], 1)

    def test_multi_zone_reference_rejected(self):
        data = ACABParser().read_inp5(self.ref / 'inp.5')
        data['block2']['NUCZO'] = [1, 1]
        data['block5'] = [
            {'INUCL': [10010], 'XCOMP': [1.0]},
            {'INUCL': [80000], 'XCOMP': [1.0]},
        ]
        (self.ref / 'inp.5').write_text(_write_inp5(data), encoding='utf-8')
        with self.assertRaises(SweepError):
            ca.generate_chains_analysis(self._payload(), _write_inp5)

    def test_infd_reference_rejected(self):
        data = ACABParser().read_inp5(self.ref / 'inp.5')
        data['block1']['INFD'] = 1
        (self.ref / 'inp.5').write_text(_write_inp5(data), encoding='utf-8')
        with self.assertRaises(SweepError):
            ca.generate_chains_analysis(self._payload(), _write_inp5)


class PreviewChainsAnalysisTests(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='chains_analysis_preview_'))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_preview_reports_folders_and_collisions(self):
        root = self.tmp / 'out'
        root.mkdir()
        (root / 'tape22').mkdir()
        res = ca.preview_chains_analysis(
            str(root), str(self.tmp), [{'name': 'TE130', 'c_i': 1.0}])
        self.assertEqual(res['folders'], ['tape22', 'tape24', 'iso_TE130', 'chains_TE130'])
        self.assertEqual(res['collisions'], ['tape22'])
        self.assertEqual(res['n_isotopes'], 1)

    def test_preview_over_limit(self):
        isotopes = [{'name': 'TE130', 'c_i': 1.0} for _ in range(ca.MAX_ISOTOPES + 1)]
        res = ca.preview_chains_analysis(str(self.tmp / 'out'), str(self.tmp), isotopes)
        self.assertTrue(res['over_limit'])


class BuildChainsPipelineJobsTests(unittest.TestCase):

    def test_job_structure(self):
        root_p = Path('/root')
        manifest = {
            'tape22_folder': 'tape22', 'tape24_folder': 'tape24',
            'isotopes': [
                {'name': 'TE130', 'iso_folder': 'iso_TE130', 'chains_folder': 'chains_TE130'},
                {'name': 'TE128', 'iso_folder': 'iso_TE128', 'chains_folder': 'chains_TE128'},
            ],
        }
        jobs = ca.build_chains_pipeline_jobs(root_p, manifest, 'acab.exe', 'chains.exe')
        self.assertEqual(len(jobs), 4)  # tape22, tape24, 2 isótopos

        self.assertEqual(jobs[0]['workdir'], str(root_p / 'tape22'))
        self.assertEqual(len(jobs[0]['steps']), 1)
        self.assertEqual(jobs[0]['steps'][0]['type'], 'run')

        self.assertEqual(jobs[1]['workdir'], str(root_p / 'tape24'))

        iso_job = jobs[2]
        self.assertEqual(iso_job['workdir'], str(root_p / 'iso_TE130'))
        steps = iso_job['steps']
        self.assertEqual([s['type'] for s in steps], ['run', 'copy', 'copy', 'run'])
        self.assertEqual(steps[0]['cwd'], str(root_p / 'iso_TE130'))
        self.assertEqual(steps[1]['src'], str(root_p / 'tape22' / 'fort.22'))
        self.assertEqual(steps[1]['dst'], str(root_p / 'chains_TE130' / 'fort.22'))
        self.assertEqual(steps[2]['src'], str(root_p / 'tape24' / 'fort.24'))
        self.assertEqual(steps[2]['dst'], str(root_p / 'chains_TE130' / 'fort.24'))
        chains_step = steps[3]
        self.assertEqual(chains_step['cwd'], str(root_p / 'chains_TE130'))
        self.assertEqual(chains_step['stdin'], str(root_p / 'chains_TE130' / 'input_chain.txt'))
        self.assertEqual(chains_step['stdout_file'], str(root_p / 'chains_TE130' / 'output_chain.txt'))

    def test_reference_folder_absent_from_manifest_does_not_raise(self):
        # Manifest sintético (sin 'reference_folder', a diferencia de un
        # chains_manifest.json real): la limpieza pre-run (F9c) debe
        # degradar sin más, no reventar la construcción de jobs.
        root_p = Path('/root')
        manifest = {
            'tape22_folder': 'tape22', 'tape24_folder': 'tape24',
            'isotopes': [
                {'name': 'TE130', 'iso_folder': 'iso_TE130', 'chains_folder': 'chains_TE130'},
            ],
        }
        jobs = ca.build_chains_pipeline_jobs(root_p, manifest, 'acab.exe', 'chains.exe')
        self.assertEqual(len(jobs), 3)  # tape22, tape24, 1 isótopo


class CleanChainsDirBeforeRunTests(unittest.TestCase):
    """F9c: limpieza/re-siembra de una carpeta chains_<isótopo> antes de
    (re)lanzar CHAINS -- sin esto, el re-run de un análisis ya generado
    hereda los restos de un intento fallido anterior."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='chains_clean_test_'))
        self.ref = self.tmp / 'ref'
        self.ref.mkdir()
        self.chains_dir = self.tmp / 'chains_TE130'
        self.chains_dir.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_removes_stale_residual_files(self):
        (self.chains_dir / 'output_chain.txt').write_text('', encoding='utf-8')
        (self.chains_dir / 'fort.23').write_text('scratch', encoding='utf-8')
        (self.chains_dir / 'fort.31').write_text('scratch', encoding='utf-8')
        ca._clean_chains_dir_before_run(self.chains_dir, None)
        for name in ('output_chain.txt', 'fort.23', 'fort.31'):
            self.assertFalse((self.chains_dir / name).exists(), name)

    def test_reseeds_reactions_and_decay_dat_from_reference(self):
        # El caso real: la carpeta ya tiene un REACTIONS.dat de 0 bytes
        # (el que el propio OPEN de Fortran crea al no encontrar el
        # fichero real en un intento anterior) y ningún DECAY.dat.
        (self.chains_dir / 'REACTIONS.dat').write_text('', encoding='utf-8')
        (self.ref / 'REACTIONS.dat').write_text('real reactions data', encoding='utf-8')
        (self.ref / 'DECAY.dat').write_text('real decay data', encoding='utf-8')

        ca._clean_chains_dir_before_run(self.chains_dir, self.ref)

        self.assertEqual((self.chains_dir / 'REACTIONS.dat').read_text(encoding='utf-8'),
                         'real reactions data')
        self.assertEqual((self.chains_dir / 'DECAY.dat').read_text(encoding='utf-8'),
                         'real decay data')

    def test_no_reference_folder_leaves_data_files_untouched(self):
        (self.chains_dir / 'REACTIONS.dat').write_text('kept as-is', encoding='utf-8')
        ca._clean_chains_dir_before_run(self.chains_dir, None)
        self.assertEqual((self.chains_dir / 'REACTIONS.dat').read_text(encoding='utf-8'),
                         'kept as-is')

    def test_reference_missing_seed_files_does_not_raise(self):
        # La referencia no tiene REACTIONS.dat/DECAY.dat (p. ej. el propio
        # escenario de la regresión de fin a fin): no hay de dónde
        # resembrar, la limpieza no debe fallar.
        ca._clean_chains_dir_before_run(self.chains_dir, self.ref)
        self.assertFalse((self.chains_dir / 'REACTIONS.dat').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
