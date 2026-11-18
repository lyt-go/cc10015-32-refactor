"""业务模块路由汇总。

这里统一按别名导入再暴露 ROUTERS：模块名有可能和内置名撞车（某个业务模块就叫 dict、list
这种名字时），按名字直接 import 会把内置类型覆盖掉，函数注解在运行时求值就会报
'module' object is not subscriptable。
"""
from __future__ import annotations

from app.routers import experiment as router_experiment
from app.routers import sample_group as router_sample_group
from app.routers import metric_def as router_metric_def
from app.routers import ab_result as router_ab_result
from app.routers import segment_compare as router_segment_compare
from app.routers import drill_down as router_drill_down
from app.routers import data_filter as router_data_filter
from app.routers import attr_analysis as router_attr_analysis
from app.routers import anomaly_detect as router_anomaly_detect
from app.routers import forecast_model as router_forecast_model
from app.routers import data_export as router_data_export
from app.routers import cohort_track as router_cohort_track
from app.routers import chart_config as router_chart_config
from app.routers import insight_report as router_insight_report
from app.routers import data_freshness as router_data_freshness
from app.routers import metric_alias as router_metric_alias
from app.routers import expr_factor as router_expr_factor
from app.routers import evaluate_board as router_evaluate_board
from app.routers import retention_matrix as router_retention_matrix

ROUTERS = [router_experiment, router_sample_group, router_metric_def, router_ab_result, router_segment_compare, router_drill_down, router_data_filter, router_attr_analysis, router_anomaly_detect, router_forecast_model, router_data_export, router_cohort_track, router_chart_config, router_insight_report, router_data_freshness, router_metric_alias, router_expr_factor, router_evaluate_board, router_retention_matrix]
