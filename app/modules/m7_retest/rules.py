from app.report import report

def next_version(current,proposed):
    if proposed<=current:raise ValueError("复测版本须递增")
    return proposed

def _identity(batch,analyte,sample_id):
    return f'{batch}|{analyte}|{sample_id}'

def apply(ctx):
    tasks={}
    def add(batch,analyte,sample_id,kind,line,rev,status,reason,evidence_ref):
        key=_identity(batch,analyte,sample_id)
        if key in tasks:return
        tasks[key]={"identity":key,"id":sample_id,"batch":batch,"analyte":analyte,"kind":kind,
                    "current_version":rev,"required_version":next_version(rev,rev+1),"status":status,
                    "reason":reason,"line":line,"evidence_ref":evidence_ref or key}
    failed_keys={(r["batch"],r["analyte"]) for r in ctx["released"] if r["status"] not in ("PASS","PENDING_EVIDENCE")}
    # 覆盖台账：补样只影响它能证明的样品项
    for r in ctx.get("coverage",[]):
        if r["status"]=="PENDING":
            add(r["batch"],r["analyte"],r["id"],"sample",r["line"],_rev(ctx,r),"SUPPLEMENT","DUPLICATE_MISSING",r["identity"])
        elif r["status"]=="REVIEW":
            add(r["batch"],r["analyte"],r["id"],"sample",r["line"],_rev(ctx,r),"RETEST","CENSORED_REVIEW",r["identity"])
        elif r["status"]=="FAILED" and (r["batch"],r["analyte"]) in failed_keys:
            add(r["batch"],r["analyte"],r["id"],"sample",r["line"],_rev(ctx,r),"RETEST","PAIR_FAIL",r["identity"])
    # 空白与加标失败：只生成对应控制样的任务，不扩大到整批
    for r in ctx["blank_checks"]:
        if r["status"]!="PASS":add(r["batch"],r["analyte"],r["id"],"blank",r["line"],_rev(ctx,r),"RETEST",r["status"],"")
    for r in ctx["recoveries"]:
        if r["status"] not in ("PASS","CENSORED_REVIEW"):add(r["batch"],r["analyte"],r["id"],"spike",r["line"],_rev(ctx,r),"RETEST",r["status"],"")
    out=[tasks[k] for k in sorted(tasks)]
    ctx["final"]=out
    return report(out,复测任务=len(out),复测=sum(r["status"]=="RETEST" for r in out),补平行=sum(r["status"]=="SUPPLEMENT" for r in out),有效样品=len(ctx["effective"]))

def _rev(ctx,row):
    for r in ctx["effective"]:
        if r["id"]==row["id"] and r["batch"]==row["batch"] and r["analyte"]==row["analyte"]:return r["rev"]
    return 1
