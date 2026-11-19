# 重复样证据范围与批次结论可核对关系
from app.pipeline import run
from app import store
from app.exporter import evidence_csv
import pytest

HEADER="id,batch,analyte,kind,pair,value,spike,unit,version"
def row(id,batch,analyte,kind,pair,value,spike="0",version="1"):
    return f"{id},{batch},{analyte},{kind},{pair},{value},{spike},mg/L,{version}"
def csv_text(*rows_):
    return HEADER+"\n"+"\n".join(rows_)+"\n"

def one_batch(covered_pairs,total_pairs,batch="B1"):
    rows_=[]
    for n in range(1,total_pairs+1):
        p=f"P{n}"
        rows_.append(row(f"S{n}",batch,"Pb","sample",p,"0.003"))
        if n in covered_pairs:
            rows_.append(row(f"D{n}",batch,"Pb","duplicate",p,"0.0032"))
        rows_.append(row(f"A{n}",batch,"Pb","spike",p,"0.013",".01"))
        rows_.append(row(f"K{n}",batch,"Pb","blank","",".0002"))
    return csv_text(*rows_)

def test_partial_coverage_marked_pending():
    r=run(one_batch({1,2},4))
    pending={c["id"]:c for c in r["coverage"] if c["status"]=="PENDING"}
    supported={c["id"] for c in r["coverage"] if c["status"]=="SUPPORTED"}
    assert set(pending)=={"S3","S4"}
    assert supported=={"S1","S2"}
    assert all(c["reason"]=="DUPLICATE_MISSING" for c in pending.values())

def test_release_carries_pending_not_silent_pass():
    r=run(one_batch({1,2},4))
    gate=r["released"][0]
    assert gate["status"]=="PENDING_EVIDENCE"
    assert gate["pending"]==2 and gate["supported"]==2
    assert gate["pending_ids"]==["S3","S4"]
    # 待证据不是质控失败，不硬阻断交付，但结论保留显式待证范围
    assert r["blocked"] is False
    assert gate["status"]!="PASS"

def test_hard_failure_still_blocks():
    rows_=[]
    for n in (1,):
        p=f"P{n}"
        rows_.append(row(f"S{n}","B9","Pb","sample",p,"0.010"))
        rows_.append(row(f"D{n}","B9","Pb","duplicate",p,"0.016"))
        rows_.append(row(f"A{n}","B9","Pb","spike",p,"0.020",".01"))
        rows_.append(row(f"K{n}","B9","Pb","blank","",".0002"))
    assert run(csv_text(*rows_))["blocked"] is True

def test_pending_batch_is_releasable_when_review_passes():
    # 待证据不是质控失败，允许先放行但结论显式保留待证范围（不被静默带过）
    text=one_batch({1,2},4,batch="BR1")
    saved=store.save(text,run(text))
    reviewed=store.review(saved["id"],saved["revision"],"通过")
    assert reviewed["decision"]=="通过"
    gate=reviewed["result"]["released"][0]
    assert gate["status"]=="PENDING_EVIDENCE" and gate["pending_ids"]==["S3","S4"]

def test_supplement_only_changes_its_scope():
    before=run(one_batch({1,2},4,batch="BS1"))
    # 在保留 S1/S2 重复样的前提下，仅补 S3 的重复样；S4 仍待证
    rows_=[]
    for n in range(1,5):
        p=f"P{n}"
        rows_.append(row(f"S{n}","BS1","Pb","sample",p,"0.003"))
        if n in (1,2,3):
            rows_.append(row(f"D{n}","BS1","Pb","duplicate",p,"0.0032"))
        rows_.append(row(f"A{n}","BS1","Pb","spike",p,"0.013",".01"))
        rows_.append(row(f"K{n}","BS1","Pb","blank","",".0002"))
    after=run(csv_text(*rows_))
    assert {c["id"] for c in after["coverage"] if c["status"]=="SUPPORTED"}=={"S1","S2","S3"}
    assert [c["id"] for c in after["coverage"] if c["status"]=="PENDING"]==["S4"]
    before_ref={c["identity"]:c["parallel_status"] for c in before["coverage"]}
    after_ref={c["identity"]:c["parallel_status"] for c in after["coverage"]}
    # 补样只改写它能证明的 S3；S1/S2 结论保持不变，S4 仍等待证据
    assert before_ref["BS1|Pb|S3"]=="PAIR_MISSING" and after_ref["BS1|Pb|S3"]=="PASS"
    for ident in ("BS1|Pb|S1","BS1|Pb|S2"):
        assert before_ref[ident]==after_ref[ident]=="PASS"
    assert after_ref["BS1|Pb|S4"]=="PAIR_MISSING"

def test_failed_duplicate_blocks_its_sample_only():
    # 高浓度双样相对偏差超20% => PAIR_FAIL
    rows_=[]
    for n in (1,2):
        p=f"P{n}"
        rows_.append(row(f"S{n}","B1","Pb","sample",p,"0.010"))
        rows_.append(row(f"D{n}","B1","Pb","duplicate",p,"0.016"))
        rows_.append(row(f"A{n}","B1","Pb","spike",p,"0.020",".01"))
        rows_.append(row(f"K{n}","B1","Pb","blank","",".0002"))
    r=run(csv_text(*rows_))
    gate=r["released"][0]
    assert gate["status"]=="PAIR_FAIL" and gate["evidence_failed"]==2
    tasks={t["id"]:t for t in r["final"] if t["kind"]=="sample"}
    assert set(tasks)=={"S1","S2"}
    assert all(t["status"]=="RETEST" and t["reason"]=="PAIR_FAIL" for t in tasks.values())

def test_supplement_task_for_pending():
    r=run(one_batch({1},3,batch="BT1"))
    supplements={t["id"]:t for t in r["final"] if t["status"]=="SUPPLEMENT"}
    assert set(supplements)=={"S2","S3"}
    assert all(t["reason"]=="DUPLICATE_MISSING" for t in supplements.values())

def test_rerun_same_input_no_duplicate_conclusions():
    text=one_batch({1,2},4,batch="BD1")
    r1=run(text);r2=run(text)
    assert [c["identity"] for c in r1["coverage"]]==[c["identity"] for c in r2["coverage"]]
    ids1=[c["identity"] for c in r1["coverage"]]
    assert len(ids1)==len(set(ids1))
    keys1=[(g["batch"],g["analyte"]) for g in r1["released"]]
    assert len(keys1)==len(set(keys1))
    saved1=store.save(text,run(text));saved2=store.save(text,run(text))
    assert saved1["id"]==saved2["id"]

def test_rerun_persists_history():
    text=one_batch({1},2,batch="BH2")
    first=store.save(text,run(text))
    start=first["revision"]
    store.review(first["id"],start,"退回")
    again=store.save(text,run(text))
    # 重跑同一输入复用同一记录、保留评审历史，且不产生新结论行
    assert again["id"]==first["id"] and again["revision"]==start+1
    assert {x["id"] for x in store.history()} >= {first["id"]}

def test_export_shows_evidence_scope():
    saved=store.save(one_batch({1,2},4,batch="BE1"),run(one_batch({1,2},4,batch="BE1")))
    text=evidence_csv(saved)
    assert "coverage" in text and "release" in text
    assert "PENDING_EVIDENCE" in text and "DUPLICATE_MISSING" in text
    assert "BE1|Pb|S3" in text

def test_coverage_identity_stable_across_versions():
    v1=one_batch({1},2,batch="BV1")
    rows_=[row("S1","BV1","Pb","sample","P1","0.003"),row("D1","BV1","Pb","duplicate","P1","0.0032"),
           row("A1","BV1","Pb","spike","P1","0.013",".01"),row("K1","BV1","Pb","blank","",".0002"),
           row("S2","BV1","Pb","sample","P2","0.003"),
           row("A2","BV1","Pb","spike","P2","0.013",".01"),row("K2","BV1","Pb","blank","",".0002")]
    before=run(v1);after=run(csv_text(*rows_))
    ident_before={c["identity"] for c in before["coverage"]}
    ident_after={c["identity"] for c in after["coverage"]}
    assert ident_before==ident_after
    changed=[c for c in after["coverage"] if c["id"]=="S1"][0]
    assert changed["status"]=="SUPPORTED"

def test_duplicate_group_supports_only_its_sample():
    r=run(one_batch({1},3,batch="BG1"))
    s1=[c for c in r["coverage"] if c["id"]=="S1"][0]
    assert s1["supported_by"][0]["duplicate_id"]=="D1"
    s3=[c for c in r["coverage"] if c["id"]=="S3"][0]
    assert s3["supported_by"]==[]
