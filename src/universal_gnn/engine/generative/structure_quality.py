"""Geometric and structural metrics for standard records, independent of a GNN runtime."""

from collections import Counter, defaultdict
import math

from .protocol import wasserstein_1d


def composition(numbers):
    return tuple(sorted(Counter(int(number) for number in numbers).items()))

class StructuralQuality:
    def __init__(self, training, *, distance_threshold=.5, record=None):
        from pymatgen.analysis.structure_matcher import ElementComparator, StructureMatcher

        if (isinstance(distance_threshold, bool) or not isinstance(distance_threshold, (float, int)) or
                not math.isfinite(distance_threshold) or distance_threshold <= 0):
            raise ValueError("Geometric distance threshold must be finite and positive")
        self.training, self.distance_threshold = training, distance_threshold
        self.record = record or (lambda value: value)
        self.matcher = StructureMatcher(ltol=.3, stol=.5, angle_tol=10., primitive_cell=False,
                                        scale=True, attempt_supercell=False, comparator=ElementComparator())
        self.training_by_composition, self.unique = defaultdict(list), defaultdict(list)
        for index in range(len(training)):
            self.training_by_composition[composition(self.record(training[index])["numbers"])].append(index)
        self.attempted = self.valid = self.novel = self.matched = 0
        self.seen_composition_valid = self.seen_composition_novel = 0
        self.valid_composition_counts = Counter()
        self.generated_distributions = {"volume_per_atom_angstrom3": [], "density_g_cm3": []}
        self.reference_distributions = {name: [] for name in self.generated_distributions}
        self.matched_rms = []

    @staticmethod
    def pmg(record):
        from pymatgen.core import Structure

        return Structure(record["cell"], record["numbers"], record["positions"], coords_are_cartesian=True)

    def update(self, generated, reference, *, failure=None):
        import numpy as np
        from ase import Atoms
        from ase.neighborlist import neighbor_list

        self.attempted += 1
        expected = self.pmg(reference)
        self.reference_distributions["volume_per_atom_angstrom3"].append(float(expected.volume / len(expected)))
        self.reference_distributions["density_g_cm3"].append(float(expected.density))
        result = {"geometrically_valid": False, "reason": failure, "unique": None, "novel_to_train": None,
                  "matches_assigned_reference": False, "normalized_rms": None}
        if generated is None:
            return result
        if composition(generated["numbers"]) != composition(reference["numbers"]):
            raise ValueError("Generated composition/atom count differs from its declared condition")
        positions, cell = np.asarray(generated["positions"], dtype=float), np.asarray(generated["cell"], dtype=float)
        if (positions.shape != (len(generated["numbers"]), 3) or cell.shape != (3, 3) or
                not np.isfinite(positions).all() or not np.isfinite(cell).all() or
                not np.linalg.det(cell) > 1e-9 or generated["pbc"] != [True, True, True]):
            result["reason"] = "nonfinite_singular_or_nonperiodic_geometry"
            return result
        fractional = np.linalg.solve(cell.T, positions.T).T
        if not ((fractional >= -1e-6).all() and (fractional < 1. + 1e-6).all()):
            result["reason"] = "fractional_coordinates_outside_unit_cell"
            return result
        atoms = Atoms(numbers=generated["numbers"], positions=positions, cell=cell, pbc=True)
        if len(neighbor_list("d", atoms, self.distance_threshold, self_interaction=False)):
            result["reason"] = "periodic_distance_below_threshold"
            return result
        actual = self.pmg(generated)
        key = composition(generated["numbers"])
        unique = not any(self.matcher.fit(actual, other, symmetric=True) for other in self.unique[key])
        if unique:
            self.unique[key].append(actual)
        novel = not any(self.matcher.fit(actual, self.pmg(self.record(self.training[index])), symmetric=True)
                        for index in self.training_by_composition.get(key, []))
        matched = self.matcher.fit(actual, expected, symmetric=True)
        rms = self.matcher.get_rms_dist(actual, expected) if matched else None
        if rms is not None:
            self.matched_rms.append(float(rms[0]))
        self.valid += 1
        self.novel += int(novel)
        self.matched += int(matched)
        self.valid_composition_counts[key] += 1
        if key in self.training_by_composition:
            self.seen_composition_valid += 1
            self.seen_composition_novel += int(novel)
        self.generated_distributions["volume_per_atom_angstrom3"].append(float(actual.volume / len(actual)))
        self.generated_distributions["density_g_cm3"].append(float(actual.density))
        result.update(geometrically_valid=True, reason=None, unique=unique, novel_to_train=novel,
                      matches_assigned_reference=matched, normalized_rms=float(rms[0]) if rms is not None else None)
        return result

    def result(self):
        if not self.attempted:
            raise ValueError("No generated conditions were evaluated")
        unique = sum(len(values) for values in self.unique.values())
        return {"attempted": self.attempted, "geometrically_valid": self.valid,
                "geometric_validity": self.valid / self.attempted,
                "unique_valid_structures": unique, "uniqueness_among_valid": unique / self.valid if self.valid else None,
                "novel_valid_structures": self.novel, "novelty_among_valid": self.novel / self.valid if self.valid else None,
                "valid_samples_with_training_seen_composition": self.seen_composition_valid,
                "novelty_among_valid_with_training_seen_composition": self.seen_composition_novel / self.seen_composition_valid
                    if self.seen_composition_valid else None,
                "valid_composition_groups": len(self.valid_composition_counts),
                "valid_samples_with_repeated_generated_composition": sum(n for n in self.valid_composition_counts.values() if n > 1),
                "novelty_scope": "unseen training compositions are automatically novel; seen-composition novelty is reported separately",
                "matched_assigned_references": self.matched, "paired_match_rate": self.matched / self.attempted,
                "paired_match_rate_among_valid": self.matched / self.valid if self.valid else None,
                "mean_normalized_rms_among_matches": sum(self.matched_rms) / len(self.matched_rms) if self.matched_rms else None,
                "distribution_wasserstein_1": {name: wasserstein_1d(values, self.reference_distributions[name])
                                                if values else None for name, values in self.generated_distributions.items()},
                "distribution_reference": "all selected assigned test references; generated distribution includes valid samples only",
                "geometry_definition": {"three_dimensional_pbc": True, "positive_volume": True,
                                        "fractional_coordinates_in_unit_cell": True,
                                        "minimum_periodic_distance_angstrom": self.distance_threshold},
                "matching": {"implementation": "pymatgen.StructureMatcher", "ltol": .3, "stol": .5, "angle_tol": 10.,
                             "primitive_cell": False, "scale": True, "attempt_supercell": False, "symmetric": True,
                             "comparator": "ElementComparator", "rms_unit": "normalized by (V/N)^(1/3)"},
                "interpretation": "conditional geometric/structural quality; no chemical or thermodynamic stability claim"}
