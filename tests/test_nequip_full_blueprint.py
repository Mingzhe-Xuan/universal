"""Metadata conversion for original per-angular-order NequIP architecture; no Torch."""

import copy
import unittest

from universal_gnn.backbones.blueprints import nequip_full_constructor_config
from test_fresh_blueprints import blueprint, statistics


def layout():
    return dict(irreps_edge_sh="1x0e + 1x1e", type_embed_num_features=32,
                feature_irreps_hidden=["128x0e + 64x1e", "128x0e"])


def author():
    value=blueprint()
    value['training_module']['model']['model'].update(type_embed_num_features=32,radial_mlp_depth=1,radial_mlp_width=128)
    return value


class NequIPFullBlueprintTests(unittest.TestCase):
    def test_expands_original_angular_widths_and_keeps_independent_embedding(self):
        source,original=author(),layout();before=copy.deepcopy((source,original))
        config,report=nequip_full_constructor_config(source,statistics('nequip',4.5),seed=456,layout=original)
        self.assertEqual((source,original),before)
        self.assertEqual(config['feature_irreps_hidden'],['128x0e + 64x1e','128x0e'])
        self.assertEqual(config['type_embed_num_features'],32)
        self.assertEqual(config['radial_mlp_depth'],[1,1]);self.assertEqual(config['radial_mlp_width'],[128,128])
        for name in ['num_features','num_layers','l_max','parity']:self.assertNotIn(name,config)
        self.assertEqual(report['constructor'],'nequip.model.FullNequIPGNNModel')
        self.assertEqual(report['source_constructor'],'nequip.model.NequIPGNNModel')
        self.assertEqual(report['width_interpretation'],'per_angular_order')

    def test_only_seed_and_fitted_statistics_change_beyond_explicit_architecture(self):
        source=author();recipe=source['training_module']['model']['model']
        config,report=nequip_full_constructor_config(source,statistics('nequip',4.5),seed=789,layout=layout())
        self.assertEqual(config['seed'],789);self.assertEqual(config['compile_mode'],'eager')
        self.assertEqual(config['avg_num_neighbors'],3.)
        self.assertEqual(config['per_type_energy_shifts'],{'H':0.,'O':0.});self.assertEqual(config['per_type_energy_scales'],[1.,1.])
        for key in ['type_names','r_max','per_type_energy_shifts_trainable','per_type_energy_scales_trainable','pair_potential']:
            self.assertEqual(config[key],recipe[key])
        config['pair_potential']['units']='changed'
        self.assertEqual(recipe['pair_potential']['units'],'metal')
        self.assertEqual(report['skipped_nonpersistent_modifiers_for_eager'],['enable_OpenEquivariance'])

    def test_rejects_per_layer_misinterpretation_and_incomplete_layout(self):
        variants=[]
        for key,value in [('feature_irreps_hidden',['128x0e + 64x1e','64x0e']),
                          ('feature_irreps_hidden',['128x0e']),('irreps_edge_sh','1x0e + 1x1o'),
                          ('type_embed_num_features',128),('feature_irreps_hidden',['128x0e + 64x1o','128x0e'])]:
            variants.append({**layout(),key:value})
        variants.extend([None,{},dict(layout(),unknown=True)])
        for value in variants:
            with self.subTest(layout=value),self.assertRaises(ValueError):
                nequip_full_constructor_config(author(),statistics('nequip',4.5),seed=123,layout=value)

    def test_rejects_invalid_irreps_types_and_blueprint_layer_settings(self):
        for value in ['128x0e + 0x1e','128x0e + -1x1e','128x0e + 64x1z',None]:
            bad=layout();bad['feature_irreps_hidden'][0]=value
            with self.subTest(irrep=value),self.assertRaises(ValueError):
                nequip_full_constructor_config(author(),statistics('nequip',4.5),seed=123,layout=bad)
        for key,value in [('num_layers',True),('l_max',-1),('parity',1),('num_features',[128]),
                          ('num_features',[128,False]),('radial_mlp_depth',[1]),('radial_mlp_width',0)]:
            source=author();source['training_module']['model']['model'][key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):
                nequip_full_constructor_config(source,statistics('nequip',4.5),seed=123,layout=layout())

    def test_scalar_width_parity_and_multiple_layers_expand_consistently(self):
        source=author();recipe=source['training_module']['model']['model']
        recipe.update(num_layers=3,num_features=16,parity=True)
        original=dict(irreps_edge_sh='1x0e + 1x1o',type_embed_num_features=32,
                      feature_irreps_hidden=['16x0e + 16x1e + 16x0o + 16x1o']*2+['16x0e'])
        config,_=nequip_full_constructor_config(source,statistics('nequip',4.5),seed=123,layout=original)
        self.assertEqual(config['radial_mlp_width'],[128]*3)
        self.assertEqual(config['feature_irreps_hidden'],original['feature_irreps_hidden'])


if __name__=='__main__':unittest.main()
