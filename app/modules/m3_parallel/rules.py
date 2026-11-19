from decimal import Decimal
from app.report import report

def pair_check(a,b,mdl=Decimal("0.001"),censored=False):
    if censored:return {"status":"CENSORED_REVIEW","metric":None,"limit":None,"method":"限定值"}
    mean=(a+b)/2;diff=abs(a-b)
    if mean<5*mdl:return {"status":"PASS" if diff<=mdl else "PAIR_FAIL","metric":diff,"limit":mdl,"method":"绝对差mg/L"}
    relative=diff/mean
    return {"status":"PASS" if relative<=Decimal("0.20") else "PAIR_FAIL","metric":relative,"limit":Decimal("0.20"),"method":"相对偏差"}

def _identity(row):
    # 覆盖证据的稳定身份键：同一批同项同样品无论重跑多少次都只有一条结论
    return f'{row["batch"]}|{row["analyte"]}|{row["id"]}'

def apply(ctx):
    groups={}
    for r in ctx["effective"]:
        if r["kind"] in {"sample","duplicate"}:groups.setdefault((r["batch"],r["analyte"],r["pair"]),[]).append(r)
    out=[];coverage=[]
    for key,rows in sorted(groups.items()):
        batch,analyte,pair=key
        left=[r for r in rows if r["kind"]=="sample"];right=[r for r in rows if r["kind"]=="duplicate"]
        if len(left)!=1 or len(right)!=1:
            out.append({"batch":batch,"analyte":analyte,"pair":pair,"sample_id":left[0]["id"] if len(left)==1 else "","duplicate_id":right[0]["id"] if len(right)==1 else "","status":"PAIR_MISSING","metric":None,"limit":None,"method":"配对","coverage_status":"PENDING" if len(left)==1 else "UNPAIRED","supported_ids":[s["id"] for s in left],"pending_ids":[s["id"] for s in left]})
            for s in left:
                coverage.append({"identity":_identity(s),"id":s["id"],"batch":batch,"analyte":analyte,"pair":pair,"line":s["line"],"status":"PENDING","reason":"DUPLICATE_MISSING","duplicate_id":"","parallel_status":"PAIR_MISSING","supported_by":[]})
            continue
        s,d=left[0],right[0]
        check=pair_check(s["value_mg"],d["value_mg"],censored=s["censored"] or d["censored"])
        evidence_status={"PASS":"SUPPORTED","PAIR_FAIL":"FAILED","CENSORED_REVIEW":"REVIEW"}[check["status"]]
        out.append(dict(batch=batch,analyte=analyte,pair=pair,sample_id=s["id"],duplicate_id=d["id"],left=s["value_mg"],right=d["value_mg"],coverage_status=evidence_status,supported_ids=[s["id"]],pending_ids=[],**check))
        coverage.append({"identity":_identity(s),"id":s["id"],"batch":batch,"analyte":analyte,"pair":pair,"line":s["line"],"status":evidence_status,"reason":"" if check["status"]=="PASS" else check["status"],"duplicate_id":d["id"],"parallel_status":check["status"],"supported_by":[{"pair":pair,"duplicate_id":d["id"],"line":d["line"],"status":check["status"]}]})
    # 身份键去重：重跑同一批同一输入不产生重复结论（保留确定性顺序）
    deduped={}
    for row in coverage:deduped.setdefault(row["identity"],row)
    ctx["coverage"]=[deduped[k] for k in sorted(deduped)]
    ctx["parallel"]=out
    ledger=ctx["coverage"]
    return report(out,配对=len(out),失败=sum(r["status"]!="PASS" for r in out),
                  已支持=sum(r["status"]=="SUPPORTED" for r in ledger),
                  待补证据=sum(r["status"]=="PENDING" for r in ledger),
                  待复核=sum(r["status"]=="REVIEW" for r in ledger),
                  证据失败=sum(r["status"]=="FAILED" for r in ledger))
