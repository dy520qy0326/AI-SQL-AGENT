-- V2: Modified e-commerce schema for version diff testing
-- Changes from V1:
--   + coupons table (new)
--   - inventory table (removed)
--   - shipping_log table (removed)
--   ~ orders.total DECIMAL(10,2) → DECIMAL(12,2)
--   + orders.coupon_id (new field)
--   ~ products.stock_quantity INT → BIGINT
--   - payments.method (removed field)
--   ~ addresses → user_addresses (renamed)
--   ~ products.category_id NOT NULL → NULL

CREATE TABLE users (
    id INT PRIMARY KEY COMMENT '用户唯一ID',
    name VARCHAR(255) NOT NULL COMMENT '用户名',
    email VARCHAR(255) COMMENT '邮箱地址',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE orders (
    id INT PRIMARY KEY COMMENT '订单ID',
    user_id INT NOT NULL COMMENT '下单用户ID',
    coupon_id INT COMMENT '优惠券ID',
    total DECIMAL(12,2) DEFAULT 0.00 COMMENT '订单总金额',
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE products (
    id INT PRIMARY KEY COMMENT '商品ID',
    name VARCHAR(255) NOT NULL COMMENT '商品名称',
    category_id INT,
    price DECIMAL(10,2) COMMENT '单价',
    stock_quantity BIGINT DEFAULT 0 COMMENT '库存数量',
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

CREATE TABLE user_addresses (
    id INT PRIMARY KEY COMMENT '地址ID',
    user_id INT NOT NULL,
    address_line VARCHAR(500),
    city VARCHAR(100),
    postal_code VARCHAR(20)
);

CREATE TABLE payments (
    id INT PRIMARY KEY COMMENT '支付ID',
    order_id INT NOT NULL COMMENT '关联订单ID',
    amount DECIMAL(14,2) NOT NULL COMMENT '支付金额',
    paid_at TIMESTAMP
);

CREATE TABLE coupons (
    id INT PRIMARY KEY,
    code VARCHAR(50) NOT NULL,
    discount DECIMAL(5,2),
    expires_at TIMESTAMP
);
