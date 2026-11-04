"""Higher precision energy references without changing the live task model."""
import copy

import torch


NEQUIP_EMBEDDINGS = {'BesselEdgeLengthEncoding', 'SphericalHarmonicEdgeAttrs', 'AddRadialCutoffToData'}


def energy_difference_reference(energy_model):
    if next(energy_model.parameters()).dtype == torch.float64:
        return energy_model, []
    reference = copy.deepcopy(energy_model).double().eval()
    backbone = getattr(reference, 'backbone', None)
    adjustments = []
    if getattr(backbone, 'official_artifact', {}).get('provider') == 'nequip':
        # NequIP eager embeddings explicitly cast outputs using a plain dtype
        # attribute, which Module.double() cannot update along with parameters.
        for path, module in backbone.model.named_modules():
            if type(module).__name__ not in NEQUIP_EMBEDDINGS:
                continue
            before = getattr(module, '_output_dtype', None)
            if before not in {torch.float32, torch.float64}:
                raise ValueError('Unsupported NequIP reference output dtype at '+path)
            module._output_dtype = torch.float64
            adjustments.append(dict(path=path, class_name=type(module).__name__,
                                    before=str(before), after=str(module._output_dtype)))
    return reference, adjustments
