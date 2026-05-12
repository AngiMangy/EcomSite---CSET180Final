Admin SignIn info
Username: admin
Password: admin123

MySQL:
-- Creating the Database
create database if not exists EcomDB;
use EcomDB;

-- Creating the table for Users 
create table if not exists UserINFO (
	userID int not null unique auto_increment primary key,
	first_name varchar(255) not null,
    last_name varchar(255) not null,
	username varchar(255) not null unique,
    email varchar(255) not null unique,
    password varchar(255) not null,
    is_vendor boolean default 0,
    is_admin boolean default 0
	);
    ALTER TABLE UserINFO ADD COLUMN is_approved BOOLEAN DEFAULT FALSE;

-- Creating Admin Account, comment back out once done
insert into Userinfo (first_name, last_name, username, email, password, is_vendor, is_admin)
Values('Admin', 'User', 'admin', 'admin@vending.com', 'scrypt:32768:8:1$NW9W4sMnlFMApxUf$15240654a40c257c2c196d56c07bef8e7efe80f17426264a84bbbc14ed396bbc60012678283d24d0b74f944c758ff546f2d51eb2120131b96f616cc419aa5ec1', 1, 1);

-- Creating the table used for Store Items
create table if not exists storeItems (
	itemID int not null auto_increment primary key,
    item_name varchar(255) not null,
    item_description varchar(255),
    item_price dec not null
	);

-- Creating the table used for the Cart / Orders Page
create table if not exists UserCart (
	item_name varchar(255) not null,
    item_details varchar(255) not null,
	order_status ENUM('pending','confirmed','shipped','out for delivery') not null default 'pending',
    order_number int not null unique auto_increment primary key
    );
    
-- Creating table used for Warranty / Refund Requests
create table if not exists requests (
	is_refund boolean default 0,
    is_warranty boolean default 0,
    req_title varchar(255) not null,
    req_desc varchar(255) not null,
    req_status ENUM('pending','rejected','confirmed','processing','complete') not null default 'pending'
    );
ALTER TABLE requests
8  ADD COLUMN req_id INT AUTO_INCREMENT PRIMARY KEY FIRST,
  ADD COLUMN user_id INT,
  ADD CONSTRAINT fk_req_user FOREIGN KEY (user_id) REFERENCES UserINFO(userID);
    
ALTER TABLE storeItems
  ADD COLUMN warranty_period VARCHAR(100),
  ADD COLUMN category VARCHAR(100),
  ADD COLUMN colors JSON,
  ADD COLUMN sizes JSON,
  ADD COLUMN stock_count INT DEFAULT 0;
ALTER TABLE storeItems MODIFY COLUMN item_description TEXT;

ALTER TABLE storeItems 
ADD COLUMN vendor_id INT,
ADD CONSTRAINT fk_storeitems_vendor FOREIGN KEY (vendor_id) REFERENCES UserINFO(userID);

ALTER TABLE storeItems 
ADD COLUMN gallery JSON;

ALTER TABLE UserCart
ADD COLUMN user_id INT,
ADD COLUMN quantity INT DEFAULT 1,
ADD COLUMN created_at DATETIME,
ADD CONSTRAINT fk_usercart_user FOREIGN KEY (user_id) REFERENCES UserINFO(userID);

select * from userinfo;
-- Delete Line; be sure to comment out after use
-- drop database ecomdb2
