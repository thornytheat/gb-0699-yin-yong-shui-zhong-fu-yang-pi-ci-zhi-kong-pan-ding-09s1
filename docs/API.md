# 接口

`POST /api/run`：{"text":"CSV内容"}。同规则版本与输入摘要只产生一条批次。

`GET/POST /api/1` 至 `/api/7`：独立样例或自定义文件计算。各模块返回 report、quarantine、balance。

`POST /api/review`：id、整数revision、decision取通过或退回。旧版本409；阻断项不能通过。状态为PENDING_EVIDENCE（待补证据、无质控失败）的批次允许通过，放行结果仍显式保留 `pending_ids` 待证范围。

`GET /api/export/{id}`：唯一证据CSV。行类别含 manifest、release（批次结论与证据引用）、coverage（逐样品项重复样证据状态）、result（复测/补平行任务）、quarantine。`GET /health`：存活检查。

错误：结构/数值422，版本冲突409，不存在404，文件过大413。逐行异常进入quarantine。
