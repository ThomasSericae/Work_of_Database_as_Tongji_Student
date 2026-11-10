-- ============================================================
-- 时空查询与研判 —— 演示查询 (对应需求分析"时空查询与研判")
-- 在 urban_crime 库上执行, 覆盖: 分级筛选 / 时间趋势 / 社区热点 /
-- 空间范围与半径 / 处罚方式 / 时空组合查询
-- ============================================================

USE urban_crime;

-- ------------------------------------------------------------
-- 1. 轻微犯罪筛选: 只看"轻微/一般"级别(呼应"轻微犯罪"主题)
-- ------------------------------------------------------------
SELECT severity_level, COUNT(*) AS 案件数
FROM fact_crime fc
JOIN dim_category c ON fc.category_id = c.category_id
WHERE c.severity_level IN ('轻微', '一般')
GROUP BY severity_level;

-- ------------------------------------------------------------
-- 2. 时间趋势: 逐月案件数(时序分析)
-- ------------------------------------------------------------
SELECT t.month AS 月份, COUNT(*) AS 案件数
FROM fact_crime fc
JOIN dim_time t ON fc.time_id = t.time_id
GROUP BY t.month
ORDER BY t.month;

-- ------------------------------------------------------------
-- 3. 社区治安热点: 各社区案件总量 TOP10(热点识别)
-- ------------------------------------------------------------
SELECT n.neighbourhood_name AS 社区, COUNT(*) AS 案件数
FROM fact_crime fc
JOIN dim_location l ON fc.location_id = l.location_id
JOIN dim_neighbourhood n ON l.neighbourhood_id = n.neighbourhood_id
GROUP BY n.neighbourhood_name
ORDER BY 案件数 DESC
LIMIT 10;

-- ------------------------------------------------------------
-- 4. 空间范围查询: 某矩形经纬度范围内的案件(矩形粗筛)
-- ------------------------------------------------------------
SELECT COUNT(*) AS 范围内案件数
FROM fact_crime fc
JOIN dim_location l ON fc.location_id = l.location_id
WHERE l.latitude  BETWEEN 53.79 AND 53.82
  AND l.longitude BETWEEN -1.57 AND -1.53;

-- ------------------------------------------------------------
-- 5. 空间半径查询: 距某点(利兹市中心) 1 公里内的案件
--    (用平方距离公式, 不依赖 PostGIS; 1 度纬度≈111km, 经度≈111*cos(53.8))
-- ------------------------------------------------------------
SELECT COUNT(*) AS 1公里内案件数
FROM fact_crime fc
JOIN dim_location l ON fc.location_id = l.location_id
WHERE POWER((l.latitude  - 53.7955) * 111.0, 2)
    + POWER((l.longitude - (-1.5474)) * 111.0 * 0.592, 2) <= 1.0;

-- ------------------------------------------------------------
-- 6. 处罚方式分布: 只统计"处罚型"处理结果(警告/罚款通知/社区判决/调解)
-- ------------------------------------------------------------
SELECT o.outcome_cn AS 处罚方式, COUNT(*) AS 件数
FROM fact_crime fc
JOIN dim_outcome o ON fc.outcome_id = o.outcome_id
WHERE o.outcome_type = '处罚型'
GROUP BY o.outcome_cn
ORDER BY 件数 DESC;

-- ------------------------------------------------------------
-- 7. 时空组合查询: "某社区 + 某月 + 某类别"组合(行政区划×时间×属性)
-- ------------------------------------------------------------
SELECT COUNT(*) AS 案件数
FROM fact_crime fc
JOIN dim_location l ON fc.location_id = l.location_id
JOIN dim_neighbourhood n ON l.neighbourhood_id = n.neighbourhood_id
JOIN dim_time t ON fc.time_id = t.time_id
JOIN dim_category c ON fc.category_id = c.category_id
WHERE n.neighbourhood_name = 'Leeds City'
  AND t.month = '2024-06'
  AND c.category_cn = '扰乱公共秩序';

-- ------------------------------------------------------------
-- 8. 使用视图(设计文档中的视图均可直接查询)
-- ------------------------------------------------------------
-- 月度统计
SELECT * FROM v_monthly_stats WHERE 分级 = '轻微' LIMIT 10;
-- 脱敏视图(面向研究/开放)
SELECT * FROM v_masked_crime LIMIT 5;
