# 深度登记 饮用水重复样与批次质控判定

- 规模：中型
- 核心规则：双样相对偏差分母零时单独判定；低浓度用绝对差阈值，高浓度用相对偏差；加标回收扣除本底

## 功能模块

| 模块 | 使用者动作 | 入口 | 核心文件 | 测试 |
|---|---|---|---|---|
| M1 样品接收 | 运行样品接收并核对证据 | `POST /api/1` | `app/modules/m1_samples/rules.py` | `tests/test_samples.py` |
| M2 检测项契约 | 运行检测项契约并核对证据 | `POST /api/2` | `app/modules/m2_contract/rules.py` | `tests/test_contract.py` |
| M3 平行样核对 | 运行平行样核对并核对证据 | `POST /api/3` | `app/modules/m3_parallel/rules.py` | `tests/test_parallel.py` |
| M4 加标回收 | 运行加标回收并核对证据 | `POST /api/4` | `app/modules/m4_spikes/rules.py` | `tests/test_spikes.py` |
| M5 空白污染 | 运行空白污染并核对证据 | `POST /api/5` | `app/modules/m5_blanks/rules.py` | `tests/test_blanks.py` |
| M6 批次放行 | 运行批次放行并核对证据 | `POST /api/6` | `app/modules/m6_release/rules.py` | `tests/test_release.py` |
| M7 复测追踪 | 运行复测追踪并核对证据 | `POST /api/7` | `app/modules/m7_retest/rules.py` | `tests/test_retest.py` |

## 陷阱登记

| TRAP | 现象 | 朴素实现会怎样 | 本项目处理 | 处理位置 | 测试 |
|---|---|---|---|---|---|
| TRAP-02 | BOM | 静默采信错误值 | 剔除首列BOM | `app/modules/m1_samples/rules.py` | `tests/test_samples.py::test_sample_bom` |
| TRAP-06 | 全角千分位 | 静默采信错误值 | NFKC转Decimal | `app/modules/m2_contract/rules.py` | `tests/test_contract.py::test_contract_unit` |
| TRAP-07 | 空值 | 静默采信错误值 | 缺失隔离 | `app/modules/m2_contract/rules.py` | `tests/test_contract.py::test_contract_sentinel` |
| TRAP-10 | 背景扣除误差 | 静默采信错误值 | Decimal精算 | `app/modules/m4_spikes/rules.py` | `tests/test_spikes.py::test_spike_background` |
| TRAP-14 | 同版冲突 | 静默采信错误值 | 隔离重复版本 | `app/modules/m1_samples/rules.py` | `tests/test_samples.py::test_sample_conflict` |
| TRAP-15 | ug与mg | 静默采信错误值 | 统一mg/L | `app/modules/m2_contract/rules.py` | `tests/test_contract.py::test_contract_unit` |
| TRAP-19 | 多质控失败 | 静默采信错误值 | 明确优先级 | `app/modules/m6_release/rules.py` | `tests/test_release.py::test_release_priority` |
| TRAP-26 | 陈旧复测 | 静默采信错误值 | 版本递增 | `app/modules/m7_retest/rules.py` | `tests/test_retest.py::test_retest_stale` |
| TRAP-31 | 部分重复样覆盖整批放行 | 一组重复样通过即带过同批未覆盖样品 | 覆盖台账逐样品项标记SUPPORTED/PENDING，批次结论PENDING_EVIDENCE显式列待证范围 | `app/modules/m3_parallel/rules.py`、`app/modules/m6_release/rules.py` | `tests/test_coverage.py::test_release_carries_pending_not_silent_pass` |
| TRAP-32 | 补样改写已发结果 | 补来的重复样重算整批、覆盖旧结论 | 证据按batch\|analyte\|id身份键限定，补样只改其样品项，其他结论不变 | `app/modules/m3_parallel/rules.py` | `tests/test_coverage.py::test_supplement_only_changes_its_scope` |
| TRAP-33 | 重跑产生重复结论 | 每次运行追加重复批次/复测行 | 台账与放行按稳定身份键去重，存储按输入摘要复用同一记录并保留评审历史 | `app/modules/m6_release/rules.py`、`app/store.py` | `tests/test_coverage.py::test_rerun_same_input_no_duplicate_conclusions` |
| TRAP-34 | 复测任务整批扩大 | 一项失败即对整批全部样品开复测 | M7按失败来源逐样品项生成RETEST/SUPPLEMENT，控制样失败只开控制样任务 | `app/modules/m7_retest/rules.py` | `tests/test_coverage.py::test_failed_duplicate_blocks_its_sample_only` |

## 对账规则

输入记录=采信记录+隔离记录+空行；重复记录归隔离；算法输出另记业务单位，不冒充输入行数。金额/浓度/时长使用Decimal；证据含原始行号。

## 已知不覆盖

不支持超过2MB输入，不执行生产自动放行；异常值需人员复核。
