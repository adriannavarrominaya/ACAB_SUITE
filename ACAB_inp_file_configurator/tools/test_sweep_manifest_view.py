"""Tests de la vista de solo lectura de un barrido generado (U6 del BACKLOG).

    C:\\venv\\acab-venv\\Scripts\\python.exe tools/test_sweep_manifest_view.py

Cubre: parseo de sweep_manifest.json de los 4 tipos de barrido (casos oro
congelados, incluido uno PRE-C4 sin `excluded_base_files`), manifest
corrupto/ausente (nunca traza cruda), con/sin batch_results.json, y el
endpoint /api/sweep/manifest (404/422/200).
"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app as appmod                                          # noqa: E402
from sweep_manifest_view import (                             # noqa: E402
    ManifestCorruptError, build_manifest_view,
)


def _write_manifest(root: Path, manifest: dict) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / 'sweep_manifest.json').write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')


# ── Casos oro: un manifest congelado por tipo de barrido ────────────────────

FLUX_MANIFEST = {
    'timestamp': '2026-07-01T10:00:00+00:00', 'sweep_type': 'flux',
    'description': 'barrido de flujo TeO2', 'fixed_params': {'masa': '0.1231 g'},
    'n': 2,
    'simulations': [
        {'folder': 'TeO2_x0.5', 'params': {'XNORM': 0.5}},
        {'folder': 'TeO2_x1.0', 'params': {'XNORM': 1.0}},
    ],
    'excluded_base_files': ['fort.6', 'run.log'],
}

MASS_MANIFEST = {
    'timestamp': '2026-07-01T10:00:00+00:00', 'sweep_type': 'mass',
    'description': 'barrido de masa', 'fixed_params': {'formula': 'TeO2'},
    'n': 1,
    'simulations': [{'folder': 'M_1.500g', 'params': {'mass': 1.5}}],
    'excluded_base_files': ['fort.6'],
}

TIME_MANIFEST = {
    'timestamp': '2026-07-01T10:00:00+00:00', 'sweep_type': 'time',
    'description': 'barrido temporal', 'fixed_params': {},
    'n': 1,
    'simulations': [{'folder': 'Tirr024.0h',
                      'params': {'t_irr_fin': 24, 'pasos_irr': 7,
                                 't_cool_fin': 4.5, 'pasos_cool': 5}}],
    'excluded_base_files': ['fort.6'],
}

SPECTRUM_MANIFEST = {
    'timestamp': '2026-07-01T10:00:00+00:00', 'sweep_type': 'spectrum',
    'description': 'barrido espectral - 9 reactores', 'fixed_params': {'phi_ref': '6.5E+13'},
    'n': 2,
    'simulations': [
        {'folder': 'S_MURR', 'params': {'espectro': 'MURR-G1', 'n_grupos': 112,
                                          'frac_termica': 0.32, 'frac_epitermica': 0.21,
                                          'frac_rapida': 0.47}},
        {'folder': 'S_TRIGA', 'params': {'espectro': 'TRIGA', 'n_grupos': 47,
                                           'frac_termica': 0.5, 'frac_epitermica': 0.3,
                                           'frac_rapida': 0.2}},
    ],
    'excluded_base_files': ['fort.6', 'collaps/XSECTION.dat', 'collaps/FLUX.inf'],
}

# Caso oro U7: manifest NUEVO (historial multi-tramo en params, junto a los
# escalares t_irr_fin/t_cool_fin de siempre) -- prueba que sweep_manifest_view
# no necesita cambios: _sim_value_label solo lee los escalares, las claves
# nuevas (arrays) se ignoran sin romper nada.
TIME_MANIFEST_MULTI_TRAMO = {
    'timestamp': '2026-07-22T10:00:00+00:00', 'sweep_type': 'time',
    'description': 'barrido temporal multi-tramo (U7)', 'fixed_params': {},
    'n': 1,
    'simulations': [{'folder': 'Tirr040.0h',
                      'params': {
                          't_irr_fin': 40, 't_cool_fin': 168,
                          'historial_irr': [{'t_fin': 10, 'pasos': 5}, {'t_fin': 40, 'pasos': 8}],
                          'historial_cool': [{'t_fin': 20, 'pasos': 4}, {'t_fin': 168, 'pasos': 6}],
                      }}],
    'excluded_base_files': ['fort.6'],
}

# Caso oro PRE-C4: sin la clave 'excluded_base_files' (trampa principal de U6).
PRE_C4_MANIFEST = {
    'timestamp': '2026-06-01T10:00:00+00:00', 'sweep_type': 'flux',
    'description': 'barrido histórico pre-C4', 'fixed_params': {'masa': '0.1 g'},
    'n': 1,
    'simulations': [{'folder': 'old_x1.0', 'params': {'XNORM': 1.0}}],
}


class BuildManifestViewGoldenTests(unittest.TestCase):
    """Parseo de los 4 tipos de barrido, con casos oro congelados."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_flux(self):
        root = self.tmp / 'flux'
        _write_manifest(root, FLUX_MANIFEST)
        for sim in FLUX_MANIFEST['simulations']:
            (root / sim['folder']).mkdir(parents=True)
        (root / 'TeO2_x1.0' / 'fort.6').write_text('salida', encoding='utf-8')

        view = build_manifest_view(root)
        self.assertEqual(view['sweep_type'], 'flux')
        self.assertEqual(view['excluded_base_files'], ['fort.6', 'run.log'])
        sims = {s['folder']: s for s in view['simulations']}
        self.assertEqual(sims['TeO2_x0.5']['value_label'], 'XNORM=0.5')
        self.assertFalse(sims['TeO2_x0.5']['fort6_exists'])
        self.assertTrue(sims['TeO2_x1.0']['fort6_exists'])
        self.assertFalse(view['has_batch_results'])
        self.assertIsNone(view['batch_summary'])
        self.assertIsNone(sims['TeO2_x0.5']['estado'])

    def test_mass(self):
        root = self.tmp / 'mass'
        _write_manifest(root, MASS_MANIFEST)
        view = build_manifest_view(root)
        self.assertEqual(view['sweep_type'], 'mass')
        self.assertEqual(view['simulations'][0]['value_label'], '1.5 g')

    def test_time(self):
        root = self.tmp / 'time'
        _write_manifest(root, TIME_MANIFEST)
        view = build_manifest_view(root)
        self.assertEqual(view['sweep_type'], 'time')
        self.assertEqual(view['simulations'][0]['value_label'],
                          'T_irr=24h, T_cool=4.5h')

    def test_time_multi_tramo_manifest_new_shape_unaffected(self):
        """U7: un manifest NUEVO (con historial_irr/historial_cool) da el
        mismo value_label que la forma plana vieja -- sweep_manifest_view no
        necesita cambios, las claves nuevas se ignoran sin romper nada."""
        root = self.tmp / 'time_multi'
        _write_manifest(root, TIME_MANIFEST_MULTI_TRAMO)
        view = build_manifest_view(root)
        self.assertEqual(view['sweep_type'], 'time')
        self.assertEqual(view['simulations'][0]['value_label'],
                          'T_irr=40h, T_cool=168h')

    def test_spectrum_uses_spectrum_name_never_param_dump(self):
        root = self.tmp / 'spectrum'
        _write_manifest(root, SPECTRUM_MANIFEST)
        view = build_manifest_view(root)
        self.assertEqual(view['sweep_type'], 'spectrum')
        sims = {s['folder']: s for s in view['simulations']}
        self.assertEqual(sims['S_MURR']['value_label'], 'MURR-G1')
        self.assertEqual(sims['S_TRIGA']['value_label'], 'TRIGA')
        # Nunca un volcado de parámetros (n_grupos/frac_*) como identificador.
        for s in view['simulations']:
            self.assertNotIn('=', s['value_label'].replace('MURR-G1', '').replace('TRIGA', ''))

    def test_pre_c4_manifest_tolerates_missing_excluded_base_files(self):
        root = self.tmp / 'pre_c4'
        _write_manifest(root, PRE_C4_MANIFEST)
        view = build_manifest_view(root)
        self.assertEqual(view['sweep_type'], 'flux')
        self.assertEqual(view['excluded_base_files'], [])  # nunca rompe, degrada a []
        self.assertEqual(view['simulations'][0]['value_label'], 'XNORM=1.0')

    def test_unknown_sweep_type_falls_back_to_none_label(self):
        root = self.tmp / 'unknown'
        manifest = dict(FLUX_MANIFEST)
        manifest['sweep_type'] = ''
        manifest['simulations'] = [{'folder': 'x', 'params': {'foo': 1}}]
        _write_manifest(root, manifest)
        view = build_manifest_view(root)
        self.assertIsNone(view['simulations'][0]['value_label'])  # el llamador cae a 'folder'


class BuildManifestViewErrorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_missing_manifest_raises_file_not_found(self):
        root = self.tmp / 'empty'
        root.mkdir()
        with self.assertRaises(FileNotFoundError):
            build_manifest_view(root)

    def test_corrupt_json_raises_manifest_corrupt_error(self):
        root = self.tmp / 'corrupt'
        root.mkdir()
        (root / 'sweep_manifest.json').write_text('{ esto no es json ][', encoding='utf-8')
        with self.assertRaises(ManifestCorruptError):
            build_manifest_view(root)


class BatchResultsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_with_batch_results_maps_estado_per_folder(self):
        root = self.tmp / 'batch'
        _write_manifest(root, FLUX_MANIFEST)
        for sim in FLUX_MANIFEST['simulations']:
            (root / sim['folder']).mkdir(parents=True)
        batch = {
            'resumen': {'total': 2, 'ok': 1, 'fallos': 1, 'canceladas': 0},
            'jobs': [
                {'workdir': str(root / 'TeO2_x0.5'), 'estado': 'ok'},
                {'workdir': str(root / 'TeO2_x1.0'), 'estado': 'failed'},
            ],
        }
        (root / 'batch_results.json').write_text(json.dumps(batch), encoding='utf-8')

        view = build_manifest_view(root)
        self.assertTrue(view['has_batch_results'])
        self.assertEqual(view['batch_summary']['ok'], 1)
        sims = {s['folder']: s for s in view['simulations']}
        self.assertEqual(sims['TeO2_x0.5']['estado'], 'ok')
        self.assertEqual(sims['TeO2_x1.0']['estado'], 'failed')

    def test_corrupt_batch_results_ignored_not_fatal(self):
        root = self.tmp / 'batch_corrupt'
        _write_manifest(root, FLUX_MANIFEST)
        (root / 'batch_results.json').write_text('{ no valido', encoding='utf-8')
        view = build_manifest_view(root)  # no debe lanzar
        self.assertFalse(view['has_batch_results'])
        self.assertIsNone(view['simulations'][0]['estado'])


class SweepManifestEndpointTests(unittest.TestCase):
    def setUp(self):
        self.client = appmod.app.test_client()
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_missing_root_422(self):
        r = self.client.get('/api/sweep/manifest', query_string={'root': ''})
        self.assertEqual(r.status_code, 422)

    def test_nonexistent_folder_422(self):
        r = self.client.get('/api/sweep/manifest',
                             query_string={'root': str(self.tmp / 'no_existe')})
        self.assertEqual(r.status_code, 422)

    def test_folder_without_manifest_404(self):
        root = self.tmp / 'sin_manifest'
        root.mkdir()
        r = self.client.get('/api/sweep/manifest', query_string={'root': str(root)})
        self.assertEqual(r.status_code, 404)
        body = r.get_json()
        self.assertFalse(body['ok'])
        self.assertIn('sweep_manifest.json', body['error'])

    def test_corrupt_manifest_422_no_raw_traceback(self):
        root = self.tmp / 'corrupto'
        root.mkdir()
        (root / 'sweep_manifest.json').write_text('{ mal ][', encoding='utf-8')
        r = self.client.get('/api/sweep/manifest', query_string={'root': str(root)})
        self.assertEqual(r.status_code, 422)
        body = r.get_json()
        self.assertNotIn('Traceback', body['error'])

    def test_happy_path_200(self):
        root = self.tmp / 'ok'
        _write_manifest(root, SPECTRUM_MANIFEST)
        r = self.client.get('/api/sweep/manifest', query_string={'root': str(root)})
        self.assertEqual(r.status_code, 200)
        body = r.get_json()
        self.assertTrue(body['ok'])
        self.assertEqual(body['sweep_type'], 'spectrum')
        self.assertEqual(len(body['simulations']), 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
