import csv,io,json

def evidence_csv(run):
    out=io.StringIO();writer=csv.writer(out)
    writer.writerow(["run_id","sha256","rule_version","kind","line","reason","evidence"])
    writer.writerow([run["id"],run["digest"],run["rule_version"],"manifest","","",json.dumps({"balance":run["result"]["balance"],"decision":run["decision"],"revision":run["revision"]},ensure_ascii=False)])
    for row in run["result"].get("released",[]):
        writer.writerow([run["id"],run["digest"],run["rule_version"],"release",row.get("evidence_refs",[{}])[0].get("line","") if row.get("evidence_refs") else "",row.get("status",""),json.dumps(row,ensure_ascii=False)])
    for row in run["result"].get("coverage",[]):
        writer.writerow([run["id"],run["digest"],run["rule_version"],"coverage",row.get("line",""),row.get("reason",row.get("status","")),json.dumps(row,ensure_ascii=False)])
    for row in run["result"].get("final",[]):
        writer.writerow([run["id"],run["digest"],run["rule_version"],"result",row.get("line",""),row.get("status",""),json.dumps(row,ensure_ascii=False)])
    for row in run["result"].get("quarantine",[]):
        writer.writerow([run["id"],run["digest"],run["rule_version"],"quarantine",row.get("line",""),row["reason"],json.dumps(row,ensure_ascii=False)])
    return "﻿"+out.getvalue()
