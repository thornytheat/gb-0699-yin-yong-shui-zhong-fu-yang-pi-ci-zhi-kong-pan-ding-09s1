def execute(text):
    from app.pipeline import run
    result=run(text)
    return {"module":6, "report":result["reports"][5], "coverage":result["coverage"], "quarantine":result["quarantine"], "balance":result["balance"]}
