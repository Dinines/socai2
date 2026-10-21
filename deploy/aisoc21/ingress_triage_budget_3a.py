"""One new ingress at a time; reuse the verified HTTP/Fusion capture operator."""
import asyncio,importlib.util,sys,uuid
from pathlib import Path

E=Path('/evidence');B='3a-triage-budget-20261020'
ALIASES=['a_done','b_done','a_unknown','a_denied','b_denied','b_extra']


async def main(alias):
    assert alias in ALIASES
    assert not (E/'inputs.json').exists() or (alias=='b_extra' and not (E/'inputs-extra.json').exists())
    output=E/('ingress-'+alias)
    assert not output.exists(),'Sending/accepted outcomes must be inspected, never resubmitted'
    output.mkdir(mode=0o700)
    spec=importlib.util.spec_from_file_location('existing_ingress','/operators/ingress_triage_durability_3a.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.E=output;module.B=B
    original=module.uuid.uuid5
    module.uuid=type('UUIDs',(),{'uuid5':staticmethod(lambda namespace,name:original(namespace,name+'/'+alias)),
                               'UUID':staticmethod(uuid.UUID),'NAMESPACE_URL':uuid.NAMESPACE_URL})
    await module.main()


if __name__=='__main__':asyncio.run(main(*sys.argv[1:]))
