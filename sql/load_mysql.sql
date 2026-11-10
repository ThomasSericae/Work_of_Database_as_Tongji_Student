-- ============================================================
-- 数据导入脚本 (MySQL 8.0)
-- 先执行 sql/schema_mysql.sql 建库建表, 再执行本文件导入 data/db/*.csv
-- 注意: 请把下面的路径改成你机器上 data/db 的绝对路径; 若 MySQL 服务与文件
--       不在同一台机器, 需开启 local_infile=ON 并用 LOAD DATA LOCAL INFILE。
--       也可用 Navicat / DataGrip / phpMyAdmin 的"导入向导"按表逐个导入 CSV,
--       (首行标题自动跳过), 效果相同。
-- ============================================================

USE urban_crime;
SET NAMES utf8mb4;

-- 1. 警署
LOAD DATA LOCAL INFILE 'D:/python_study/SQLwork/data/db/dim_force.csv'
INTO TABLE dim_force
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(force_id, force_name);

-- 2. 社区
LOAD DATA LOCAL INFILE 'D:/python_study/SQLwork/data/db/dim_neighbourhood.csv'
INTO TABLE dim_neighbourhood
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(neighbourhood_id, neighbourhood_name, force_id);

-- 3. 犯罪类别
LOAD DATA LOCAL INFILE 'D:/python_study/SQLwork/data/db/dim_category.csv'
INTO TABLE dim_category
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(category_id, category_name, category_cn, severity_level);

-- 4. 处理结果
LOAD DATA LOCAL INFILE 'D:/python_study/SQLwork/data/db/dim_outcome.csv'
INTO TABLE dim_outcome
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(outcome_id, outcome_name, outcome_cn, outcome_type);

-- 5. 时间
LOAD DATA LOCAL INFILE 'D:/python_study/SQLwork/data/db/dim_time.csv'
INTO TABLE dim_time
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(time_id, month, year, month_num, quarter, season);

-- 6. 地点 (neighbourhood_id 为空串 -> NULL)
LOAD DATA LOCAL INFILE 'D:/python_study/SQLwork/data/db/dim_location.csv'
INTO TABLE dim_location
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(location_id, street_id, street_name, @latitude, @longitude, @neighbourhood_id)
SET latitude        = NULLIF(@latitude, ''),
    longitude       = NULLIF(@longitude, ''),
    neighbourhood_id = NULLIF(@neighbourhood_id, '');

-- 7. 案件事实 (空外键 -> NULL)
LOAD DATA LOCAL INFILE 'D:/python_study/SQLwork/data/db/fact_crime.csv'
INTO TABLE fact_crime
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(crime_id, @persistent_id, time_id, category_id, @location_id, @outcome_id,
 context, location_type, location_subtype)
SET persistent_id = NULLIF(@persistent_id, ''),
    location_id   = NULLIF(@location_id, ''),
    outcome_id    = NULLIF(@outcome_id, '');
