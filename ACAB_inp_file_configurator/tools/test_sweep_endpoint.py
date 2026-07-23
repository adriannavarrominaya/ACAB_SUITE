"""Tests del generador de barridos (Fase 2 del runbook v2; Fase P2 del
RUNBOOK_barrido_espectral.md para los tests de coll_patch).

    C:\\venv\\acab-venv\\Scripts\\python.exe tools/test_sweep_endpoint.py

Cubre: merge recursivo, flujo feliz (copia de carpeta base + reemplazo de
inp.5 + manifest coherente), colisión 409, límites 422 (N>200, sufijo
duplicado, descripción vacía), aborto + limpieza ante un patch que produce
un inp.5 inválido / no re-parseable, y el barrido espectral (coll_patch):
escritura de collaps/COLL.inp por sim, 422 si falta collaps/COLL.inp en la
base, y round-trip del COLL.inp generado.
"""
import csv
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app as appmod                              # noqa: E402
from acab_parser import ACABParser               # noqa: E402
from coll_writer import read_coll_inp            # noqa: E402
from sweep_writer import SweepError, deep_merge, _roundtrip_check  # noqa: E402

FIXTURE_COLL_211 = Path(__file__).resolve().parents[1] / 'tests/fixtures/spectra/COLL.inp'


class DeepMergeTests(unittest.TestCase):
    def test_scalar_replaced(self):
        self.assertEqual(deep_merge({'a': 1, 'b': 2}, {'a': 9}), {'a': 9, 'b': 2})

    def test_nested_dict_merged(self):
        self.assertEqual(
            deep_merge({'b': {'x': 1, 'y': 2}}, {'b': {'y': 9}}),
            {'b': {'x': 1, 'y': 9}})

    def test_list_replaced_whole(self):
        self.assertEqual(deep_merge({'l': [1, 2, 3]}, {'l': [9]}), {'l': [9]})

    def test_no_mutation(self):
        base = {'b': {'x': 1}}
        deep_merge(base, {'b': {'x': 2}})
        self.assertEqual(base, {'b': {'x': 1}})


class SweepEndpointTests(unittest.TestCase):
    def setUp(self):
        self.client = appmod.app.test_client()
        self.tmp = Path(tempfile.mkdtemp())
        self.base = self.tmp / 'base'
        (self.base / 'sub').mkdir(parents=True)
        (self.base / 'lib.dat').write_text('library data', encoding='utf-8')
        (self.base / 'sub' / 'aux.txt').write_text('aux', encoding='utf-8')
        (self.base / 'inp.5').write_text('OLD BASE INP', encoding='utf-8')
        self.data = appmod._default_data()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _flux_sims(self, values):
        return [{'suffix': f'x{v}', 'params': {'XNORM': v},
                 'patch': {'block9': {'XNORM': v}}} for v in values]

    def test_default_data_roundtrips(self):
        # Prerrequisito del flujo feliz: el fichero base debe re-parsear.
        _roundtrip_check(appmod._write_inp5(self.data), ACABParser(), 'default')

    def test_happy_path(self):
        root = self.tmp / 'out'
        sims = self._flux_sims([0.5, 0.75, 1.0])
        r = self.client.post('/api/sweep', json={
            'root': str(root), 'base_folder': str(self.base), 'prefix': 'TeO2_',
            'description': 'barrido de flujo de prueba', 'sweep_type': 'flux',
            'fixed_params': {'masa': '0.1231 g', 'T_irr': '24 h'},
            'data': self.data, 'sims': sims})
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True))
        body = r.get_json()
        self.assertTrue(body['ok'])
        self.assertEqual(body['n_written'], 3)

        for suf, xn in [('x0.5', '5.000000E-01'), ('x0.75', '7.500000E-01'),
                        ('x1.0', '1.000000E+00')]:
            d = root / f'TeO2_{suf}'
            self.assertTrue(d.is_dir())
            self.assertTrue((d / 'lib.dat').exists(), 'copió lib.dat de la base')
            self.assertTrue((d / 'sub' / 'aux.txt').exists(), 'copió subdir')
            inp = (d / 'inp.5').read_text(encoding='utf-8')
            self.assertNotIn('OLD BASE INP', inp, 'inp.5 base reemplazado')
            self.assertIn(xn, inp, 'XNORM aplicado en el inp.5')
            _roundtrip_check(inp, ACABParser(), suf)

        manifest = json.loads((root / 'sweep_manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['n'], 3)
        self.assertEqual(manifest['sweep_type'], 'flux')
        self.assertEqual(len(manifest['simulations']), 3)
        self.assertEqual(manifest['simulations'][0]['folder'], 'TeO2_x0.5')
        self.assertIn('masa', manifest['fixed_params'])

        csv_txt = (root / 'sweep_manifest.csv').read_text(encoding='utf-8')
        self.assertIn('folder', csv_txt)
        self.assertIn('XNORM', csv_txt)
        self.assertTrue((root / 'README.txt').exists())
        self.assertTrue((root / 'run_all.ps1').exists())
        self.assertTrue((root / 'run_all.sh').exists())

    def test_time_sweep_byte_identical_manual_vs_sweep_path(self):
        """U7 del BACKLOG: refresco automatizado de "Control de malla" (README
        de acab_suite, verificado antes a mano con fc) para el caso
        multi-tramo. Prueba la identidad del CAMINO DE ESCRITURA del servidor
        (deep_merge + _write_inp5, vía sweep_writer, vs _write_inp5 directo,
        vía el flujo manual) -- NO las matemáticas de la malla, ya cubiertas
        por el test de equivalencia buildTimePatches ≡ buildBlocks78 en
        tools/test_sweep_utils.js. El blocks78 usado aquí es un literal
        cualquiera válido: lo único que importa es que ambos caminos reciban
        el MISMO patch.
        """
        blocks78 = {
            'sets': [
                {'MMN': 2, 'MOUT': 3, 'NGO': 1, 'MSUB': 0, 'IUNIT': 3,
                 'MFEED': 0, 'IOUT': 1, 'IPLOT': 0, 'TIMES': [10.0, 20.0, 5.0]},
                {'MMN': 0, 'MOUT': 2, 'NGO': 0, 'MSUB': 3, 'IUNIT': 3,
                 'MFEED': 0, 'IOUT': 1, 'IPLOT': 0, 'TIMES': [15.0, 30.0]},
            ],
            'times': [[10.0, 1], [20.0, 1], [5.0, 0], [15.0, 0], [30.0, 0]],
        }
        # block13.ITSO tiene un elemento por NOTTS (app.py::_write_inp5,
        # rama Block #13): el default de _default_data() trae NOTTS=1 /
        # ITSO=[1] consistentes entre sí; al subir NOTTS a 2 hay que ampliar
        # ITSO en el mismo patch o el inp.5 generado queda desincronizado.
        # Desde F8 este patch (blocks78 + block11.NOTTS + block13.ITSO) es
        # exactamente lo que produce buildTimePatches en el navegador (JS,
        # tools/test_sweep_utils.js) -- aquí se construye a mano porque este
        # test ejercita el camino de escritura del SERVIDOR, no el cálculo.
        patch = {'blocks78': blocks78, 'block11': {'NOTTS': 2}, 'block13': {'ITSO': [1, 1]}}

        # Camino "manual": generarB78() deja blocks78/NOTTS en appState.data
        # y el guardado pasa por _write_inp5 directamente.
        content_manual = appmod._write_inp5(deep_merge(self.data, patch))

        # Camino "barrido": una sola simulación temporal con el MISMO patch.
        root = self.tmp / 'time_out'
        historial_irr  = [{'t_fin': 10.0, 'pasos': 2}, {'t_fin': 20.0, 'pasos': 1}]
        historial_cool = [{'t_fin': 30.0, 'pasos': 2}]
        sims = [{
            'suffix': 'Tirr020.0h',
            'params': {
                't_irr_fin': 20.0, 't_cool_fin': 30.0,
                'historial_irr': historial_irr, 'historial_cool': historial_cool,
            },
            'patch': patch,
        }]
        r = self.client.post('/api/sweep', json={
            'root': str(root), 'base_folder': str(self.base), 'prefix': '',
            'description': 'barrido temporal multi-tramo', 'sweep_type': 'time',
            'fixed_params': {}, 'data': self.data, 'sims': sims})
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True))
        body = r.get_json()
        self.assertTrue(body['ok'])

        content_sweep = (root / 'Tirr020.0h' / 'inp.5').read_text(encoding='utf-8')
        self.assertEqual(content_manual, content_sweep,
                          'inp.5 del barrido debe ser BYTE-IDÉNTICO al del flujo manual')
        _roundtrip_check(content_sweep, ACABParser(), 'Tirr020.0h')

        manifest = json.loads((root / 'sweep_manifest.json').read_text(encoding='utf-8'))
        sim_params = manifest['simulations'][0]['params']
        self.assertEqual(sim_params['t_irr_fin'], 20.0,
                          'valor barrido (eje X del analyzer) sigue siendo t_irr_fin numérico')
        self.assertEqual(sim_params['historial_irr'], historial_irr)
        self.assertEqual(sim_params['historial_cool'], historial_cool)

        # El CSV del manifest es un entregable de trazabilidad: el historial
        # multi-tramo debe quedar como JSON válido en su celda, no como repr
        # de Python (_manifest_csv::_csv_cell).
        csv_txt = (root / 'sweep_manifest.csv').read_text(encoding='utf-8')
        rows = list(csv.reader(io.StringIO(csv_txt)))
        header, data_row = rows[0], rows[1]
        hist_irr_cell = data_row[header.index('historial_irr')]
        self.assertEqual(json.loads(hist_irr_cell), historial_irr)

    def test_preview(self):
        root = self.tmp / 'pv'
        r = self.client.post('/api/sweep/preview', json={
            'root': str(root), 'base_folder': str(self.base), 'prefix': 'P_',
            'sims': [{'suffix': 'a'}, {'suffix': 'b'}]})
        self.assertEqual(r.status_code, 200)
        b = r.get_json()
        self.assertTrue(b['base_exists'])
        self.assertTrue(b['base_has_inp5'])
        self.assertEqual(b['n'], 2)
        self.assertEqual(b['est_disk'], b['base_size'] * 2)
        self.assertEqual(b['collisions'], [])
        self.assertGreater(b['base_size'], 0)

    def test_collision_409(self):
        root = self.tmp / 'out2'
        (root / 'P_a').mkdir(parents=True)
        r = self.client.post('/api/sweep', json={
            'root': str(root), 'base_folder': str(self.base), 'prefix': 'P_',
            'description': 'd', 'data': self.data,
            'sims': [{'suffix': 'a', 'params': {}, 'patch': {}}]})
        self.assertEqual(r.status_code, 409)

    def test_overwrite_allows_existing(self):
        root = self.tmp / 'out2b'
        (root / 'P_a').mkdir(parents=True)
        r = self.client.post('/api/sweep', json={
            'root': str(root), 'base_folder': str(self.base), 'prefix': 'P_',
            'description': 'd', 'overwrite': True, 'data': self.data,
            'sims': [{'suffix': 'a', 'params': {}, 'patch': {}}]})
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True))

    def test_too_many_sims_422(self):
        root = self.tmp / 'out3'
        sims = [{'suffix': f's{i}', 'params': {}, 'patch': {}} for i in range(201)]
        r = self.client.post('/api/sweep', json={
            'root': str(root), 'base_folder': str(self.base), 'prefix': 'P_',
            'description': 'd', 'data': self.data, 'sims': sims})
        self.assertEqual(r.status_code, 422)

    def test_duplicate_suffix_422(self):
        root = self.tmp / 'out4'
        sims = [{'suffix': 'a', 'params': {}, 'patch': {}},
                {'suffix': 'a', 'params': {}, 'patch': {}}]
        r = self.client.post('/api/sweep', json={
            'root': str(root), 'base_folder': str(self.base), 'prefix': 'P_',
            'description': 'd', 'data': self.data, 'sims': sims})
        self.assertEqual(r.status_code, 422)

    def test_empty_description_422(self):
        root = self.tmp / 'out5'
        r = self.client.post('/api/sweep', json={
            'root': str(root), 'base_folder': str(self.base), 'prefix': 'P_',
            'description': '   ', 'data': self.data,
            'sims': [{'suffix': 'a', 'params': {}, 'patch': {}}]})
        self.assertEqual(r.status_code, 422)

    def test_abort_and_cleanup_on_bad_patch(self):
        root = self.tmp / 'out6'
        sims = [
            {'suffix': 'good', 'params': {}, 'patch': {}},
            # XCOMP vacío ⇒ el writer falla ⇒ aborta y limpia todo el barrido
            {'suffix': 'bad', 'params': {},
             'patch': {'block5': [{'INUCL': [10000], 'XCOMP': []}]}},
        ]
        r = self.client.post('/api/sweep', json={
            'root': str(root), 'base_folder': str(self.base), 'prefix': 'P_',
            'description': 'd', 'data': self.data, 'sims': sims})
        self.assertEqual(r.status_code, 422)
        self.assertFalse((root / 'P_good').exists(), 'limpió la sim ya escrita')
        self.assertFalse((root / 'P_bad').exists())
        self.assertFalse((root / 'sweep_manifest.json').exists())

    def test_roundtrip_check_rejects_garbage(self):
        with self.assertRaises(SweepError):
            _roundtrip_check('esto no es un fichero ACAB valido', ACABParser(), 'g')


class SpectralSweepTests(unittest.TestCase):
    """coll_patch (D9, RUNBOOK_barrido_espectral.md Fase P2)."""

    def setUp(self):
        self.client = appmod.app.test_client()
        self.tmp = Path(tempfile.mkdtemp())
        self.base = self.tmp / 'base'
        self.base.mkdir(parents=True)
        (self.base / 'inp.5').write_text('OLD BASE INP', encoding='utf-8')
        self.data = appmod._default_data()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _spectrum_sims(self):
        return [
            {'suffix': 'MURR', 'params': {'espectro': 'MURR-G1'},
             'coll_patch': {'ngroup': -3, 'cx': [20.0, 10.0, 1.0, 0.1],
                            'ft': [1.1e10, 2.2e10, 3.3e10]}},
            {'suffix': 'TRIGA', 'params': {'espectro': 'TRIGA'},
             'coll_patch': {'ngroup': -2, 'cx': [20.0, 5.0, 0.5],
                            'ft': [4.4e10, 5.5e10]}},
        ]

    def test_missing_collaps_coll_inp_422(self):
        # La base no tiene 'collaps/COLL.inp' -> 422 claro (D9)
        root = self.tmp / 'out_spec1'
        r = self.client.post('/api/sweep', json={
            'root': str(root), 'base_folder': str(self.base), 'prefix': 'S_',
            'description': 'barrido espectral sin base collaps', 'sweep_type': 'spectrum',
            'data': self.data, 'sims': self._spectrum_sims()})
        self.assertEqual(r.status_code, 422)
        body = r.get_json()
        self.assertIn('collaps/COLL.inp', body['error'])
        self.assertFalse(root.exists())

    def test_happy_path_writes_coll_inp_per_sim(self):
        collaps_dir = self.base / 'collaps'
        collaps_dir.mkdir()
        shutil.copy(FIXTURE_COLL_211, collaps_dir / 'COLL.inp')

        root = self.tmp / 'out_spec2'
        r = self.client.post('/api/sweep', json={
            'root': str(root), 'base_folder': str(self.base), 'prefix': 'S_',
            'description': 'barrido espectral de prueba', 'sweep_type': 'spectrum',
            'fixed_params': {'phi_ref': '6.5E+13'},
            'data': self.data, 'sims': self._spectrum_sims()})
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True))
        body = r.get_json()
        self.assertTrue(body['ok'])
        self.assertEqual(body['n_written'], 2)

        for suf, ngroup, ncx, nft in [('MURR', -3, 4, 3), ('TRIGA', -2, 3, 2)]:
            coll_path = root / f'S_{suf}' / 'collaps' / 'COLL.inp'
            self.assertTrue(coll_path.is_file(), f'{coll_path} no se generó')
            parsed = read_coll_inp(coll_path)
            self.assertEqual(parsed['card1']['IESF'], 5, 'coll_patch con cx fuerza IESF=5')
            self.assertEqual(parsed['card5']['NGROUP'], ngroup)
            self.assertEqual(len(parsed['card6']['CX']), ncx)
            self.assertEqual(len(parsed['card7']['FT']), nft)
            # inp.5 de la sim también se generó con normalidad (independiente del COLL.inp)
            self.assertTrue((root / f'S_{suf}' / 'inp.5').is_file())

    def test_bad_coll_patch_aborts_and_cleans_up(self):
        collaps_dir = self.base / 'collaps'
        collaps_dir.mkdir()
        shutil.copy(FIXTURE_COLL_211, collaps_dir / 'COLL.inp')

        root = self.tmp / 'out_spec3'
        sims = [
            {'suffix': 'good', 'params': {},
             'coll_patch': {'ngroup': -2, 'cx': [20.0, 1.0, 0.1], 'ft': [1.0, 2.0]}},
            # FT con longitud incoherente con NGROUP -> apply_spectrum_patch falla
            {'suffix': 'bad', 'params': {},
             'coll_patch': {'ngroup': -2, 'cx': [20.0, 1.0, 0.1], 'ft': [1.0]}},
        ]
        r = self.client.post('/api/sweep', json={
            'root': str(root), 'base_folder': str(self.base), 'prefix': 'S_',
            'description': 'd', 'data': self.data, 'sims': sims})
        self.assertEqual(r.status_code, 422)
        self.assertFalse((root / 'S_good').exists(), 'limpió la sim ya escrita')
        self.assertFalse((root / 'S_bad').exists())
        self.assertFalse((root / 'sweep_manifest.json').exists())


class BaseFolderExclusionTests(unittest.TestCase):
    """C4 del BACKLOG: exclusión de salidas viejas al copiar la carpeta base
    (asimetría espectral vs flujo/masa/temporal) -- caso oro con una carpeta
    base sembrada de salidas falsas reconocibles ('STALE')."""

    def setUp(self):
        self.client = appmod.app.test_client()
        self.tmp = Path(tempfile.mkdtemp())
        self.data = appmod._default_data()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _seed_acab_outputs(self, base: Path):
        (base / 'inp.5').write_text('OLD BASE INP', encoding='utf-8')
        (base / 'acab.exe').write_text('fake exe', encoding='utf-8')
        (base / 'DECAY.dat').write_text('decay data', encoding='utf-8')
        (base / 'fort.6').write_text('STALE_ACAB_OUTPUT', encoding='utf-8')
        (base / 'run.log').write_text('STALE_ACAB_OUTPUT', encoding='utf-8')
        (base / 'cpu_time.txt').write_text('STALE_ACAB_OUTPUT', encoding='utf-8')

    def test_spectrum_sweep_excludes_acab_and_collaps_outputs(self):
        base = self.tmp / 'base_spec'
        base.mkdir(parents=True)
        self._seed_acab_outputs(base)
        # XSECTION.dat top-level: copia residual de una ejecución previa de
        # la propia base (entrada de ACAB, pero regenerada por sim en el
        # barrido espectral -> también es salida vieja aquí).
        (base / 'XSECTION.dat').write_text('STALE_COLLAPS_OUTPUT', encoding='utf-8')
        coll = base / 'collaps'
        coll.mkdir()
        (coll / 'COLL.inp').write_text('coll base', encoding='utf-8')
        for name in ('XSECTION.dat', 'FLUX.inf', 'XS.inf', 'REACTIONS.dat', 'XSZERO.dat'):
            (coll / name).write_text('STALE_COLLAPS_OUTPUT', encoding='utf-8')

        root = self.tmp / 'out_spec'
        r = self.client.post('/api/sweep', json={
            'root': str(root), 'base_folder': str(base), 'prefix': 'P_',
            'description': 'barrido espectral - exclusion C4', 'sweep_type': 'spectrum',
            'data': self.data, 'sims': [{'suffix': 's1', 'params': {}, 'patch': {}}]})
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True))

        sim_dir = root / 'P_s1'
        stale_rel_paths = ('fort.6', 'run.log', 'cpu_time.txt', 'XSECTION.dat',
                            'collaps/XSECTION.dat', 'collaps/FLUX.inf',
                            'collaps/XS.inf', 'collaps/REACTIONS.dat',
                            'collaps/XSZERO.dat')
        for rel in stale_rel_paths:
            self.assertFalse((sim_dir / rel).exists(),
                              f'{rel} no debería copiarse en un barrido espectral')
        # Lo que no es salida sobrevive (entradas, ejecutable, COLL.inp base).
        self.assertTrue((sim_dir / 'acab.exe').exists())
        self.assertTrue((sim_dir / 'DECAY.dat').exists())
        self.assertTrue((sim_dir / 'collaps' / 'COLL.inp').exists())

        manifest = json.loads((root / 'sweep_manifest.json').read_text(encoding='utf-8'))
        excluded = set(manifest['excluded_base_files'])
        self.assertEqual(excluded, {
            'fort.6', 'run.log', 'cpu_time.txt', 'XSECTION.dat',
            'collaps/XSECTION.dat', 'collaps/FLUX.inf', 'collaps/XS.inf',
            'collaps/REACTIONS.dat', 'collaps/XSZERO.dat',
        })

    def test_flux_sweep_keeps_shared_spectrum_but_drops_acab_outputs(self):
        base = self.tmp / 'base_flux'
        base.mkdir(parents=True)
        self._seed_acab_outputs(base)
        # XSECTION.dat/FLUX.inf: espectro compartido a propósito por todas
        # las sims del barrido de flujo -- deben sobrevivir IDÉNTICOS.
        (base / 'XSECTION.dat').write_text('SHARED_SPECTRUM_DATA', encoding='utf-8')
        (base / 'FLUX.inf').write_text('SHARED_SPECTRUM_DATA', encoding='utf-8')

        root = self.tmp / 'out_flux'
        sims = [{'suffix': 'x1', 'params': {'XNORM': 1.0},
                 'patch': {'block9': {'XNORM': 1.0}}}]
        r = self.client.post('/api/sweep', json={
            'root': str(root), 'base_folder': str(base), 'prefix': 'P_',
            'description': 'barrido de flujo - exclusion C4', 'sweep_type': 'flux',
            'data': self.data, 'sims': sims})
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True))

        sim_dir = root / 'P_x1'
        self.assertFalse((sim_dir / 'fort.6').exists())
        self.assertFalse((sim_dir / 'run.log').exists())
        self.assertFalse((sim_dir / 'cpu_time.txt').exists())
        self.assertEqual((sim_dir / 'XSECTION.dat').read_text(encoding='utf-8'),
                          'SHARED_SPECTRUM_DATA')
        self.assertEqual((sim_dir / 'FLUX.inf').read_text(encoding='utf-8'),
                          'SHARED_SPECTRUM_DATA')

        manifest = json.loads((root / 'sweep_manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(set(manifest['excluded_base_files']),
                          {'fort.6', 'run.log', 'cpu_time.txt'})


if __name__ == '__main__':
    unittest.main(verbosity=2)
