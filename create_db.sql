-- ============================================================================
-- CANASTA EXPRESS - Inicialización de base de datos (create_db.sql)
-- Motor: PostgreSQL 16
--
-- IMPORTANTE:
--   Este script es DESTRUCTIVO: elimina las tablas existentes y sus datos.
--   Úsalo únicamente para crear/recrear una base de datos local de desarrollo
--   o pruebas. En entornos persistentes utiliza las migraciones de Alembic.
--
-- El esquema debe mantenerse alineado con los modelos SQLAlchemy y las
-- migraciones del backend.
-- ============================================================================

-- 1. LIMPIEZA DE OBJETOS PREVIOS (SOLO DESARROLLO / PRUEBAS)
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS cart_items CASCADE;
DROP TABLE IF EXISTS carts CASCADE;
DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS payments CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS product_sections CASCADE;
DROP TABLE IF EXISTS restore_codes CASCADE;
DROP TABLE IF EXISTS outbox_events CASCADE;
DROP TABLE IF EXISTS users CASCADE;

DROP TYPE IF EXISTS user_role CASCADE;
DROP TYPE IF EXISTS unit_of_measure CASCADE;
DROP TYPE IF EXISTS payment_status CASCADE;
DROP TYPE IF EXISTS payment_methods CASCADE;
DROP TYPE IF EXISTS delivery_status CASCADE;


-- 2. TIPOS ENUM
-- ----------------------------------------------------------------------------
CREATE TYPE user_role AS ENUM (
    'customer',
    'store_manager',
    'warehouse_manager',
    'packaging_manager',
    'courier'
);

CREATE TYPE unit_of_measure AS ENUM (
    'kilogram',
    'gram',
    'unit',
    'pound'
);

CREATE TYPE payment_status AS ENUM (
    'pending',
    'succeeded',
    'failed',
    'refunded'
);

CREATE TYPE payment_methods AS ENUM (
    'card',
    'cash',
    'transfer'
);

CREATE TYPE delivery_status AS ENUM (
    'pending',
    'packaged',
    'in_transit',
    'delivered',
    'returned_to_warehouse'
);


-- 3. TABLAS
-- ----------------------------------------------------------------------------

CREATE TABLE users (
    id integer GENERATED ALWAYS AS IDENTITY,
    first_name character varying(20) NOT NULL,
    middle_name character varying(20),
    first_surname character varying(20) NOT NULL,
    middle_surname character varying(20),
    email character varying(255) NOT NULL,
    password_hash character varying(255),
    user_role user_role NOT NULL,
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    google_sub character varying(255),
    CONSTRAINT users_pkey PRIMARY KEY (id),
    CONSTRAINT users_email_key UNIQUE (email),
    CONSTRAINT uq_users_google_sub UNIQUE (google_sub)
);

CREATE TABLE restore_codes (
    id integer GENERATED ALWAYS AS IDENTITY,
    user_id integer NOT NULL,
    code_hash character varying(255) NOT NULL,
    was_used boolean NOT NULL DEFAULT false,
    expired_at timestamp with time zone NOT NULL,
    is_active boolean NOT NULL DEFAULT true,
    CONSTRAINT restore_codes_pkey PRIMARY KEY (id),
    CONSTRAINT fk_restore_codes_users
        FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Solo puede existir un código activo por usuario.
CREATE UNIQUE INDEX uq_restore_codes_one_active_per_user
    ON restore_codes (user_id)
    WHERE is_active = true;


CREATE TABLE product_sections (
    id integer GENERATED ALWAYS AS IDENTITY,
    name character varying(30) NOT NULL,
    created_at timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT product_sections_pkey PRIMARY KEY (id),
    CONSTRAINT product_sections_name_key UNIQUE (name)
);

CREATE TABLE products (
    id integer GENERATED ALWAYS AS IDENTITY,
    name character varying(120) NOT NULL,
    price numeric(10,2) NOT NULL,
    unit_of_measure unit_of_measure NOT NULL,
    -- Se admiten cantidades fraccionarias (por ejemplo, 0.500 kg).
    stock numeric(10,3) NOT NULL,
    created_at timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    -- Todo producto publicado debe tener una imagen asociada.
    image_path character varying(255) NOT NULL,
    section_id integer NOT NULL,
    CONSTRAINT products_pkey PRIMARY KEY (id),
    CONSTRAINT products_name_key UNIQUE (name),
    CONSTRAINT products_price_check CHECK (price > 0),
    CONSTRAINT products_stock_check CHECK (stock >= 0),
    CONSTRAINT fk_products_product_sections
        FOREIGN KEY (section_id) REFERENCES product_sections(id)
);


CREATE TABLE payments (
    id integer GENERATED ALWAYS AS IDENTITY,
    status payment_status NOT NULL DEFAULT 'pending',
    method payment_methods NOT NULL,
    created_at timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT payments_pkey PRIMARY KEY (id)
);
CREATE INDEX idx_payments_status ON payments (status);


CREATE TABLE outbox_events (
    id integer GENERATED ALWAYS AS IDENTITY,
    event_key character varying(255) NOT NULL,
    event_type character varying(100) NOT NULL,
    payload jsonb NOT NULL,
    status character varying(20) NOT NULL DEFAULT 'pending',
    attempts integer NOT NULL DEFAULT 0,
    available_at timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    locked_until timestamp with time zone,
    created_at timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    processed_at timestamp with time zone,
    last_error character varying(1000),
    CONSTRAINT outbox_events_pkey PRIMARY KEY (id),
    CONSTRAINT outbox_events_event_key_key UNIQUE (event_key),
    CONSTRAINT ck_outbox_events_attempts_nonnegative CHECK (attempts >= 0)
);


CREATE TABLE orders (
    id integer GENERATED ALWAYS AS IDENTITY,
    user_id integer NOT NULL,
    courier_id integer,
    total_price numeric(10,2) NOT NULL,
    delivery_status delivery_status NOT NULL DEFAULT 'pending',
    shipping_street character varying(80) NOT NULL,
    shipping_details character varying(120) NOT NULL,
    shipping_city character varying(60) NOT NULL,
    created_at timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    phone_number character varying(10) NOT NULL,
    customer_name character varying(100) NOT NULL DEFAULT '',
    idempotency_key character varying(255),
    payment_id integer NOT NULL,
    shipping_neighborhood character varying(60) NOT NULL DEFAULT '',
    shipping_instructions character varying(250) DEFAULT '',
    shipping_department character varying(60) NOT NULL DEFAULT '',
    CONSTRAINT orders_pkey PRIMARY KEY (id),
    CONSTRAINT uq_orders_payments UNIQUE (payment_id),
    -- La clave evita crear dos pedidos ante reintentos del mismo checkout.
    -- PostgreSQL permite múltiples NULL en una restricción UNIQUE.
    CONSTRAINT uq_orders_idempotency_key UNIQUE (idempotency_key),
    CONSTRAINT ck_orders_total_price_nonnegative CHECK (total_price >= 0),
    CONSTRAINT ck_orders_courier_required_for_delivery CHECK (
        delivery_status NOT IN ('in_transit', 'delivered')
        OR courier_id IS NOT NULL
    ),
    CONSTRAINT fk_orders_payment_id FOREIGN KEY (payment_id) REFERENCES payments(id),
    CONSTRAINT fk_orders_users FOREIGN KEY (user_id) REFERENCES users(id),
    CONSTRAINT fk_orders_courier FOREIGN KEY (courier_id) REFERENCES users(id)
);

CREATE INDEX idx_orders_courier_id ON orders (courier_id);
CREATE INDEX idx_orders_delivery_status ON orders (delivery_status);
CREATE INDEX idx_orders_shipping_city ON orders (shipping_city);
CREATE INDEX idx_orders_user_id ON orders (user_id);


CREATE TABLE order_items (
    id integer GENERATED ALWAYS AS IDENTITY,
    order_id integer NOT NULL,
    product_id integer NOT NULL,
    unit_price numeric(10,2) NOT NULL,
    -- Debe conservar la misma precisión fraccionaria que el carrito.
    quantity numeric(10,3) NOT NULL,
    created_at timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT order_items_pkey PRIMARY KEY (id),
    CONSTRAINT uk_order_items_order_id_product_id UNIQUE (order_id, product_id),
    CONSTRAINT order_items_quantity_check CHECK (quantity > 0),
    CONSTRAINT order_items_unit_price_check CHECK (unit_price > 0),
    CONSTRAINT fk_order_items_orders FOREIGN KEY (order_id) REFERENCES orders(id),
    CONSTRAINT fk_order_items_products FOREIGN KEY (product_id) REFERENCES products(id)
);
CREATE INDEX idx_order_items_product_id ON order_items (product_id);


CREATE TABLE carts (
    id integer GENERATED ALWAYS AS IDENTITY,
    user_id integer NOT NULL,
    created_at timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT carts_pkey PRIMARY KEY (id),
    CONSTRAINT uq_carts_user_id UNIQUE (user_id),
    CONSTRAINT fk_carts_user_id FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE cart_items (
    id integer GENERATED ALWAYS AS IDENTITY,
    cart_id integer NOT NULL,
    product_id integer NOT NULL,
    quantity numeric(10,3) NOT NULL,
    created_at timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT cart_items_pkey PRIMARY KEY (id),
    CONSTRAINT uq_cart_items_cart_product UNIQUE (cart_id, product_id),
    CONSTRAINT ck_cart_items_quantity_positive CHECK (quantity > 0),
    CONSTRAINT fk_cart_items_cart_id FOREIGN KEY (cart_id) REFERENCES carts(id),
    CONSTRAINT fk_cart_items_product_id FOREIGN KEY (product_id) REFERENCES products(id)
);


-- 4. DATOS SEMILLA
-- ----------------------------------------------------------------------------
-- Secciones iniciales para que el formulario de creación de productos pueda
-- cargar opciones desde GET /products/sections en una base recién inicializada.
INSERT INTO product_sections (name) VALUES
    ('Frutas'),
    ('Verduras'),
    ('Tubérculos'),
    ('Legumbres'),
    ('Hierbas y aromáticas');

-- Usuarios de prueba: únicamente para desarrollo local.
-- Contraseña de prueba documentada por el proyecto: usuario123*
INSERT INTO users (
    first_name, middle_name, first_surname, middle_surname,
    email, password_hash, user_role, is_active
) VALUES
    ('Carlos', 'Alberto', 'Pérez', 'Gómez', 'admin.tienda@canasta.com',
     '$2b$14$Tb5GZ7CkxZM9rElOa9ioA.C0qy4W3oq6XJ7EJXMg9H3/OM.o6BgYi',
     'store_manager', true),
    ('Ana', NULL, 'Rodríguez', 'López', 'bodega@canasta.com',
     '$2b$14$Tb5GZ7CkxZM9rElOa9ioA.C0qy4W3oq6XJ7EJXMg9H3/OM.o6BgYi',
     'warehouse_manager', true),
    ('Luis', 'Miguel', 'García', 'Martínez', 'empaque@canasta.com',
     '$2b$14$Tb5GZ7CkxZM9rElOa9ioA.C0qy4W3oq6XJ7EJXMg9H3/OM.o6BgYi',
     'packaging_manager', true),
    ('Pedro', NULL, 'Sánchez', 'Ruiz', 'courier@canasta.com',
     '$2b$14$Tb5GZ7CkxZM9rElOa9ioA.C0qy4W3oq6XJ7EJXMg9H3/OM.o6BgYi',
     'courier', true),
    ('Maria', 'Elena', 'Torres', 'Castro', 'cliente@canasta.com',
     '$2b$14$Tb5GZ7CkxZM9rElOa9ioA.C0qy4W3oq6XJ7EJXMg9H3/OM.o6BgYi',
     'customer', true);

-- Sincronización segura de la secuencia identity, incluso si no hay filas.
SELECT setval(
    pg_get_serial_sequence('users', 'id'),
    COALESCE((SELECT MAX(id) FROM users), 1),
    EXISTS (SELECT 1 FROM users)
);
