"""留存矩阵与洞察结论的共用路径测试。

覆盖四件事：
1. 重构后留存矩阵数据表与洞察结论数据表复现历史结果；
2. 新周期口径有独立版本，且历史矩阵列不被覆盖；
3. 工作台与详情页展示同一份业务数据；
4. V032 矩阵替换遇到未清残留时整笔回滚，并按留档核对。
"""
from __future__ import annotations

import copy
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from app.retention_core import (
    CURRENT_CALIBER,
    HISTORICAL_CALIBER,
    historical_archive,
    period_columns,
    retention_series,
)
from app.retention_definitions import COHORTS, MATRIX_VERSION
from app.retention_seed import (
    ARCHIVE_TABLE,
    CONCLUSION_TABLE,
    HISTORY_TABLE,
    MATRIX_TABLE,
    SNAPSHOT_TABLE,
    VERSION_TABLE,
    build_retention_tables,
    matrix_fingerprint,
)
from app.services import retention
from app.services.cohort_track import CohortTrackService
from app.services.insight_report import InsightReportService
from app.store import store


@pytest.fixture(autouse=True)
def reset_tables():
    """每个用例都从示例数据的原始状态开始，避免事务外用例互相污染。"""
    from app.retention_seed import cohort_rows, insight_rows

    store._tables["cohort_track"] = [copy.deepcopy(row) for row in cohort_rows()]
    store._tables["insight_report"] = [copy.deepcopy(row) for row in insight_rows()]
    for name, rows in build_retention_tables().items():
        store._tables[name] = [copy.deepcopy(row) for row in rows]
    yield


# ---------------------------------------------------------------------------
# 1. 历史复现
# ---------------------------------------------------------------------------


def test_matrix_reproduces_history():
    """存活矩阵仍复现历史留档的每一列，成员边界不变。"""
    result = retention.verify_history()
    assert result["ok"], result["差异"]
    assert result["核对群组数"] == len(COHORTS)

    archive = historical_archive(COHORTS)
    for row in retention.matrix_rows("V031"):
        expected = archive[row["群组编号"]]
        assert period_columns(row) == expected["周期列"]
        assert row["成员边界"] == expected["成员边界"]
        assert row["留存窗口"] == expected["留存窗口"]


def test_rerun_uses_archived_member_boundary():
    """重跑历史同期群只认留档成员边界，不读取当前群组定义。"""
    service = CohortTrackService()
    before = service.get_entry(1)
    expected = retention.retention_series_from_history("COHO-0001")

    # 改掉当前群组定义的成员基数与时间基准，模拟业务侧调整。
    current = store.find("cohort_track", 1)
    current["成员基数"] = 7
    current["时间基准"] = "2026-10-01"
    current["留存窗口"] = "2"

    rerun = service.rerun("COHO-0001")
    assert rerun["周期列"] == expected["周期列"], "重跑必须沿用历史成员边界"
    assert rerun["成员边界"] == expected["成员边界"]
    assert str(rerun["留存窗口"]) == str(before["留存窗口"])
    assert retention.verify_history()["ok"], "矩阵本身不应被当前定义的改动影响"


def test_period_window_and_caliber_are_single_sourced():
    """同期群追踪与洞察报告读到的周期列完全一致，不再各自维护一份。"""
    cohort = CohortTrackService().get_entry(1)
    insight = InsightReportService().get_entry(1)
    assert insight["历史口径留存率"] == cohort["留存率"]["第3期"]
    assert set(cohort["留存率"]) == {
        f"第{index}期" for index in range(1, int(cohort["留存窗口"]) + 1)
    }


# ---------------------------------------------------------------------------
# 2. 新口径独立版本
# ---------------------------------------------------------------------------


def test_new_caliber_has_independent_version():
    versions = retention.versions()
    assert {item["版本"] for item in versions} == {"V031", MATRIX_VERSION}
    historical = retention.matrix_rows("V031")
    current = retention.matrix_rows("V032")
    assert len(historical) == len(current)
    for old, new in zip(historical, current):
        assert old["群组编号"] == new["群组编号"]
        assert old["口径"] == HISTORICAL_CALIBER
        assert new["口径"] == CURRENT_CALIBER
        assert old["留存窗口"] == new["留存窗口"], "新口径不改周期窗口"
        assert set(period_columns(old)) == set(period_columns(new)), "新口径不改周期列"
        assert period_columns(old) != period_columns(new), "新口径应当算出不同留存率"


# ---------------------------------------------------------------------------
# 3. 工作台与详情页同一份数据
# ---------------------------------------------------------------------------


def test_workbench_and_detail_share_payload():
    service = CohortTrackService()
    rows = service.list_results()
    assert len(rows) == 3
    for row in rows:
        detail = service.get_entry(int(row["id"]))
        assert detail is not None
        assert detail["留存率"] == row["留存率"]
        assert detail["周期口径"] == row["周期口径"]
        assert detail["成员基数"] == row["成员基数"]
        assert detail["留存窗口"] == row["留存窗口"]


def test_insight_workbench_and_detail_share_payload():
    service = InsightReportService()
    for row in service.list_results():
        detail = service.get_entry(int(row["id"]))
        assert detail is not None
        assert detail["历史口径留存率"] == row["历史口径留存率"]
        assert detail["新口径留存率"] == row["新口径留存率"]
        assert detail["核对结论"] == row["核对结论"]


def test_insight_samples_match_matrix():
    """跨模块联动（V032）：原报告样例的关键发现与矩阵读取一致。"""
    result = InsightReportService().verify()
    assert result["ok"], result["mismatches"]
    assert result["checked"] == 3
    for report in store.rows("insight_report"):
        conclusion = InsightReportService().conclusion_for(report["报告编号"])
        assert conclusion is not None
        assert conclusion["结论"] == report["关键发现"]


# ---------------------------------------------------------------------------
# 4. V032 矩阵替换的事务与留档
# ---------------------------------------------------------------------------


def test_replace_blocked_by_residue_rolls_back():
    """未清残留存在时，矩阵替换整笔回滚，矩阵与版本表保持不变。"""
    matrix_before = copy.deepcopy(store.rows(MATRIX_TABLE))
    version_before = copy.deepcopy(store.rows(VERSION_TABLE))
    archive_before = len(store.rows(ARCHIVE_TABLE))

    result = retention.replace_matrix(policy="recompute")
    assert result["ok"] is False
    assert result["结果"] == "rolled_back"
    assert result["残留"] == {"COHO-0001": ["第99期"]}
    assert store.rows(MATRIX_TABLE) == matrix_before
    assert store.rows(VERSION_TABLE) == version_before
    assert store.rows(SNAPSHOT_TABLE) == []
    assert len(store.rows(ARCHIVE_TABLE)) == archive_before + 1
    assert store.rows(ARCHIVE_TABLE)[-1]["结果"] == "rolled_back"


def test_historical_first_keeps_old_columns_and_annotates_diff():
    """历史口径优先：矩阵保留旧列结果，只附新口径差异。"""
    retention.clean_residue()
    result = retention.replace_matrix(policy="historical_first")
    assert result["ok"] is True

    for row in retention.matrix_rows("V031"):
        current = retention.matrix_row_for(row["群组编号"], "V032")
        assert period_columns(row) == {
            label: value for label, value in period_columns(row).items()
        }
        assert row["口径"] == HISTORICAL_CALIBER
        assert row["新口径差异"]["第2期"]["新口径"] == period_columns(current)["第2期"]
        assert row["新口径差异"]["第2期"]["历史口径"] == period_columns(row)["第2期"]
    assert retention.verify_history()["ok"], "历史列必须保持不变"


def test_recompute_replaces_columns_and_keeps_snapshot():
    """按新口径整列重算：矩阵替换为当前口径，历史列快照保留。"""
    retention.clean_residue()
    before = {row["群组编号"]: period_columns(row) for row in retention.matrix_rows("V031")}

    result = retention.replace_matrix(policy="recompute")
    assert result["ok"] is True

    for row in retention.matrix_rows("V031"):
        assert row["口径"] == CURRENT_CALIBER
        assert period_columns(row) == period_columns(retention.matrix_row_for(row["群组编号"], "V032"))
    assert retention.verify_history()["ok"] is False, "整列重算后历史核对应报差异"

    snapshots = retention.snapshot_rows()
    assert len(snapshots) == len(before)
    assert {item["群组编号"]: item["周期列"] for item in snapshots} == before

    restored = retention.restore_snapshot()
    assert restored["ok"] is True
    assert {row["群组编号"]: period_columns(row) for row in retention.matrix_rows("V031")} == before
    assert retention.verify_history()["ok"] is True


def test_archive_check_matches_matrix_state():
    result = retention.check_archive()
    assert result["ok"] is True
    assert result["版本"] == MATRIX_VERSION
    assert result["留档指纹"] == matrix_fingerprint(retention.matrix_rows("V031", include_residue=True))


def test_insight_conclusions_read_current_version_after_replace():
    """洞察结论读取矩阵：替换后新口径留存率随之更新，历史口径仍可追溯。"""
    retention.clean_residue()
    retention.replace_matrix(policy="historical_first")
    service = InsightReportService()
    conclusion = service.conclusion_for("INSI-0001")
    assert conclusion is not None
    current = retention.matrix_row_for("COHO-0001", "V032")
    assert conclusion["新口径留存率"] == period_columns(current)["第3期"]
    assert service.verify()["ok"] is True


def test_unknown_policy_rejected():
    with pytest.raises(retention.RetentionError):
        retention.replace_matrix(policy="overwrite_everything")


def test_conclusion_table_and_matrix_are_consistent():
    conclusions = store.rows(CONCLUSION_TABLE)
    assert conclusions
    for item in conclusions:
        historical = retention.matrix_row_for(item["群组编号"], "V031")
        current = retention.matrix_row_for(item["群组编号"], "V032")
        label = f"第{item['核对周期']}期"
        assert item["历史口径留存率"] == period_columns(historical)[label]
        assert item["新口径留存率"] == period_columns(current)[label]


def test_retention_series_is_deterministic():
    """同一份输入跨调用必须得到同一份输出，否则历史留存率会漂移。"""
    first = retention_series(COHORTS[0], HISTORICAL_CALIBER)
    second = retention_series(COHORTS[0], HISTORICAL_CALIBER)
    assert first == second
