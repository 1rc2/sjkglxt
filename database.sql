-- ============================================================
-- 大学生竞赛成果管理系统  数据库脚本
-- 数据库: MySQL 8.0+ (CHECK 约束需 8.0.16 及以上才生效)
-- 使用方法: mysql -u root -p < database.sql
-- ============================================================

-- 1. 创建数据库
CREATE DATABASE IF NOT EXISTS competition_db
    DEFAULT CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE competition_db;

-- ------------------------------------------------------------
-- 2. 建表（注意删除顺序：先删子表再删父表，避免外键冲突）
-- ------------------------------------------------------------
DROP TABLE IF EXISTS record;
DROP TABLE IF EXISTS student;
DROP TABLE IF EXISTS competition;
DROP TABLE IF EXISTS award;
DROP TABLE IF EXISTS depart;

-- 2.1 院系表 depart（一对多的"一"方）
CREATE TABLE depart (
    depart_id   INT PRIMARY KEY AUTO_INCREMENT COMMENT '院系编号(自增主键)',
    depart_name VARCHAR(50) NOT NULL UNIQUE COMMENT '院系名称(非空且唯一)'
) COMMENT '院系表';

-- 2.2 学生表 student
CREATE TABLE student (
    stu_id    CHAR(10)   PRIMARY KEY COMMENT '学号(固定10位数字)',
    name      VARCHAR(50) NOT NULL COMMENT '姓名(非空)',
    gender    VARCHAR(4)  NOT NULL COMMENT '性别(男/女)',
    depart_id INT         NOT NULL COMMENT '所属院系(外键)',
    phone     VARCHAR(20) UNIQUE COMMENT '联系电话(唯一)',
    -- 用户自定义完整性：性别仅允许男/女
    CONSTRAINT chk_student_gender   CHECK (gender IN ('男', '女')),
    -- 用户自定义完整性：学号必须为10位数字
    CONSTRAINT chk_student_stuid    CHECK (stu_id REGEXP '^[0-9]{10}$'),
    -- 参照完整性：院系外键
    CONSTRAINT fk_student_depart    FOREIGN KEY (depart_id)
        REFERENCES depart (depart_id)
) COMMENT '学生表';

-- 2.3 竞赛表 competition
CREATE TABLE competition (
    com_id    INT PRIMARY KEY AUTO_INCREMENT COMMENT '竞赛编号(自增主键)',
    com_name  VARCHAR(100) NOT NULL COMMENT '竞赛名称(非空)',
    level     VARCHAR(20)  NOT NULL COMMENT '竞赛级别(国家级/省级/校级)',
    hold_year INT          NOT NULL COMMENT '举办年份',
    -- 用户自定义完整性：级别仅允许三种
    CONSTRAINT chk_comp_level CHECK (level IN ('国家级', '省级', '校级')),
    -- 用户自定义完整性：年份范围 2000~2026
    CONSTRAINT chk_comp_year  CHECK (hold_year BETWEEN 2000 AND 2026),
    -- 用户自定义完整性：数字字段不能为负数
    CONSTRAINT chk_comp_year_positive CHECK (hold_year >= 0)
) COMMENT '竞赛表';

-- 2.4 奖项表 award
CREATE TABLE award (
    award_id   INT PRIMARY KEY AUTO_INCREMENT COMMENT '奖项编号(自增主键)',
    award_name VARCHAR(50) NOT NULL COMMENT '奖项名称(非空)',
    `rank`     INT         NOT NULL COMMENT '获奖等级(1一等奖/2二等奖/3三等奖)',
    -- 用户自定义完整性：等级仅允许 1/2/3
    CONSTRAINT chk_award_rank CHECK (`rank` IN (1, 2, 3)),
    -- 用户自定义完整性：数字字段不能为负数
    CONSTRAINT chk_award_rank_positive CHECK (`rank` >= 0)
) COMMENT '奖项表';

-- 2.5 参赛记录表 record（多对多关系的中间表，三条外键）
CREATE TABLE record (
    rec_id    INT PRIMARY KEY AUTO_INCREMENT COMMENT '记录编号(自增主键)',
    stu_id    CHAR(10)   NOT NULL COMMENT '参赛学生学号(外键)',
    com_id    INT        NOT NULL COMMENT '参赛竞赛编号(外键)',
    award_id  INT        NOT NULL COMMENT '所获奖项编号(外键)',
    teacher   VARCHAR(50) NOT NULL COMMENT '指导教师(非空)',
    join_year INT        NOT NULL COMMENT '参赛年份',
    -- 用户自定义完整性：年份范围 2000~2026
    CONSTRAINT chk_record_year  CHECK (join_year BETWEEN 2000 AND 2026),
    -- 用户自定义完整性：数字字段不能为负数
    CONSTRAINT chk_record_year_positive CHECK (join_year >= 0),
    -- 参照完整性：三条外键，数据库层面禁止非法外键插入
    CONSTRAINT fk_record_student     FOREIGN KEY (stu_id)   REFERENCES student (stu_id),
    CONSTRAINT fk_record_competition FOREIGN KEY (com_id)   REFERENCES competition (com_id),
    CONSTRAINT fk_record_award       FOREIGN KEY (award_id) REFERENCES award (award_id)
) COMMENT '参赛记录表';

-- ------------------------------------------------------------
-- 3. 插入测试模拟数据
-- ------------------------------------------------------------
-- 3.1 院系数据
INSERT INTO depart (depart_name) VALUES
('计算机学院'),
('电子信息学院'),
('机械工程学院'),
('经济管理学院'),
('外国语学院');

-- 3.2 学生数据
INSERT INTO student (stu_id, name, gender, depart_id, phone) VALUES
('2023001001', '张三',   '男', 1, '13800000001'),
('2023001002', '李四',   '女', 1, '13800000002'),
('2022002001', '王五',   '男', 2, '13800000003'),
('2022002002', '赵六',   '女', 2, '13800000004'),
('2023003001', '孙七',   '男', 3, '13800000005'),
('2021004001', '周八',   '女', 4, '13800000006'),
('2023005001', '吴九',   '女', 5, '13800000007'),
('2022001003', '郑十',   '男', 1, '13800000008'),
('2021001004', '钱十一', '男', 1, '13800000009'),
('2023002003', '冯十二', '女', 2, '13800000010'),
('2022003002', '陈十三', '男', 3, '13800000011'),
('2021003003', '褚十四', '女', 3, '13800000012'),
('2023004002', '卫十五', '女', 4, '13800000013'),
('2022004003', '蒋十六', '男', 4, '13800000014'),
('2021005002', '沈十七', '女', 5, '13800000015'),
('2023001005', '韩十八', '男', 1, '13800000016'),
('2022002004', '杨十九', '男', 2, '13800000017'),
('2021003004', '朱二十', '女', 3, '13800000018'),
('2022005003', '秦二十一','女', 5, '13800000019'),
('2023003005', '尤二十二','男', 3, '13800000020');

-- 3.3 竞赛数据
INSERT INTO competition (com_name, level, hold_year) VALUES
('全国大学生数学建模竞赛',            '国家级', 2023),
('ACM国际大学生程序设计竞赛',         '国家级', 2023),
('蓝桥杯全国软件和信息技术专业人才大赛', '国家级', 2024),
('湖北省大学生电子设计竞赛',          '省级',   2023),
('湖北省大学生机械创新设计大赛',      '省级',   2024),
('武汉科技大学程序设计竞赛',          '校级',   2024),
('全国大学生英语竞赛',                '国家级', 2023),
('校园科技文化节创新创业大赛',        '校级',   2024),
('全国大学生机器人大赛',              '国家级', 2025),
('武汉科技大学数学竞赛',              '校级',   2025);

-- 3.4 奖项数据
INSERT INTO award (award_name, `rank`) VALUES
('一等奖', 1),
('二等奖', 2),
('三等奖', 3);

-- 3.5 参赛记录数据（覆盖多个年份，便于统计）
INSERT INTO record (stu_id, com_id, award_id, teacher, join_year) VALUES
('2023001001', 1, 1, '刘老师', 2023),
('2023001002', 1, 2, '刘老师', 2023),
('2022002001', 2, 2, '陈老师', 2023),
('2022002002', 4, 1, '陈老师', 2023),
('2023003001', 5, 3, '王老师', 2024),
('2021004001', 6, 1, '周老师', 2024),
('2023005001', 7, 2, '吴老师', 2023),
('2022001003', 3, 1, '刘老师', 2024),
('2021001004', 1, 3, '刘老师', 2023),
('2023002003', 4, 2, '陈老师', 2023),
('2022003002', 5, 1, '王老师', 2024),
('2021003003', 6, 3, '周老师', 2024),
('2023004002', 8, 2, '孙老师', 2024),
('2022004003', 6, 2, '周老师', 2024),
('2021005002', 7, 3, '吴老师', 2023),
('2023001005', 3, 2, '刘老师', 2024),
('2022002004', 9, 1, '陈老师', 2025),
('2021003004', 5, 3, '王老师', 2024),
('2022005003', 7, 1, '吴老师', 2023),
('2023003005', 9, 2, '王老师', 2025),
('2023001001', 3, 1, '刘老师', 2024),
('2022002001', 3, 3, '陈老师', 2024),
('2021001004', 10, 2, '刘老师', 2025),
('2023004002', 10, 1, '孙老师', 2025),
('2022003002', 9, 3, '王老师', 2025),
('2023001002', 10, 3, '刘老师', 2025),
('2022004003', 8, 1, '孙老师', 2024);

-- 校验：查看各表数据量
SELECT '院系数量' AS 名称, COUNT(*) AS 数量 FROM depart
UNION ALL SELECT '学生数量', COUNT(*) FROM student
UNION ALL SELECT '竞赛数量', COUNT(*) FROM competition
UNION ALL SELECT '奖项数量', COUNT(*) FROM award
UNION ALL SELECT '记录数量', COUNT(*) FROM record;
