from app.report import report
PRIORITY=["BLANK_FAIL","BLANK_MISSING","RECOVERY_FAIL","SPIKE_ZERO","BASE_MISSING","PAIR_FAIL","CENSORED_REVIEW"]
def verdict(statuses):
    return next((s for s in PRIORITY if s in statuses),"PASS")

def apply(ctx):
    keys={(r["batch"],r["analyte"]) for r in ctx["effective"]};out=[]
    for key in sorted(keys):
        rows=[r for source in [ctx["parallel"],ctx["recoveries"],ctx["blank_checks"]] for r in source if (r["batch"],r["analyte"])==key]
        # 配对缺失属于证据覆盖问题，交由覆盖台账判定，不冒充质控失败
        qc_statuses=[r["status"] for r in rows if r["status"]!="PAIR_MISSING"]
        if not any((r["batch"],r["analyte"])==key for r in ctx["blank_checks"]):qc_statuses.append("BLANK_MISSING")
        ledger=[r for r in ctx.get("coverage",[]) if (r["batch"],r["analyte"])==key]
        supported=[r["id"] for r in ledger if r["status"]=="SUPPORTED"]
        pending=[r["id"] for r in ledger if r["status"]=="PENDING"]
        review=[r["id"] for r in ledger if r["status"]=="REVIEW"]
        failed=[r["id"] for r in ledger if r["status"]=="FAILED"]
        qc=verdict(qc_statuses)
        if qc!="PASS":status=qc
        elif pending:status="PENDING_EVIDENCE"
        else:status="PASS"
        out.append({"batch":key[0],"analyte":key[1],"status":status,"checks":len(rows),"failed":sum(s!="PASS" for s in qc_statuses),
                    "evidence_total":len(ledger),"supported":len(supported),"pending":len(pending),"review":len(review),"evidence_failed":len(failed),
                    "supported_ids":supported,"pending_ids":pending,"review_ids":review,"failed_ids":failed,
                    "evidence_refs":[{"identity":r["identity"],"id":r["id"],"pair":r["pair"],"status":r["status"],"reason":r["reason"],"duplicate_id":r["duplicate_id"]} for r in ledger]})
    # 放行结论按检测批+检测项去重：重跑不新增重复结论
    deduped={}
    for row in out:deduped.setdefault((row["batch"],row["analyte"]),row)
    # 待证据可带显式范围先行放行；只有质控/复核失败才硬阻断
    ctx["released"]=[deduped[k] for k in sorted(deduped)]
    ctx["blocked"]=not ctx["released"] or any(r["status"] not in ("PASS","PENDING_EVIDENCE") for r in ctx["released"])
    ctx["balance"]={"input":ctx["input_count"],"accepted":ctx["input_count"]-len(ctx["quarantine"])-ctx["blank_rows"],"quarantined":len(ctx["quarantine"]),"blank":ctx["blank_rows"]}
    return report(ctx["released"],可放行=sum(r["status"]=="PASS" for r in ctx["released"]),
                  待补证据=sum(r["status"]=="PENDING_EVIDENCE" for r in ctx["released"]),
                  阻断=sum(r["status"] not in ("PASS","PENDING_EVIDENCE") for r in ctx["released"]),
                  待补样品项=sum(r["pending"] for r in ctx["released"]))
