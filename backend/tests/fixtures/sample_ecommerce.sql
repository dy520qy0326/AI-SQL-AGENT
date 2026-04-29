-- 10-table e-commerce DDL for Phase 3 testing
-- 5 tables with explicit FK, 2 with _id naming (no explicit FK), 3 isolated

CREATE TABLE users (
    id INT PRIMARY KEY COMMENT '用户唯一ID',
    name VARCHAR(255) NOT NULL COMMENT '用户名',
    email VARCHAR(255) COMMENT '邮箱地址',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE orders (
    id INT PRIMARY KEY COMMENT '订单ID',
    user_id INT NOT NULL COMMENT '下单用户ID',
    total DECIMAL(10,2) DEFAULT 0.00 COMMENT '订单总金额',
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE products (
    id INT PRIMARY KEY COMMENT '商品ID',
    name VARCHAR(255) NOT NULL COMMENT '商品名称',
    category_id INT NOT NULL,
    price DECIMAL(10,2) COMMENT '单价',
    stock_quantity INT DEFAULT 0 COMMENT '库存数量',
    FOREIGN KEY (category_id) REFERENCES categories(id)
);

CREATE TABLE categories (
    id INT PRIMARY KEY COMMENT '分类ID',
    name VARCHAR(255) NOT NULL COMMENT '分类名称',
    parent_id INT
);

CREATE TABLE cart_items (
    id INT PRIMARY KEY,
    user_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT DEFAULT 1,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);

CREATE TABLE reviews (
    id INT PRIMARY KEY COMMENT '评论ID',
    user_id INT NOT NULL,
    product_id INT NOT NULL,
    rating INT COMMENT '评分(1-5)',
    content TEXT COMMENT '评论内容',
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);

-- _id naming convention, no explicit FK (Phase 2 inferred)
CREATE TABLE addresses (
    id INT PRIMARY KEY COMMENT '地址ID',
    user_id INT NOT NULL,
    address_line VARCHAR(500),
    city VARCHAR(100),
    postal_code VARCHAR(20)
);

CREATE TABLE payments (
    id INT PRIMARY KEY COMMENT '支付ID',
    order_id INT NOT NULL COMMENT '关联订单ID',
    amount DECIMAL(10,2) NOT NULL COMMENT '支付金额',
    method VARCHAR(50) COMMENT '支付方式',
    paid_at TIMESTAMP
);

-- Isolated tables (no FK, no _id references)
CREATE TABLE inventory (
    id INT PRIMARY KEY,
    warehouse_name VARCHAR(255),
    location_code VARCHAR(50),
    capacity INT
);

CREATE TABLE shipping_log (
    id INT PRIMARY KEY,
    tracking_number VARCHAR(100),
    carrier VARCHAR(100),
    shipped_at TIMESTAMP,
    status VARCHAR(50) DEFAULT 'pending'
);
