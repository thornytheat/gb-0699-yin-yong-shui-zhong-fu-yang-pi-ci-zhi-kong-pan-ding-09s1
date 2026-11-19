# TRAP-26
from app.modules.m7_retest.rules import *
from app.errors import BusinessError
from app.numbers import number
from decimal import Decimal
import pytest

def test_retest_version():
    assert next_version(1,2)==2

def test_retest_stale():
    with pytest.raises(ValueError):next_version(2,2)

def test_retest_backward():
    with pytest.raises(ValueError):next_version(2,1)

def test_retest_large():
    assert next_version(100,102)==102

def test_retest_sample(result):
    # 复测任务只覆盖失败实际涉及的样品项，不再整批扩大
    assert len(result["final"])==6

def test_retest_scoped_identities(result):
    ids={r["id"] for r in result["final"]}
    assert ids=={"006S","007S","008S","009S","010S","010B"}

def test_retest_identity_unique(result):
    keys=[r["identity"] for r in result["final"]]
    assert len(keys)==len(set(keys))

def test_retest_evidence_ref(result):
    samples=[r for r in result["final"] if r["kind"]=="sample"]
    assert all(r["evidence_ref"]==f'{r["batch"]}|{r["analyte"]}|{r["id"]}' for r in samples)

def test_retest_increment(result):
    assert all(r["required_version"]>r["current_version"] for r in result["final"])

def test_retest_batch(result):
    assert {r["batch"] for r in result["final"]}=={"B02"}