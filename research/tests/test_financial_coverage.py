import importlib.util
from pathlib import Path


def test_dependency_basename_does_not_suppress_financial_source():
    root=Path(__file__).resolve().parents[2]
    spec=importlib.util.spec_from_file_location('financial_coverage',root/'scripts/financial-coverage.py')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    tracer=module.make_tracer()
    dependency=str(root/'backend/.venv/Lib/site-packages/sympy/concrete/products.py')
    application=str(root/'backend/app/products.py')
    assert tracer.ignore.names(dependency,'products')
    assert not tracer.ignore.names(application,'products')
    for name in module.FILES:
        assert not tracer.ignore.names(str(root/'backend/app'/name),Path(name).stem)
    assert tracer.ignore.names(str(root/'backend/app/main.py'),'main')
