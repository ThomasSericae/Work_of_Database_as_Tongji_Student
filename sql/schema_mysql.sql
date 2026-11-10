-- ============================================================
-- 城市计算之轻微犯罪数据库  ——  建库脚本 (MySQL 8.0)
-- 数据源: 英国警方开放数据 data.police.uk (利兹 Leeds, 2024H1)
-- 设计: 方案A —— 星型模型(时空核心), 全部表可由真实数据填充
-- ============================================================

DROP DATABASE IF EXISTS urban_crime;
CREATE DATABASE urban_crime
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
USE urban_crime;

-- ------------------------------------------------------------
-- 维度表 dim_force : 警署(部门/辖区)
-- ------------------------------------------------------------
CREATE TABLE dim_force (
  force_id    VARCHAR(50)  NOT NULL COMMENT '警署编码',
  force_name  VARCHAR(100) NOT NULL COMMENT '警署名',
  PRIMARY KEY (force_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ------------------------------------------------------------
-- 维度表 dim_neighbourhood : 社区(行政区划层级)
-- ------------------------------------------------------------
CREATE TABLE dim_neighbourhood (
  neighbourhood_id   VARCHAR(20)  NOT NULL COMMENT '社区编码',
  neighbourhood_name VARCHAR(100) NOT NULL COMMENT '社区名',
  force_id           VARCHAR(50)  NOT NULL COMMENT '所属警署',
  PRIMARY KEY (neighbourhood_id),
  CONSTRAINT fk_nb_force FOREIGN KEY (force_id)
    REFERENCES dim_force (force_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ------------------------------------------------------------
-- 维度表 dim_location : 地点(空间维度, 点模型)
--   坐标以 DECIMAL(10,7) 存储, 不启用 PostGIS; 半径查询用平方距离
-- ------------------------------------------------------------
CREATE TABLE dim_location (
  location_id      BIGINT        NOT NULL COMMENT '地点代理键',
  street_id        BIGINT        NOT NULL COMMENT '街道标识(数据源自然键)',
  street_name      VARCHAR(200)  NULL     COMMENT '街道文本(On or near ...)',
  latitude         DECIMAL(10,7) NULL     COMMENT '纬度',
  longitude        DECIMAL(10,7) NULL     COMMENT '经度',
  neighbourhood_id VARCHAR(20)   NULL     COMMENT '所属社区(点在多边形内判定回填)',
  PRIMARY KEY (location_id),
  UNIQUE KEY uk_location_street (street_id),
  CONSTRAINT fk_loc_nb FOREIGN KEY (neighbourhood_id)
    REFERENCES dim_neighbourhood (neighbourhood_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ------------------------------------------------------------
-- 维度表 dim_time : 时间维度
-- ------------------------------------------------------------
CREATE TABLE dim_time (
  time_id   SMALLINT     NOT NULL COMMENT '时间代理键',
  month     CHAR(7)      NOT NULL COMMENT 'YYYY-MM',
  year      SMALLINT     NOT NULL COMMENT '年份',
  month_num TINYINT      NOT NULL COMMENT '月份 1-12',
  quarter   TINYINT      NOT NULL COMMENT '季度 1-4',
  season    VARCHAR(10)  NULL     COMMENT '季节',
  PRIMARY KEY (time_id),
  UNIQUE KEY uk_time_month (month)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ------------------------------------------------------------
-- 维度表 dim_category : 犯罪类别(含轻微犯罪分级)
-- ------------------------------------------------------------
CREATE TABLE dim_category (
  category_id    SMALLINT     NOT NULL COMMENT '类别代理键',
  category_name  VARCHAR(50)  NOT NULL COMMENT '类别英文名',
  category_cn    VARCHAR(50)  NULL     COMMENT '类别中文名',
  severity_level VARCHAR(20)  NOT NULL COMMENT '轻微/一般/较重/严重',
  PRIMARY KEY (category_id),
  UNIQUE KEY uk_category_name (category_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ------------------------------------------------------------
-- 维度表 dim_outcome : 处理结果(处罚方式)
--   处罚型=警告/罚款通知/社区判决/现场调解; 另有终止型与未决型
-- ------------------------------------------------------------
CREATE TABLE dim_outcome (
  outcome_id   SMALLINT     NOT NULL COMMENT '结果代理键',
  outcome_name VARCHAR(100) NOT NULL COMMENT '处理结果英文',
  outcome_cn   VARCHAR(100) NULL     COMMENT '处理结果中文',
  outcome_type VARCHAR(20)  NULL     COMMENT '处罚型/终止型/未决型',
  PRIMARY KEY (outcome_id),
  UNIQUE KEY uk_outcome_name (outcome_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ------------------------------------------------------------
-- 事实表 fact_crime : 案件记录(时空事件)
-- ------------------------------------------------------------
CREATE TABLE fact_crime (
  crime_id         BIGINT       NOT NULL COMMENT '案件记录号(数据源 id)',
  persistent_id    VARCHAR(64)  NULL     COMMENT '稳定案件号(跨月追踪,可空)',
  time_id          SMALLINT     NOT NULL COMMENT '发生时间',
  category_id      SMALLINT     NOT NULL COMMENT '犯罪类别',
  location_id      BIGINT       NULL     COMMENT '发生地点(可空, Force级精度无坐标)',
  outcome_id       SMALLINT     NULL     COMMENT '处理结果(可空, 未结案)',
  context          VARCHAR(500) NULL     COMMENT '附加信息',
  location_type    VARCHAR(20)  NULL     COMMENT '定位精度 Force/Neighbourhood/BTP',
  location_subtype VARCHAR(50)  NULL     COMMENT '精度子类',
  PRIMARY KEY (crime_id),
  CONSTRAINT fk_fc_time FOREIGN KEY (time_id)     REFERENCES dim_time (time_id),
  CONSTRAINT fk_fc_cat  FOREIGN KEY (category_id) REFERENCES dim_category (category_id),
  CONSTRAINT fk_fc_loc  FOREIGN KEY (location_id) REFERENCES dim_location (location_id),
  CONSTRAINT fk_fc_out  FOREIGN KEY (outcome_id)  REFERENCES dim_outcome (outcome_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- 索引设计
--   (MySQL 对主键/UNIQUE 自动建 B+树索引; 下列为外键与业务查询索引)
-- ============================================================

-- 外键索引
CREATE INDEX idx_fc_time ON fact_crime (time_id);
CREATE INDEX idx_fc_cat  ON fact_crime (category_id);
CREATE INDEX idx_fc_loc  ON fact_crime (location_id);
CREATE INDEX idx_fc_out  ON fact_crime (outcome_id);
CREATE INDEX idx_loc_nb  ON dim_location (neighbourhood_id);

-- 业务查询索引
CREATE INDEX idx_fc_persistent ON fact_crime (persistent_id);      -- 按稳定案件号追踪
CREATE INDEX idx_fc_type       ON fact_crime (location_type);      -- 按定位精度过滤
CREATE INDEX idx_cat_severity  ON dim_category (severity_level);   -- 轻微犯罪筛选
CREATE INDEX idx_out_type      ON dim_outcome (outcome_type);      -- 处罚型筛选
CREATE INDEX idx_loc_coord     ON dim_location (latitude, longitude); -- 矩形范围粗筛

-- ============================================================
-- 视图设计
-- ============================================================

-- 1. 案件全景视图: 暴露可读字段, 隐藏代理键
CREATE OR REPLACE VIEW v_case_overview AS
SELECT
  fc.crime_id                       AS 案件号,
  fc.persistent_id                  AS 稳定案件号,
  t.month                           AS 发生月份,
  t.year                            AS 年份,
  t.quarter                         AS 季度,
  c.category_name                   AS 犯罪类别,
  c.category_cn                     AS 类别中文名,
  c.severity_level                  AS 轻微犯罪分级,
  l.street_name                     AS 发生街道,
  l.latitude                        AS 纬度,
  l.longitude                       AS 经度,
  o.outcome_name                    AS 处理结果,
  o.outcome_cn                      AS 处理结果中文,
  o.outcome_type                    AS 处理类型,
  fc.context                        AS 附加信息
FROM fact_crime fc
LEFT JOIN dim_time t       ON fc.time_id     = t.time_id
LEFT JOIN dim_category c   ON fc.category_id = c.category_id
LEFT JOIN dim_location l   ON fc.location_id = l.location_id
LEFT JOIN dim_outcome o    ON fc.outcome_id  = o.outcome_id;

-- 2. 月度案件统计视图(只读分析型, 不涉及个人隐私)
CREATE OR REPLACE VIEW v_monthly_stats AS
SELECT
  t.year            AS 年份,
  t.month           AS 月份,
  c.category_cn     AS 犯罪类别,
  c.severity_level  AS 分级,
  COUNT(*)          AS 案件数
FROM fact_crime fc
JOIN dim_time t     ON fc.time_id     = t.time_id
JOIN dim_category c ON fc.category_id = c.category_id
GROUP BY t.year, t.month, c.category_cn, c.severity_level;

-- 3. 社区治安热点视图: 按社区聚合, 只到社区级不暴露具体位置
CREATE OR REPLACE VIEW v_community_hotspot AS
SELECT
  n.neighbourhood_name AS 社区,
  t.month              AS 月份,
  c.category_cn        AS 犯罪类别,
  COUNT(*)             AS 案件数
FROM fact_crime fc
JOIN dim_location l   ON fc.location_id = l.location_id
LEFT JOIN dim_neighbourhood n ON l.neighbourhood_id = n.neighbourhood_id
JOIN dim_time t       ON fc.time_id     = t.time_id
JOIN dim_category c   ON fc.category_id = c.category_id
GROUP BY n.neighbourhood_name, t.month, c.category_cn;

-- 4. 脱敏案件视图: 面向研究/开放, 隐藏稳定案件号与精确街道
CREATE OR REPLACE VIEW v_masked_crime AS
SELECT
  fc.crime_id                        AS 案件号,
  t.month                            AS 发生月份,
  c.category_name                    AS 犯罪类别,
  c.severity_level                   AS 分级,
  ROUND(l.latitude, 3)               AS 纬度_模糊,
  ROUND(l.longitude, 3)              AS 经度_模糊,
  o.outcome_cn                       AS 处理结果
FROM fact_crime fc
LEFT JOIN dim_time t     ON fc.time_id     = t.time_id
LEFT JOIN dim_category c ON fc.category_id = c.category_id
LEFT JOIN dim_location l ON fc.location_id = l.location_id
LEFT JOIN dim_outcome o  ON fc.outcome_id  = o.outcome_id;
