"""Slurm-only native constructor/RNG/state acceptance, separate from task benchmarks."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if not os.environ.get('SLURM_JOB_ID'):
        parser.error('Actual official-model validation must execute through Slurm')
    subprocess.run([sys.executable,'-m','pip','check'],check=True)
    import torch
    from universal_gnn.backbones.factory import make_backbone

    if args.output.exists():
        raise FileExistsError('Acceptance output must be fresh')
    args.output.mkdir(parents=True)
    torch.set_default_dtype(torch.float32)

    def construct(name,mode,seed,artifact=None):
        torch.manual_seed(seed)
        options={'initialization':mode,'implementation':'official'}
        if artifact is not None:options['_artifact']=artifact
        model=make_backbone(name,**options)
        return model,torch.rand(4)

    def digest(model):
        value=hashlib.sha256()
        for key,tensor in sorted(model.state_dict().items()):
            value.update(key.encode())
            value.update(str((tensor.dtype,tuple(tensor.shape))).encode())
            value.update(tensor.detach().cpu().contiguous().numpy().tobytes())
        return value.hexdigest()

    results=[]
    for name in ('cgcnn','alignn'):
        pretrained,rng_original=construct(name,'pretrained',29)
        fresh,rng_fresh=construct(name,'scratch',29)
        again,_=construct(name,'scratch',29)
        different,_=construct(name,'scratch',31)
        expected={key:tuple(tensor.shape) for key,tensor in pretrained.state_dict().items()}
        assert {key:tuple(tensor.shape) for key,tensor in fresh.state_dict().items()}==expected
        assert fresh.feature_irreps==pretrained.feature_irreps
        assert {key:type(module) for key,module in fresh.model.named_modules()}=={
                key:type(module) for key,module in pretrained.model.named_modules()}
        assert torch.equal(rng_original,rng_fresh),'Head initialization RNG must match for the same upstream constructor'
        hashes={key:digest(value) for key,value in (('pretrained',pretrained),('fresh',fresh),('again',again),('different_seed',different))}
        assert hashes['fresh']==hashes['again']
        assert hashes['fresh']!=hashes['pretrained'] and hashes['fresh']!=hashes['different_seed']
        for module in fresh.model.modules():
            if isinstance(module,torch.nn.modules.batchnorm._BatchNorm) and module.track_running_stats:
                assert module.running_mean.eq(0).all() and module.running_var.eq(1).all()
                assert module.num_batches_tracked.item()==0
        assert fresh.load_report['parameter_coverage']==0 and fresh.load_report['buffer_coverage']==0
        assert pretrained.load_report['parameter_coverage']==1 and pretrained.load_report['strict']
        try:
            fresh.native_task_contract()
        except ValueError as error:
            assert 'original pretrained head' in str(error)
        else:
            raise AssertionError('A random head cannot claim to retain original weights')
        rebuilt,_=construct(name,'scratch',33,artifact=fresh.official_artifact)
        rebuilt.load_state_dict(fresh.state_dict(),strict=True)
        assert digest(rebuilt)==hashes['fresh']
        item={'model':name,'accepted':True,'hashes':hashes,'feature_irreps':fresh.feature_irreps,
              'load_report':fresh.load_report,'parameter_count':sum(p.numel() for p in fresh.model.parameters())}
        results.append(item)
        (args.output/(name+'.json')).write_text(json.dumps(item,indent=2))
        del pretrained,fresh,again,different,rebuilt
    report={'accepted':True,'results':results,'slurm_job_id':os.environ['SLURM_JOB_ID'],
            'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            'scope':'CGCNN/ALIGNN actual upstream fresh construction and reload only; not full task training or GPU acceptance'}
    (args.output/'report.json').write_text(json.dumps(report,indent=2))
    print('OFFICIAL_FRESH_CONSTRUCTORS_ACCEPTED '+json.dumps({'models':[r['model'] for r in results]}))


if __name__=='__main__':
    main()
