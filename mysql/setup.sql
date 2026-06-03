-- ============================================================
-- MySQL Tutorial — 一键初始化脚本
-- 功能：建库 → 建表 → 约束 → 索引 → 造数据
-- 使用：mysql -u root -padmin < setup.sql
-- 可重复执行（幂等）
-- ============================================================

DROP DATABASE IF EXISTS mysql_tutorial;

CREATE DATABASE mysql_tutorial
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE mysql_tutorial;

-- ============================================================
-- 1. 商品分类表 (自引用：parent_id 指向自身，支持多级分类)
-- ============================================================
CREATE TABLE categories (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(50)  NOT NULL COMMENT '分类名称',
    parent_id   INT          DEFAULT NULL COMMENT '父分类ID，NULL表示一级分类',
    sort_order  INT          DEFAULT 0 COMMENT '排序权重',
    created_at  DATETIME     DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_id) REFERENCES categories(id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    INDEX idx_parent (parent_id)
) COMMENT '商品分类（支持无限层级）';

-- ============================================================
-- 2. 供应商表
-- ============================================================
CREATE TABLE suppliers (
    id      INT AUTO_INCREMENT PRIMARY KEY,
    name    VARCHAR(80)  NOT NULL COMMENT '供应商名称',
    contact VARCHAR(30)  DEFAULT NULL COMMENT '联系人',
    phone   VARCHAR(20)  DEFAULT NULL COMMENT '联系电话',
    city    VARCHAR(30)  DEFAULT NULL COMMENT '所在城市',
    rating  DECIMAL(2,1) DEFAULT 5.0 COMMENT '评分 0~5',
    INDEX idx_city (city)
) COMMENT '供应商';

-- ============================================================
-- 3. 商品表
-- ============================================================
CREATE TABLE products (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(100)   NOT NULL COMMENT '商品名称',
    category_id INT            DEFAULT NULL COMMENT '所属分类',
    supplier_id INT            DEFAULT NULL COMMENT '供应商',
    price       DECIMAL(10,2)  NOT NULL COMMENT '售价',
    cost        DECIMAL(10,2)  DEFAULT NULL COMMENT '成本价',
    stock       INT            DEFAULT 0 COMMENT '库存量',
    unit        VARCHAR(10)    DEFAULT '件' COMMENT '单位',
    description TEXT           DEFAULT NULL COMMENT '商品描述',
    created_at  DATETIME       DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    INDEX idx_category (category_id),
    INDEX idx_price (price),
    INDEX idx_category_price (category_id, price)  -- 复合索引，演示最左前缀
) COMMENT '商品';

-- ============================================================
-- 4. 客户表
-- ============================================================
CREATE TABLE customers (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    name          VARCHAR(50)  NOT NULL COMMENT '姓名',
    email         VARCHAR(80)  DEFAULT NULL COMMENT '邮箱',
    phone         VARCHAR(20)  DEFAULT NULL COMMENT '手机号',
    city          VARCHAR(30)  DEFAULT NULL COMMENT '城市',
    gender        ENUM('男','女','未知') DEFAULT '未知' COMMENT '性别',
    vip_level     TINYINT      DEFAULT 0 COMMENT 'VIP等级 0-5',
    register_date DATE         DEFAULT NULL COMMENT '注册日期',
    INDEX idx_city (city),
    INDEX idx_register (register_date),
    UNIQUE INDEX idx_email (email)
) COMMENT '客户';

-- ============================================================
-- 5. 订单主表
-- ============================================================
CREATE TABLE orders (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT            NOT NULL COMMENT '下单客户',
    order_date  DATETIME       DEFAULT CURRENT_TIMESTAMP COMMENT '下单时间',
    total_amount DECIMAL(12,2) DEFAULT 0.00 COMMENT '订单总金额',
    status      ENUM('pending','paid','shipped','delivered','cancelled')
                DEFAULT 'pending' COMMENT '订单状态',
    remark      VARCHAR(200)   DEFAULT NULL COMMENT '备注',
    FOREIGN KEY (customer_id) REFERENCES customers(id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    INDEX idx_customer (customer_id),
    INDEX idx_order_date (order_date),
    INDEX idx_customer_date (customer_id, order_date),
    INDEX idx_status (status)
) COMMENT '订单主表';

-- ============================================================
-- 6. 订单明细表
-- ============================================================
CREATE TABLE order_items (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    order_id    INT            NOT NULL COMMENT '所属订单',
    product_id  INT            DEFAULT NULL COMMENT '商品',
    quantity    INT            NOT NULL DEFAULT 1 COMMENT '购买数量',
    unit_price  DECIMAL(10,2)  NOT NULL COMMENT '下单时的单价',
    FOREIGN KEY (order_id) REFERENCES orders(id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    INDEX idx_order (order_id),
    INDEX idx_product (product_id),
    INDEX idx_order_product (order_id, product_id)
) COMMENT '订单明细';

-- ============================================================
-- 7. 审计日志表 (供触发器章节使用)
-- ============================================================
CREATE TABLE audit_log (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    table_name  VARCHAR(50)  NOT NULL COMMENT '操作的表',
    operation   ENUM('INSERT','UPDATE','DELETE') NOT NULL COMMENT '操作类型',
    record_id   INT          DEFAULT NULL COMMENT '被操作记录的ID',
    old_data    JSON         DEFAULT NULL COMMENT '变更前数据',
    new_data    JSON         DEFAULT NULL COMMENT '变更后数据',
    changed_at  DATETIME     DEFAULT CURRENT_TIMESTAMP COMMENT '变更时间',
    INDEX idx_table_time (table_name, changed_at)
) COMMENT '审计日志';

-- ============================================================
-- ====================== 插入种子数据 ========================
-- ============================================================

-- ---- 分类数据（3级分类：一级 → 二级 → 三级）----
INSERT INTO categories (id, name, parent_id, sort_order) VALUES
(1,  '数码电子',  NULL, 1),
(2,  '服装鞋帽',  NULL, 2),
(3,  '食品饮料',  NULL, 3),
(4,  '图书音像',  NULL, 4),
(5,  '家用电器',  NULL, 5),
(6,  '手机通讯',  1,    1),   -- 数码电子 → 手机通讯
(7,  '电脑办公',  1,    2),   -- 数码电子 → 电脑办公
(8,  '男装',      2,    1),   -- 服装鞋帽 → 男装
(9,  '女装',      2,    2),   -- 服装鞋帽 → 女装
(10, '休闲零食',  3,    1),   -- 食品饮料 → 休闲零食
(11, '智能手机',  6,    1),   -- 手机通讯 → 智能手机
(12, '轻薄本',    7,    1);   -- 电脑办公 → 轻薄本

-- ---- 供应商数据 ----
INSERT INTO suppliers (id, name, contact, phone, city, rating) VALUES
(1,  '深圳华强电子',   '张总', '13800001001', '深圳', 4.8),
(2,  '杭州数码科技',   '李经理','13800001002', '杭州', 4.5),
(3,  '广州服装贸易',   '王总', '13800001003', '广州', 4.2),
(4,  '北京食品集团',   '赵经理','13800001004', '北京', 4.6),
(5,  '上海文化出版',   '钱总', '13800001005', '上海', 4.0),
(6,  '成都电器制造',   '周经理','13800001006', '成都', 4.7),
(7,  '武汉通信科技',   '吴总', '13800001007', '武汉', 4.3),
(8,  '南京云商集团',   '郑经理', NULL,       '南京', 3.9),
(9,  '重庆百货供应',   '刘总', '13800001009', '重庆', 4.1),
(10, '东莞制造工厂',   '陈经理','13800001010', '东莞', 4.4);

-- ---- 商品数据（50个商品，覆盖不同分类和价格带）----
INSERT INTO products (id, name, category_id, supplier_id, price, cost, stock, unit, description) VALUES
-- 智能手机
(1,  '华为 Mate 70 Pro',       11, 1,  6999.00,  5500.00, 200, '台', '旗舰智能手机，麒麟芯片'),
(2,  '小米 15 Ultra',          11, 2,  5999.00,  4800.00, 150, '台', '骁龙8 Elite，徕卡影像'),
(3,  'OPPO Find X8 Pro',       11, 2,  4999.00,  3900.00, 180, '台', '哈苏人像摄影'),
(4,  'vivo X200 Pro',          11, 7,  4799.00,  3700.00, 120, '台', '蔡司超级长焦'),
(5,  'iPhone 16 Pro Max',      11, 1,  9999.00,  8200.00,  80, '台', 'A18 Pro 芯片'),
-- 轻薄本
(6,  'MacBook Pro 16',          12, 1, 19999.00, 17000.00,  50, '台', 'M4 Max 芯片'),
(7,  '华为 MateBook X Pro',     12, 2, 12999.00, 10500.00,  60, '台', '3K OLED 原色屏'),
(8,  '联想 ThinkPad X1 Carbon', 12, 2,  9999.00,  8200.00,  70, '台', '商务旗舰轻薄本'),
(9,  '小米笔记本 Pro 16',       12, 2,  6999.00,  5700.00,  90, '台', '12代酷睿，2.5K屏'),
-- 男装
(10, '商务休闲西装外套',         8, 3,   699.00,   400.00, 300, '件', '羊毛混纺，修身版型'),
(11, '纯棉牛津纺衬衫',           8, 3,   299.00,   150.00, 500, '件', '100%纯棉，不易皱'),
(12, '男士牛仔裤',               8, 3,   399.00,   200.00, 400, '条', '弹力棉，直筒版型'),
(13, '秋冬羽绒服',               8, 3,  1299.00,   700.00, 150, '件', '90%白鹅绒填充'),
-- 女装
(14, '碎花连衣裙',               9, 3,   459.00,   230.00, 250, '件', '雪纺面料，收腰设计'),
(15, '羊毛呢大衣',               9, 3,  1899.00,  1100.00, 100, '件', '双面羊毛，经典驼色'),
(16, '高腰阔腿裤',               9, 3,   329.00,   160.00, 350, '条', '垂感面料，显瘦'),
-- 休闲零食
(17, '每日坚果礼盒',            10, 4,    89.00,    50.00, 800, '盒', '7种坚果混合'),
(18, '有机蓝莓干',              10, 4,    35.00,    18.00, 600, '袋', '无添加蔗糖'),
(19, '薯片大礼包',              10, 4,    49.90,    28.00, 400, '包', '6种口味组合'),
(20, '巧克力夹心饼干',          10, 4,    25.00,    12.00, 500, '盒', '进口可可脂'),
-- 数码配件（二级分类：数码电子 → 挂一级）
(21, 'Type-C 数据线',            1, 1,    29.90,    12.00, 2000,'根', '100W快充'),
(22, '无线蓝牙耳机',            1, 1,   299.00,   150.00, 500, '副', 'ENC降噪，续航30h'),
(23, '充电宝 20000mAh',          1, 2,   149.00,    80.00, 600, '个', '22.5W超级快充'),
(24, '机械键盘 87键',            1, 2,   349.00,   200.00, 200, '个', 'Cherry轴体'),
-- 家电
(25, '智能扫地机器人',           5, 6,  2499.00,  1700.00, 100, '台', 'LDS激光导航'),
(26, '空气净化器',               5, 6,  1599.00,  1000.00, 120, '台', 'HEPA滤网，静音'),
(27, '电热水壶 1.7L',            5, 6,    89.00,    45.00, 400, '个', '304不锈钢'),
(28, '无叶风扇',                 5, 6,   599.00,   350.00, 180, '台', '遥控定时，静音'),
-- 图书
(29, 'MySQL实战45讲',           4, 5,    79.00,    45.00, 300, '本', '丁奇 著'),
(30, '高性能MySQL 第4版',        4, 5,   128.00,    75.00, 200, '本', '施瓦茨 著'),
(31, '数据仓库工具箱 第3版',      4, 5,    99.00,    58.00, 150, '本', 'Kimball 维度建模'),
(32, '深入浅出数据分析',          4, 5,    69.00,    40.00, 250, '本', '统计学入门经典'),
-- 更多商品（用于呈现足够的数据量）
(33, '无线充电器 15W',           1, 7,    79.00,    35.00, 350, '个', 'MagSafe兼容'),
(34, 'iPad Air 13',              7, 1,  6499.00,  5200.00,  55, '台', 'M4 芯片'),
(35, '运动卫衣',                 8, 3,   259.00,   120.00, 320, '件', '加绒保暖'),
(36, '真皮腰带',                 8, 3,   169.00,    70.00, 400, '条', '头层牛皮'),
(37, '半身裙',                   9, 3,   289.00,   140.00, 220, '条', 'A字版型'),
(38, '全麦面包',                10, 4,    16.90,     8.00, 300, '袋', '无糖低脂'),
(39, '智能手表',                 1, 1,  2299.00,  1600.00, 130, '块', '心率血氧监测'),
(40, '移动固态硬盘 1TB',         7, 7,   499.00,   320.00, 250, '个', 'USB 3.2 读写'),
(41, '女士运动鞋',               9, 3,   599.00,   320.00, 280, '双', '气垫缓震'),
(42, '男士皮鞋',                 8, 3,   799.00,   450.00, 160, '双', '头层牛皮'),
(43, '混合坚果',                10, 4,    69.00,    38.00, 350, '罐', '每日坚果系列'),
(44, '游戏鼠标',                 1, 2,   259.00,   130.00, 300, '个', '16000DPI'),
(45, '加湿器',                   5, 6,   199.00,   110.00, 200, '台', '4L大容量'),
(46, '华为平板 MatePad Pro',     7, 2,  4299.00,  3400.00,  65, '台', 'OLED全面屏'),
(47, 'TWS降噪耳机',              1, 2,   699.00,   420.00, 220, '副', '空间音频'),
(48, '运动毛巾',                 8, 10,   39.00,    15.00,   NULL, '条', '速干材质'),  -- stock为NULL，演示NULL处理
(49, '无糖薄荷糖',              10, 4,    12.90,     5.50, 900, '盒', '清新口气'),
(50, '迷你电饭煲 2L',            5, 6,   229.00,   130.00, 170, '个', '预约定时');

-- ---- 客户数据（100个客户）----
INSERT INTO customers (id, name, email, phone, city, gender, vip_level, register_date) VALUES
(1,  '张伟',   'zhangwei@email.com',   '13900000001', '北京', '男',  3, '2023-01-15'),
(2,  '李娜',   'lina@email.com',       '13900000002', '上海', '女',  4, '2023-02-20'),
(3,  '王强',   'wangqiang@email.com',  '13900000003', '广州', '男',  2, '2023-03-10'),
(4,  '赵敏',   'zhaomin@email.com',    '13900000004', '深圳', '女',  1, '2023-04-05'),
(5,  '刘洋',   'liuyang@email.com',    '13900000005', '杭州', '男',  5, '2023-01-28'),
(6,  '陈静',   'chenjing@email.com',   '13900000006', '成都', '女',  2, '2023-05-12'),
(7,  '杨磊',   'yanglei@email.com',    '13900000007', '武汉', '男',  0, '2023-06-18'),
(8,  '周婷',   'zhouting@email.com',   '13900000008', '南京', '女',  3, '2023-02-14'),
(9,  '吴昊',   'wuhao@email.com',      '13900000009', '重庆', '男',  1, '2023-07-22'),
(10, '孙悦',   'sunyue@email.com',     '13900000010', '北京', '女',  4, '2023-03-08'),
(11, '马超',   'machao@email.com',     '13900000011', '上海', '男',  2, '2023-08-30'),
(12, '黄丽',   'huangli@email.com',    '13900000012', '广州', '女',  0, '2023-04-17'),
(13, '朱涛',   'zhutao@email.com',     '13900000013', '深圳', '男',  3, '2023-01-01'),
(14, '林芳',   'linfang@email.com',    '13900000014', '杭州', '女',  5, '2023-05-25'),
(15, '何军',   'hejun@email.com',      '13900000015', '成都', '男',  1, '2023-06-03'),
(16, '胡雪',   'huxue@email.com',      '13900000016', '武汉', '女',  2, '2023-07-11'),
(17, '郭鹏',   'guopeng@email.com',    '13900000017', '南京', '男',  4, '2023-02-28'),
(18, '罗敏',   'luomin@email.com',     '13900000018', '重庆', '女',  0, '2023-08-15'),
(19, '梁龙',   'lianglong@email.com',  '13900000019', '北京', '男',  5, '2023-03-22'),
(20, '宋佳',   'songjia@email.com',    '13900000020', '上海', '女',  3, '2023-04-09'),
(21, '唐晨',   'tangchen@email.com',   '13900000021', '广州', '男',  1, '2023-10-05'),
(22, '韩冰',   'hanbing@email.com',    '13900000022', '深圳', '女',  2, '2023-11-12'),
(23, '冯雷',   'fenglei@email.com',    '13900000023', '杭州', '男',  0, '2023-12-01'),
(24, '曹慧',   'caohui@email.com',     '13900000024', '成都', '女',  4, '2023-01-20'),
(25, '邓辉',   'denghui@email.com',    '13900000025', '武汉', '男',  3, '2023-02-15'),
(26, '许洁',   'xujie@email.com',      '13900000026', '南京', '女',  1, '2023-03-18'),
(27, '沈飞',   'shenfei@email.com',    '13900000027', '重庆', '男',  2, '2023-04-22'),
(28, '彭婷',   'pengting@email.com',   '13900000028', '北京', '女',  5, '2023-05-07'),
(29, '吕明',   'lvming@email.com',     '13900000029', '上海', '男',  0, '2023-06-14'),
(30, '苏瑶',   'suyao@email.com',      '13900000030', '广州', '女',  3, '2023-07-19'),
-- 以下30个客户无邮箱，用于演示NULL处理
(31, '蒋伟',   NULL,                   '13900000031', '深圳', '男',  1, '2023-08-25'),
(32, '蔡琳',   NULL,                   '13900000032', '杭州', '女',  2, '2023-09-03'),
(33, '潘峰',   NULL,                   '13900000033', '成都', '男',  4, '2023-10-10'),
(34, '田芳',   NULL,                   '13900000034', '武汉', '女',  0, '2023-11-19'),
(35, '丁浩',   NULL,                   '13900000035', '南京', '男',  3, '2023-12-25'),
(36, '魏红',   NULL,                   '13900000036', '重庆', '女',  1, '2024-01-08'),
(37, '薛磊',   NULL,                   '13900000037', '北京', '男',  5, '2024-01-15'),
(38, '叶静',   NULL,                   '13900000038', '上海', '女',  2, '2024-02-01'),
(39, '闫涛',   'yantao@email.com',     NULL,        '广州', '男',  0, '2024-02-14'),
(40, '余敏',   'yumin@email.com',      NULL,        '深圳', '女',  4, '2024-02-28'),
(41, '戴强',   'daiqiang@email.com',   '13900000041', '杭州', '男',  1, '2024-03-05'),
(42, '夏雪',   'xiaxue@email.com',     '13900000042', '成都', '女',  3, '2024-03-12'),
(43, '钟雷',   'zhonglei@email.com',   '13900000043', '武汉', '男',  2, '2024-03-19'),
(44, '姚丽',   'yaoli@email.com',      '13900000044', '南京', '女',  5, '2024-03-26'),
(45, '汪洋',   'wangyang@email.com',   '13900000045', '重庆', '男',  0, '2024-04-02'),
(46, '任静',   'renjing@email.com',    '13900000046', '北京', '女',  1, '2024-04-09'),
(47, '姜龙',   'jianglong@email.com',  '13900000047', '上海', '男',  4, '2024-04-16'),
(48, '范芳',   'fanfang@email.com',    '13900000048', '广州', '女',  2, '2024-04-23'),
(49, '方晨',   'fangchen@email.com',   '13900000049', '深圳', '男',  3, '2024-04-30'),
(50, '石磊',   'shilei@email.com',     '13900000050', '杭州', '男',  1, '2024-05-07'),
-- 最后50个客户，覆盖更多城市和VIP等级
(51, '崔浩',   'cuihao@email.com',     '13900000051', '成都', '男',  5, '2024-01-01'),
(52, '康婷',   'kangting@email.com',   '13900000052', '武汉', '女',  2, '2024-01-05'),
(53, '邱明',   'qiuming@email.com',    '13900000053', '南京', '男',  0, '2024-01-10'),
(54, '秦丽',   'qinli@email.com',      '13900000054', '重庆', '女',  3, '2024-01-15'),
(55, '江华',   'jianghua@email.com',   '13900000055', '北京', '男',  1, '2024-01-20'),
(56, '史敏',   'shimin@email.com',     '13900000056', '上海', '女',  4, '2024-01-25'),
(57, '顾洋',   'guyang@email.com',     '13900000057', '广州', '男',  2, '2024-02-01'),
(58, '侯婷',   'houting@email.com',    '13900000058', '深圳', '女',  0, '2024-02-05'),
(59, '邵伟',   'shaowei@email.com',    '13900000059', '杭州', '男',  5, '2024-02-10'),
(60, '孟雪',   'mengxue@email.com',    '13900000060', '成都', '女',  1, '2024-02-15'),
(61, '龙涛',   'longtao@email.com',    '13900000061', '武汉', '男',  3, '2024-02-20'),
(62, '万芳',   'wanfang@email.com',    '13900000062', '南京', '女',  2, '2024-02-25'),
(63, '段磊',   'duanlei@email.com',    '13900000063', '重庆', '男',  4, '2024-03-01'),
(64, '雷静',   'leijing@email.com',    '13900000064', '北京', '女',  0, '2024-03-05'),
(65, '钱洋',   'qianyang@email.com',   '13900000065', '上海', '男',  1, '2024-03-10'),
(66, '汤丽',   'tangli@email.com',     '13900000066', '广州', '女',  5, '2024-03-15'),
(67, '尹浩',   'yinhao@email.com',     '13900000067', '深圳', '男',  2, '2024-03-20'),
(68, '易敏',   'yimin@email.com',      '13900000068', '杭州', '女',  3, '2024-03-25'),
(69, '常龙',   'changlong@email.com',  '13900000069', '成都', '男',  0, '2024-03-30'),
(70, '武芬',   'wufen@email.com',      '13900000070', '武汉', '女',  4, '2024-04-01'),
(71, '乔伟',   'qiaowei@email.com',    '13900000071', '南京', '男',  1, '2024-04-05'),
(72, '贺雪',   'hexue@email.com',      '13900000072', '重庆', '女',  2, '2024-04-10'),
(73, '赖涛',   'laitao@email.com',     '13900000073', '北京', '男',  5, '2024-04-15'),
(74, '龚丽',   'gongli@email.com',     '13900000074', '上海', '女',  3, '2024-04-20'),
(75, '文强',   'wenqiang@email.com',   '13900000075', '广州', '男',  0, '2024-04-25'),
(76, '庞静',   'pangjing@email.com',   '13900000076', '深圳', '女',  1, '2024-05-01'),
(77, '樊磊',   'fanlei@email.com',     '13900000077', '杭州', '男',  4, '2024-05-05'),
(78, '兰敏',   'lanmin@email.com',     '13900000078', '成都', '女',  2, '2024-05-10'),
(79, '殷浩',   'yinhao2@email.com',    '13900000079', '武汉', '男',  1, '2024-05-15'),
(80, '施婷',   'shiting@email.com',    '13900000080', '南京', '女',  5, '2024-05-20'),
(81, '陶明',   'taoming@email.com',    '13900000081', '重庆', '男',  0, '2024-05-25'),
(82, '洪丽',   'hongli@email.com',     '13900000082', '北京', '女',  3, '2024-06-01'),
(83, '包伟',   'baowei@email.com',     '13900000083', '上海', '男',  2, '2024-06-05'),
(84, '左雪',   'zuoxue@email.com',    '13900000084', '广州', '女',  4, '2024-06-10'),
(85, '吉涛',   'jitao@email.com',     '13900000085', '深圳', '男',  1, '2024-06-15'),
(86, '盛芳',   'shengfang@email.com',  '13900000086', '杭州', '女',  0, '2024-06-20'),
(87, '凌磊',   'linglei@email.com',    '13900000087', '成都', '男',  5, '2024-06-25'),
(88, '颜静',   'yanjing@email.com',    '13900000088', '武汉', '女',  3, '2024-07-01'),
(89, '华伟',   'huawei@email.com',     '13900000089', '南京', '男',  1, '2024-07-05'),
(90, '梅丽',   'meili@email.com',      '13900000090', '重庆', '女',  2, '2024-07-10'),
(91, '邢涛',   'xingtao@email.com',    '13900000091', '北京', '男',  4, '2024-07-15'),
(92, '舒敏',   'shumin@email.com',     '13900000092', '上海', '女',  0, '2024-07-20'),
(93, '欧雷',   'oulei@email.com',      '13900000093', '广州', '男',  1, '2024-07-25'),
(94, '米婷',   'miting@email.com',     '13900000094', '深圳', '女',  5, '2024-08-01'),
(95, '纪强',   'jiqiang@email.com',    '13900000095', '杭州', '男',  2, '2024-08-05'),
(96, '舒慧',   'shuhui@email.com',     '13900000096', '成都', '女',  3, '2024-08-10'),
(97, '屈明',   'quming@email.com',     '13900000097', '武汉', '男',  0, '2024-08-15'),
(98, '褚丽',   'chuli@email.com',      '13900000098', '南京', '女',  4, '2024-08-20'),
(99, '卫伟',   'weiwei@email.com',     '13900000099', '重庆', '男',  1, '2024-08-25'),
(100,'甄芳',   'zhenfang@email.com',   '13900000100', '北京', '女', 3, '2024-09-01');

-- ---- 订单数据（约500个订单，分布在2023-2024年）----
-- 通过存储过程批量生成，覆盖多种状态

DELIMITER //
CREATE PROCEDURE generate_orders()
BEGIN
    DECLARE i INT DEFAULT 1;
    DECLARE cid INT;
    DECLARE od DATE;
    DECLARE st VARCHAR(20);
    DECLARE base_date DATE;

    -- 为每个客户生成 3-10 个订单
    WHILE i <= 100 DO
        SET cid = i;
        SET base_date = DATE_ADD('2023-03-01', INTERVAL FLOOR(RAND() * 90) DAY);

        -- 每个客户随机 1-8 个订单
        SET @order_count = 1 + FLOOR(RAND() * 8);
        SET @j = 1;

        WHILE @j <= @order_count DO
            SET od = DATE_ADD(base_date, INTERVAL @j * FLOOR(15 + RAND() * 60) DAY);
            -- 确保订单日期不过于未来
            IF od <= '2024-09-01' THEN
                -- 随机状态（加权分布）
                SET @rand_val = RAND();
                IF @rand_val < 0.05 THEN
                    SET st = 'pending';
                ELSEIF @rand_val < 0.15 THEN
                    SET st = 'paid';
                ELSEIF @rand_val < 0.25 THEN
                    SET st = 'shipped';
                ELSEIF @rand_val < 0.95 THEN
                    SET st = 'delivered';
                ELSE
                    SET st = 'cancelled';
                END IF;

                INSERT INTO orders (customer_id, order_date, status, remark)
                VALUES (cid, od, st,
                    CASE WHEN st = 'cancelled' THEN '客户取消' ELSE NULL END);
            END IF;
            SET @j = @j + 1;
        END WHILE;

        SET i = i + 1;
    END WHILE;
END //
DELIMITER ;

CALL generate_orders();
DROP PROCEDURE generate_orders;

-- 更新订单总金额为0（后续通过 order_items 计算后更新）
-- 先留为0，插入order_items后会通过UPDATE更新

-- ---- 订单明细数据（为每个 delivered/shipped/paid 订单生成 1-6 条明细）----

DELIMITER //
CREATE PROCEDURE generate_order_items()
BEGIN
    DECLARE done INT DEFAULT FALSE;
    DECLARE oid INT;
    DECLARE pid INT;
    DECLARE qty INT;
    DECLARE uprice DECIMAL(10,2);
    DECLARE item_count INT;
    DECLARE k INT;

    DECLARE order_cursor CURSOR FOR
        SELECT id FROM orders
        WHERE status IN ('delivered', 'shipped', 'paid')
        ORDER BY id;

    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;

    OPEN order_cursor;

    read_loop: LOOP
        FETCH order_cursor INTO oid;
        IF done THEN
            LEAVE read_loop;
        END IF;

        -- 每个订单 1-6 条明细
        SET item_count = 1 + FLOOR(RAND() * 6);
        SET k = 1;

        WHILE k <= item_count DO
            SET pid = 1 + FLOOR(RAND() * 50);   -- 随机商品 1-50
            SET qty = 1 + FLOOR(RAND() * 5);     -- 随机数量 1-5

            -- 取商品当前价格
            SELECT price INTO uprice FROM products WHERE id = pid;

            INSERT INTO order_items (order_id, product_id, quantity, unit_price)
            VALUES (oid, pid, qty, uprice);

            SET k = k + 1;
        END WHILE;
    END LOOP;

    CLOSE order_cursor;
END //
DELIMITER ;

CALL generate_order_items();
DROP PROCEDURE generate_order_items;

-- ---- 更新订单总金额（根据 order_items 汇总）----
UPDATE orders o
SET total_amount = (
    SELECT COALESCE(SUM(quantity * unit_price), 0)
    FROM order_items oi
    WHERE oi.order_id = o.id
);

-- ---- 额外插入一些特殊数据（用于演示边界情况）----

-- 一个没有任何订单的客户（用于 EXISTS / LEFT JOIN 演示）
INSERT INTO customers (id, name, email, phone, city, gender, vip_level, register_date) VALUES
(101, '测试用户A', 'testa@test.com', '13999999999', '火星', '未知', 0, '2024-12-31');

-- 一个有订单但全部取消的客户（用于状态过滤演示）
INSERT INTO orders (id, customer_id, order_date, status, total_amount, remark) VALUES
(9999, 101, '2024-12-25', 'cancelled', 0.00, '全部取消');

-- 一些价格边缘的商品
INSERT INTO products (id, name, category_id, supplier_id, price, cost, stock, description) VALUES
(51, '测试超便宜商品',  NULL, NULL,   0.01,   0.00,   9999, '最小价格边界测试'),
(52, '测试超贵商品',    NULL, NULL, 999999.99, NULL,  1,    '最大价格边界测试'),
(53, '已下架商品',      NULL, NULL, 100.00,   50.00,  0,    '库存为0，测试边界');

-- ============================================================
-- 初始化完成，打印各表数据量
-- ============================================================
SELECT 'categories'   AS 表名, COUNT(*) AS 行数 FROM categories
UNION ALL
SELECT 'suppliers',    COUNT(*) FROM suppliers
UNION ALL
SELECT 'products',     COUNT(*) FROM products
UNION ALL
SELECT 'customers',    COUNT(*) FROM customers
UNION ALL
SELECT 'orders',       COUNT(*) FROM orders
UNION ALL
SELECT 'order_items',  COUNT(*) FROM order_items
UNION ALL
SELECT 'audit_log',    COUNT(*) FROM audit_log;

SELECT '✅ 数据库 mysql_tutorial 初始化完成！' AS 状态;
