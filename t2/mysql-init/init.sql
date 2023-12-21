CREATE DATABASE IF NOT EXISTS ecommerce;

USE ecommerce;

CREATE TABLE products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255),
    description TEXT,
    price DECIMAL(10, 2),
    quantity INT
);

INSERT INTO products (name, description, price, quantity) VALUES
    ('Guarda-chuva', 'Item indispensável para esperar o 110 quando a parada de ônibus tá lotada', 19.99, 12),
    ('Power bank', 'Para conseguir carregar seu celular mesmo nas salas em que nenhuma tomada funciona', 49.90, 5),
    ('Calculadora científica', 'Essa é pra você que fez Cálculo 1, 2 e 3, mas sofre pra fazer uma divisão com casas decimais', 79.90, 10),
    ('Raquete de tênis de mesa', 'É difícil chegar no CA e jogar com aquelas que nem borracha mais têm', 65.50, 2);
