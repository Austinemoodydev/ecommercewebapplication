-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1:3306
-- Generation Time: Aug 16, 2026 at 11:39 AM
-- Server version: 9.1.0
-- PHP Version: 8.3.14

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `onlinestore`
--

-- --------------------------------------------------------

--
-- Table structure for table `accounts_address`
--

DROP TABLE IF EXISTS `accounts_address`;
CREATE TABLE IF NOT EXISTS `accounts_address` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `full_name` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `phone` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `county` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `city` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `estate` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `house_number` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `landmark` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `is_default` tinyint(1) NOT NULL,
  `user_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `accounts_address_user_id_c8c74ddf` (`user_id`)
) ENGINE=MyISAM AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `accounts_address`
--

INSERT INTO `accounts_address` (`id`, `full_name`, `phone`, `county`, `city`, `estate`, `house_number`, `landmark`, `is_default`, `user_id`) VALUES
(3, 'AUSTINE', '0115650092', 'NAIROBI', 'NAIROBI', 'WESTLANDS', 'HOUSE 11', 'NEAR OTC MALL', 0, 1),
(2, 'Austine Moody', '0115650092', 'kisumu', 'kisumu', 'kamukunji', '11', 'near otc', 1, 1);

-- --------------------------------------------------------

--
-- Table structure for table `accounts_customuser`
--

DROP TABLE IF EXISTS `accounts_customuser`;
CREATE TABLE IF NOT EXISTS `accounts_customuser` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `password` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL,
  `last_login` datetime(6) DEFAULT NULL,
  `is_superuser` tinyint(1) NOT NULL,
  `username` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `first_name` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `last_name` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `email` varchar(254) COLLATE utf8mb4_unicode_ci NOT NULL,
  `is_staff` tinyint(1) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `date_joined` datetime(6) NOT NULL,
  `phone` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `avatar` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `role` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `email_verified` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=MyISAM AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `accounts_customuser`
--

INSERT INTO `accounts_customuser` (`id`, `password`, `last_login`, `is_superuser`, `username`, `first_name`, `last_name`, `email`, `is_staff`, `is_active`, `date_joined`, `phone`, `avatar`, `role`, `email_verified`) VALUES
(1, 'pbkdf2_sha256$1200000$DVR7Ullt3bPKT0LyAnGfbY$rxrouCGJ3y3hBKvgX4GMQp0NXU//cdrNfhC8cr1qGfU=', '2026-08-14 20:04:00.086170', 1, 'austine', '', '', 'madyaustine@gmail.com', 1, 1, '2026-07-21 21:31:51.728940', '', '', 'customer', 0),
(2, 'pbkdf2_sha256$1200000$hoVjuyASiEpAf5qWtLgzSF$84rGguIm2dkhnOPxjbTGuK8GaZ8cIzqj9Mf9uI9nBJ8=', '2026-07-21 21:37:27.893469', 0, 'tygh', 'anyan', 'tur', 'trgh@gmail.com', 0, 1, '2026-07-21 21:37:26.948350', '0976545480', '', 'customer', 0);

-- --------------------------------------------------------

--
-- Table structure for table `accounts_customuser_groups`
--

DROP TABLE IF EXISTS `accounts_customuser_groups`;
CREATE TABLE IF NOT EXISTS `accounts_customuser_groups` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `customuser_id` bigint NOT NULL,
  `group_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `accounts_customuser_groups_customuser_id_group_id_c074bdcb_uniq` (`customuser_id`,`group_id`),
  KEY `accounts_customuser_groups_customuser_id_bc55088e` (`customuser_id`),
  KEY `accounts_customuser_groups_group_id_86ba5f9e` (`group_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `accounts_customuser_user_permissions`
--

DROP TABLE IF EXISTS `accounts_customuser_user_permissions`;
CREATE TABLE IF NOT EXISTS `accounts_customuser_user_permissions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `customuser_id` bigint NOT NULL,
  `permission_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `accounts_customuser_user_customuser_id_permission_9632a709_uniq` (`customuser_id`,`permission_id`),
  KEY `accounts_customuser_user_permissions_customuser_id_0deaefae` (`customuser_id`),
  KEY `accounts_customuser_user_permissions_permission_id_aea3d0e5` (`permission_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `accounts_userprofile`
--

DROP TABLE IF EXISTS `accounts_userprofile`;
CREATE TABLE IF NOT EXISTS `accounts_userprofile` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `date_of_birth` date DEFAULT NULL,
  `gender` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `bio` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `user_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `user_id` (`user_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `account_emailaddress`
--

DROP TABLE IF EXISTS `account_emailaddress`;
CREATE TABLE IF NOT EXISTS `account_emailaddress` (
  `id` int NOT NULL AUTO_INCREMENT,
  `email` varchar(191) COLLATE utf8mb4_unicode_ci NOT NULL,
  `verified` tinyint(1) NOT NULL,
  `primary` tinyint(1) NOT NULL,
  `user_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `account_emailaddress_user_id_email_987c8728_uniq` (`user_id`,`email`),
  KEY `account_emailaddress_user_id_2c513194` (`user_id`),
  KEY `account_emailaddress_email_03be32b2` (`email`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `account_emailconfirmation`
--

DROP TABLE IF EXISTS `account_emailconfirmation`;
CREATE TABLE IF NOT EXISTS `account_emailconfirmation` (
  `id` int NOT NULL AUTO_INCREMENT,
  `created` datetime(6) NOT NULL,
  `sent` datetime(6) DEFAULT NULL,
  `key` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `email_address_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `key` (`key`),
  KEY `account_emailconfirmation_email_address_id_5b7f8c58` (`email_address_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `auth_group`
--

DROP TABLE IF EXISTS `auth_group`;
CREATE TABLE IF NOT EXISTS `auth_group` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `auth_group_permissions`
--

DROP TABLE IF EXISTS `auth_group_permissions`;
CREATE TABLE IF NOT EXISTS `auth_group_permissions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `group_id` int NOT NULL,
  `permission_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_group_permissions_group_id_permission_id_0cd325b0_uniq` (`group_id`,`permission_id`),
  KEY `auth_group_permissions_group_id_b120cbf9` (`group_id`),
  KEY `auth_group_permissions_permission_id_84c5c92e` (`permission_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `auth_permission`
--

DROP TABLE IF EXISTS `auth_permission`;
CREATE TABLE IF NOT EXISTS `auth_permission` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `content_type_id` int NOT NULL,
  `codename` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_permission_content_type_id_codename_01ab375a_uniq` (`content_type_id`,`codename`),
  KEY `auth_permission_content_type_id_2f476e4b` (`content_type_id`)
) ENGINE=MyISAM AUTO_INCREMENT=109 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `auth_permission`
--

INSERT INTO `auth_permission` (`id`, `name`, `content_type_id`, `codename`) VALUES
(1, 'Can add log entry', 1, 'add_logentry'),
(2, 'Can change log entry', 1, 'change_logentry'),
(3, 'Can delete log entry', 1, 'delete_logentry'),
(4, 'Can view log entry', 1, 'view_logentry'),
(5, 'Can add permission', 3, 'add_permission'),
(6, 'Can change permission', 3, 'change_permission'),
(7, 'Can delete permission', 3, 'delete_permission'),
(8, 'Can view permission', 3, 'view_permission'),
(9, 'Can add group', 2, 'add_group'),
(10, 'Can change group', 2, 'change_group'),
(11, 'Can delete group', 2, 'delete_group'),
(12, 'Can view group', 2, 'view_group'),
(13, 'Can add content type', 4, 'add_contenttype'),
(14, 'Can change content type', 4, 'change_contenttype'),
(15, 'Can delete content type', 4, 'delete_contenttype'),
(16, 'Can view content type', 4, 'view_contenttype'),
(17, 'Can add session', 5, 'add_session'),
(18, 'Can change session', 5, 'change_session'),
(19, 'Can delete session', 5, 'delete_session'),
(20, 'Can view session', 5, 'view_session'),
(21, 'Can add user', 6, 'add_customuser'),
(22, 'Can change user', 6, 'change_customuser'),
(23, 'Can delete user', 6, 'delete_customuser'),
(24, 'Can view user', 6, 'view_customuser'),
(25, 'Can add brand', 7, 'add_brand'),
(26, 'Can change brand', 7, 'change_brand'),
(27, 'Can delete brand', 7, 'delete_brand'),
(28, 'Can view brand', 7, 'view_brand'),
(29, 'Can add product image', 9, 'add_productimage'),
(30, 'Can change product image', 9, 'change_productimage'),
(31, 'Can delete product image', 9, 'delete_productimage'),
(32, 'Can view product image', 9, 'view_productimage'),
(33, 'Can add product', 8, 'add_product'),
(34, 'Can change product', 8, 'change_product'),
(35, 'Can delete product', 8, 'delete_product'),
(36, 'Can view product', 8, 'view_product'),
(37, 'Can add category', 10, 'add_category'),
(38, 'Can change category', 10, 'change_category'),
(39, 'Can delete category', 10, 'delete_category'),
(40, 'Can view category', 10, 'view_category'),
(41, 'Can add cart item', 12, 'add_cartitem'),
(42, 'Can change cart item', 12, 'change_cartitem'),
(43, 'Can delete cart item', 12, 'delete_cartitem'),
(44, 'Can view cart item', 12, 'view_cartitem'),
(45, 'Can add cart', 11, 'add_cart'),
(46, 'Can change cart', 11, 'change_cart'),
(47, 'Can delete cart', 11, 'delete_cart'),
(48, 'Can view cart', 11, 'view_cart'),
(49, 'Can add address', 13, 'add_address'),
(50, 'Can change address', 13, 'change_address'),
(51, 'Can delete address', 13, 'delete_address'),
(52, 'Can view address', 13, 'view_address'),
(53, 'Can add user profile', 14, 'add_userprofile'),
(54, 'Can change user profile', 14, 'change_userprofile'),
(55, 'Can delete user profile', 14, 'delete_userprofile'),
(56, 'Can view user profile', 14, 'view_userprofile'),
(57, 'Can add wishlist', 15, 'add_wishlist'),
(58, 'Can change wishlist', 15, 'change_wishlist'),
(59, 'Can delete wishlist', 15, 'delete_wishlist'),
(60, 'Can view wishlist', 15, 'view_wishlist'),
(61, 'Can add order item', 16, 'add_orderitem'),
(62, 'Can change order item', 16, 'change_orderitem'),
(63, 'Can delete order item', 16, 'delete_orderitem'),
(64, 'Can view order item', 16, 'view_orderitem'),
(65, 'Can add order', 17, 'add_order'),
(66, 'Can change order', 17, 'change_order'),
(67, 'Can delete order', 17, 'delete_order'),
(68, 'Can view order', 17, 'view_order'),
(69, 'Can add delivery area', 18, 'add_deliveryarea'),
(70, 'Can change delivery area', 18, 'change_deliveryarea'),
(71, 'Can delete delivery area', 18, 'delete_deliveryarea'),
(72, 'Can view delivery area', 18, 'view_deliveryarea'),
(73, 'Can add mpesa transaction', 19, 'add_mpesatransaction'),
(74, 'Can change mpesa transaction', 19, 'change_mpesatransaction'),
(75, 'Can delete mpesa transaction', 19, 'delete_mpesatransaction'),
(76, 'Can view mpesa transaction', 19, 'view_mpesatransaction'),
(77, 'Can add coupon', 20, 'add_coupon'),
(78, 'Can change coupon', 20, 'change_coupon'),
(79, 'Can delete coupon', 20, 'delete_coupon'),
(80, 'Can view coupon', 20, 'view_coupon'),
(81, 'Can add review', 21, 'add_review'),
(82, 'Can change review', 21, 'change_review'),
(83, 'Can delete review', 21, 'delete_review'),
(84, 'Can view review', 21, 'view_review'),
(85, 'Can add site', 22, 'add_site'),
(86, 'Can change site', 22, 'change_site'),
(87, 'Can delete site', 22, 'delete_site'),
(88, 'Can view site', 22, 'view_site'),
(89, 'Can add email address', 23, 'add_emailaddress'),
(90, 'Can change email address', 23, 'change_emailaddress'),
(91, 'Can delete email address', 23, 'delete_emailaddress'),
(92, 'Can view email address', 23, 'view_emailaddress'),
(93, 'Can add email confirmation', 24, 'add_emailconfirmation'),
(94, 'Can change email confirmation', 24, 'change_emailconfirmation'),
(95, 'Can delete email confirmation', 24, 'delete_emailconfirmation'),
(96, 'Can view email confirmation', 24, 'view_emailconfirmation'),
(97, 'Can add social account', 25, 'add_socialaccount'),
(98, 'Can change social account', 25, 'change_socialaccount'),
(99, 'Can delete social account', 25, 'delete_socialaccount'),
(100, 'Can view social account', 25, 'view_socialaccount'),
(101, 'Can add social application', 26, 'add_socialapp'),
(102, 'Can change social application', 26, 'change_socialapp'),
(103, 'Can delete social application', 26, 'delete_socialapp'),
(104, 'Can view social application', 26, 'view_socialapp'),
(105, 'Can add social application token', 27, 'add_socialtoken'),
(106, 'Can change social application token', 27, 'change_socialtoken'),
(107, 'Can delete social application token', 27, 'delete_socialtoken'),
(108, 'Can view social application token', 27, 'view_socialtoken');

-- --------------------------------------------------------

--
-- Table structure for table `cart_cart`
--

DROP TABLE IF EXISTS `cart_cart`;
CREATE TABLE IF NOT EXISTS `cart_cart` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `user_id` bigint DEFAULT NULL,
  `session_key` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `cart_cart_user_id_9b4220b9` (`user_id`)
) ENGINE=MyISAM AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `cart_cart`
--

INSERT INTO `cart_cart` (`id`, `created_at`, `updated_at`, `user_id`, `session_key`) VALUES
(1, '2026-07-25 10:46:04.605351', '2026-07-25 10:46:04.605400', 1, NULL),
(2, '2026-07-31 12:18:56.324986', '2026-07-31 12:18:56.325034', NULL, 'jlc4h8hun4lt73h5gvwtqm6hoag6tprk'),
(3, '2026-08-09 19:48:55.422344', '2026-08-09 19:48:55.422360', NULL, 'zeamz4oyrnujedie1otw4ip6zfy8vvt8'),
(4, '2026-08-09 19:52:55.053584', '2026-08-09 19:52:55.053598', NULL, 'lfgdhgcxh3rxbchlsv32rrrogf0ulnx9'),
(5, '2026-08-13 11:18:12.271820', '2026-08-13 11:18:12.271837', NULL, 'd1ckvoes6lnawv876u4fs32555i97ag1'),
(6, '2026-08-14 19:11:44.080113', '2026-08-14 19:11:44.080130', NULL, 'i2082xge2swts1p8t9ruvamrugcg1io1');

-- --------------------------------------------------------

--
-- Table structure for table `cart_cartitem`
--

DROP TABLE IF EXISTS `cart_cartitem`;
CREATE TABLE IF NOT EXISTS `cart_cartitem` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `quantity` int UNSIGNED NOT NULL,
  `cart_id` bigint NOT NULL,
  `product_id` bigint NOT NULL,
  `created_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `cart_cartitem_cart_id_product_id_53cce7c3_uniq` (`cart_id`,`product_id`),
  KEY `cart_cartitem_cart_id_370ad265` (`cart_id`),
  KEY `cart_cartitem_product_id_b24e265a` (`product_id`)
) ;

--
-- Dumping data for table `cart_cartitem`
--

INSERT INTO `cart_cartitem` (`id`, `quantity`, `cart_id`, `product_id`, `created_at`) VALUES
(8, 1, 2, 1, '2026-07-31 12:19:34.295436'),
(11, 1, 3, 1, '2026-08-09 19:48:55.425238'),
(12, 1, 4, 1, '2026-08-09 19:52:55.054963'),
(23, 1, 5, 1, '2026-08-13 11:18:12.275851'),
(24, 1, 6, 1, '2026-08-14 19:11:44.092709');

-- --------------------------------------------------------

--
-- Table structure for table `categories_category`
--

DROP TABLE IF EXISTS `categories_category`;
CREATE TABLE IF NOT EXISTS `categories_category` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `slug` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `image` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `description` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`),
  UNIQUE KEY `slug` (`slug`)
) ENGINE=MyISAM AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `categories_category`
--

INSERT INTO `categories_category` (`id`, `name`, `slug`, `image`, `description`, `is_active`, `created_at`) VALUES
(1, 'Electronics', 'electronics', 'categories/gaming_category.jpg', 'best quality electronic gadgets and gaming equipments', 1, '2026-07-25 03:41:40.368029'),
(2, 'Beauty& personal care', 'b_e_a_u', 'categories/beauty__personal_care_category.jpg', 'Quality beauty and personal care products designed to enhance your appearance confidence and everyday self care', 1, '2026-07-25 03:42:00.860721'),
(4, 'Home & Kitchen', 'home-kitchen', 'categories/home__living_category.jpg', '', 1, '2026-07-25 03:43:11.766420'),
(6, 'fashion&clothing', 'fashionclothing', 'categories/image.png', 'Trendy and Stylish clothing for every occasion', 1, '2026-08-15 21:44:06.811080');

-- --------------------------------------------------------

--
-- Table structure for table `django_admin_log`
--

DROP TABLE IF EXISTS `django_admin_log`;
CREATE TABLE IF NOT EXISTS `django_admin_log` (
  `id` int NOT NULL AUTO_INCREMENT,
  `action_time` datetime(6) NOT NULL,
  `object_id` longtext COLLATE utf8mb4_unicode_ci,
  `object_repr` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL,
  `action_flag` smallint UNSIGNED NOT NULL,
  `change_message` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `content_type_id` int DEFAULT NULL,
  `user_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `django_admin_log_content_type_id_c4bce8eb` (`content_type_id`),
  KEY `django_admin_log_user_id_c564eba6` (`user_id`)
) ;

--
-- Dumping data for table `django_admin_log`
--

INSERT INTO `django_admin_log` (`id`, `action_time`, `object_id`, `object_repr`, `action_flag`, `change_message`, `content_type_id`, `user_id`) VALUES
(1, '2026-07-25 03:41:40.371736', '1', 'Electronics', 1, '[{\"added\": {}}]', 10, 1),
(2, '2026-07-25 03:42:00.862893', '2', 'Fashion', 1, '[{\"added\": {}}]', 10, 1),
(3, '2026-07-25 03:42:30.659217', '3', 'Beauty', 1, '[{\"added\": {}}]', 10, 1),
(4, '2026-07-25 03:43:11.768696', '4', 'Home & Kitchen', 1, '[{\"added\": {}}]', 10, 1),
(5, '2026-07-25 03:47:26.165250', '1', 'Samsung', 1, '[{\"added\": {}}]', 7, 1),
(6, '2026-07-25 03:47:55.314718', '2', 'Apple', 1, '[{\"added\": {}}]', 7, 1),
(7, '2026-07-25 03:48:23.934438', '3', 'nike', 1, '[{\"added\": {}}]', 7, 1),
(8, '2026-07-25 03:48:51.042243', '4', 'HP', 1, '[{\"added\": {}}]', 7, 1),
(9, '2026-07-25 03:49:14.372222', '5', 'Lenovo', 1, '[{\"added\": {}}]', 7, 1),
(10, '2026-07-25 03:54:29.079021', '1', 'Gaming Laptop', 1, '[{\"added\": {}}]', 8, 1),
(11, '2026-07-27 16:50:07.682339', '5', 'inner clothes', 1, '[{\"added\": {}}]', 10, 1),
(12, '2026-07-27 16:50:49.164281', '6', 'mercedes', 1, '[{\"added\": {}}]', 7, 1),
(13, '2026-08-13 07:01:43.919855', '1', 'SAVE10', 1, '[{\"added\": {}}]', 20, 1),
(14, '2026-08-15 21:44:06.821412', '6', 'fashion&clothing', 1, '[{\"added\": {}}]', 10, 1),
(15, '2026-08-15 21:49:45.800010', '2', 'Beauty& personal care', 2, '[{\"changed\": {\"fields\": [\"Name\", \"Slug\", \"Image\", \"Description\"]}}]', 10, 1),
(16, '2026-08-15 21:50:09.216365', '3', 'Beauty', 3, '', 10, 1),
(17, '2026-08-15 21:52:15.833845', '1', 'Electronics', 2, '[{\"changed\": {\"fields\": [\"Image\", \"Description\"]}}]', 10, 1),
(18, '2026-08-15 21:57:06.978359', '4', 'Home & Kitchen', 2, '[{\"changed\": {\"fields\": [\"Image\"]}}]', 10, 1),
(19, '2026-08-16 07:10:57.052615', '5', 'inner clothes', 3, '', 10, 1),
(20, '2026-08-16 09:48:23.429057', '1', 'Gaming Laptop', 2, '[{\"changed\": {\"fields\": [\"Image\"]}}]', 8, 1),
(21, '2026-08-16 09:54:56.600325', '7', 'GLOWE', 1, '[{\"added\": {}}]', 7, 1),
(22, '2026-08-16 09:55:32.378109', '7', 'glowe', 2, '[{\"changed\": {\"fields\": [\"Name\"]}}]', 7, 1),
(23, '2026-08-16 10:04:57.913451', '2', 'glowe radiance', 1, '[{\"added\": {}}]', 8, 1);

-- --------------------------------------------------------

--
-- Table structure for table `django_content_type`
--

DROP TABLE IF EXISTS `django_content_type`;
CREATE TABLE IF NOT EXISTS `django_content_type` (
  `id` int NOT NULL AUTO_INCREMENT,
  `app_label` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `model` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `django_content_type_app_label_model_76bd3d3b_uniq` (`app_label`,`model`)
) ENGINE=MyISAM AUTO_INCREMENT=28 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `django_content_type`
--

INSERT INTO `django_content_type` (`id`, `app_label`, `model`) VALUES
(1, 'admin', 'logentry'),
(2, 'auth', 'group'),
(3, 'auth', 'permission'),
(4, 'contenttypes', 'contenttype'),
(5, 'sessions', 'session'),
(6, 'accounts', 'customuser'),
(7, 'products', 'brand'),
(8, 'products', 'product'),
(9, 'products', 'productimage'),
(10, 'categories', 'category'),
(11, 'cart', 'cart'),
(12, 'cart', 'cartitem'),
(13, 'accounts', 'address'),
(14, 'accounts', 'userprofile'),
(15, 'wishlist', 'wishlist'),
(16, 'orders', 'orderitem'),
(17, 'orders', 'order'),
(18, 'orders', 'deliveryarea'),
(19, 'payments', 'mpesatransaction'),
(20, 'orders', 'coupon'),
(21, 'reviews', 'review'),
(22, 'sites', 'site'),
(23, 'account', 'emailaddress'),
(24, 'account', 'emailconfirmation'),
(25, 'socialaccount', 'socialaccount'),
(26, 'socialaccount', 'socialapp'),
(27, 'socialaccount', 'socialtoken');

-- --------------------------------------------------------

--
-- Table structure for table `django_migrations`
--

DROP TABLE IF EXISTS `django_migrations`;
CREATE TABLE IF NOT EXISTS `django_migrations` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `app` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `applied` datetime(6) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM AUTO_INCREMENT=52 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `django_migrations`
--

INSERT INTO `django_migrations` (`id`, `app`, `name`, `applied`) VALUES
(1, 'contenttypes', '0001_initial', '2026-07-21 21:30:23.355803'),
(2, 'contenttypes', '0002_remove_content_type_name', '2026-07-21 21:30:23.422074'),
(3, 'auth', '0001_initial', '2026-07-21 21:30:23.681797'),
(4, 'auth', '0002_alter_permission_name_max_length', '2026-07-21 21:30:23.728567'),
(5, 'auth', '0003_alter_user_email_max_length', '2026-07-21 21:30:23.732588'),
(6, 'auth', '0004_alter_user_username_opts', '2026-07-21 21:30:23.737914'),
(7, 'auth', '0005_alter_user_last_login_null', '2026-07-21 21:30:23.744449'),
(8, 'auth', '0006_require_contenttypes_0002', '2026-07-21 21:30:23.745651'),
(9, 'auth', '0007_alter_validators_add_error_messages', '2026-07-21 21:30:23.751549'),
(10, 'auth', '0008_alter_user_username_max_length', '2026-07-21 21:30:23.755402'),
(11, 'auth', '0009_alter_user_last_name_max_length', '2026-07-21 21:30:23.760568'),
(12, 'auth', '0010_alter_group_name_max_length', '2026-07-21 21:30:23.786092'),
(13, 'auth', '0011_update_proxy_permissions', '2026-07-21 21:30:23.792315'),
(14, 'auth', '0012_alter_user_first_name_max_length', '2026-07-21 21:30:23.797203'),
(15, 'accounts', '0001_initial', '2026-07-21 21:30:24.085462'),
(16, 'admin', '0001_initial', '2026-07-21 21:30:24.220506'),
(17, 'admin', '0002_logentry_remove_auto_add', '2026-07-21 21:30:24.227105'),
(18, 'admin', '0003_logentry_add_action_flag_choices', '2026-07-21 21:30:24.235592'),
(19, 'sessions', '0001_initial', '2026-07-21 21:30:24.266435'),
(20, 'categories', '0001_initial', '2026-07-25 03:32:11.996172'),
(21, 'products', '0001_initial', '2026-07-25 03:32:12.442389'),
(22, 'cart', '0001_initial', '2026-07-25 04:44:48.568937'),
(23, 'products', '0002_alter_product_options_productimage_alt_text_and_more', '2026-07-27 16:46:36.721732'),
(24, 'accounts', '0002_remove_customuser_created_at_and_more', '2026-07-28 04:57:00.722596'),
(25, 'wishlist', '0001_initial', '2026-07-31 08:30:34.693449'),
(26, 'cart', '0002_cart_session_key_cartitem_created_at_alter_cart_user_and_more', '2026-07-31 11:07:03.269611'),
(27, 'orders', '0001_initial', '2026-08-09 19:42:41.118696'),
(28, 'orders', '0002_deliveryarea', '2026-08-09 20:36:26.862316'),
(29, 'orders', '0003_seed_delivery_areas', '2026-08-09 20:38:15.315562'),
(30, 'orders', '0004_order_latitude_order_longitude', '2026-08-09 20:54:38.836498'),
(31, 'payments', '0001_initial', '2026-08-11 10:14:31.510665'),
(32, 'orders', '0005_coupon', '2026-08-13 06:47:51.264644'),
(33, 'orders', '0006_order_coupon', '2026-08-13 06:48:52.525845'),
(34, 'reviews', '0001_initial', '2026-08-14 19:38:46.392893'),
(35, 'account', '0001_initial', '2026-08-15 19:20:25.252005'),
(36, 'account', '0002_email_max_length', '2026-08-15 19:23:58.746943'),
(37, 'account', '0003_alter_emailaddress_create_unique_verified_email', '2026-08-15 19:23:58.798260'),
(38, 'account', '0004_alter_emailaddress_drop_unique_email', '2026-08-15 19:23:58.903280'),
(39, 'account', '0005_emailaddress_idx_upper_email', '2026-08-15 19:23:58.917367'),
(40, 'account', '0006_emailaddress_lower', '2026-08-15 19:23:58.948633'),
(41, 'account', '0007_emailaddress_idx_email', '2026-08-15 19:23:59.017957'),
(42, 'account', '0008_emailaddress_unique_primary_email_fixup', '2026-08-15 19:23:59.040959'),
(43, 'account', '0009_emailaddress_unique_primary_email', '2026-08-15 19:23:59.055147'),
(44, 'sites', '0001_initial', '2026-08-15 19:23:59.069474'),
(45, 'sites', '0002_alter_domain_unique', '2026-08-15 19:23:59.103219'),
(46, 'socialaccount', '0001_initial', '2026-08-15 19:23:59.533855'),
(47, 'socialaccount', '0002_token_max_lengths', '2026-08-15 19:23:59.631243'),
(48, 'socialaccount', '0003_extra_data_default_dict', '2026-08-15 19:23:59.643632'),
(49, 'socialaccount', '0004_app_provider_id_settings', '2026-08-15 19:26:42.116581'),
(50, 'socialaccount', '0005_socialtoken_nullable_app', '2026-08-15 19:26:43.571407'),
(51, 'socialaccount', '0006_alter_socialaccount_extra_data', '2026-08-15 19:26:43.616188');

-- --------------------------------------------------------

--
-- Table structure for table `django_session`
--

DROP TABLE IF EXISTS `django_session`;
CREATE TABLE IF NOT EXISTS `django_session` (
  `session_key` varchar(40) COLLATE utf8mb4_unicode_ci NOT NULL,
  `session_data` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `expire_date` datetime(6) NOT NULL,
  PRIMARY KEY (`session_key`),
  KEY `django_session_expire_date_a5c62663` (`expire_date`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `django_session`
--

INSERT INTO `django_session` (`session_key`, `session_data`, `expire_date`) VALUES
('oqdg78jrjiqphgah77nz1f6y2srcgp0c', '.eJxVjEEOwiAQRe_C2hAQsIxL9z0DmRlAqgaS0q6Md7dNutDtf-_9twi4LiWsPc1hiuIqtDj9boT8THUH8YH13iS3uswTyV2RB-1ybDG9bof7d1Cwl60GNgpMxsHThY1RCForD2eg7FwyTDa7TbDWe0eg2aWEMIDVniwqZPH5AsZoN04:1wmIAz:dz6QxDf9gpYQ1_zDHUAnsPNT7DuVlSya-9QyZ2AOom0', '2026-08-04 21:38:57.120963'),
('t1j2jffwv2vjiudgczl410nh1znmdu1v', '.eJxVjEEOwiAQRe_C2hAQsIxL9z0DmRlAqgaS0q6Md7dNutDtf-_9twi4LiWsPc1hiuIqtDj9boT8THUH8YH13iS3uswTyV2RB-1ybDG9bof7d1Cwl60GNgpMxsHThY1RCForD2eg7FwyTDa7TbDWe0eg2aWEMIDVniwqZPH5AsZoN04:1wnTAI:Mw0iWMYhWhjQfEQ1v102X5gzsCqOGAjTpNhCtIY1vZE', '2026-08-08 03:35:06.513862'),
('jlc4h8hun4lt73h5gvwtqm6hoag6tprk', 'e30:1wpmCW:th_MACgCpZW1Og5HKsPnhLIUXd3W1hS2R9h2HWJMzqU', '2026-08-14 12:18:56.341660'),
('d1ckvoes6lnawv876u4fs32555i97ag1', 'e30:1wuTRs:rX-_uWKdgEFNkOEfklD9lmDAuXZIptRRfjzgpbtMS6A', '2026-08-27 11:18:12.280359'),
('cqn1db4fiz9yy2vsk5zlxwyh1xuqtqm6', '.eJxVjMsOwiAQRf-FtSHlDS7d-w1kYAapGkhKuzL-uzbpQrf3nHNfLMK21rgNWuKM7MwEO_1uCfKD2g7wDu3Wee5tXebEd4UfdPBrR3peDvfvoMKo3xps0lpazEEK541F0sWqYFRBB2iEksrpyRc5KcLgQ0m5IEm01vmiPLD3B9LQN8I:1wt9WR:jyn4HaPMUvw0a3AWZ80-aWbQ1vENDepmj46_cImFNLI', '2026-08-23 19:49:27.722790'),
('xlhr7hbqrr00pg558vwk5ad8br2k615g', '.eJxVjDkOwjAQRe_iGlleJl4o6TlDNOOxcQDZUpYKcXeIlALa_977LzHittZxW_I8TizOQovT70aYHrntgO_Ybl2m3tZ5Irkr8qCLvHbOz8vh_h1UXOq3hgI-ekLngwIHrgANgCozG89sy5BIa1KKNIG1jBiKDQ6NyRxLTEm8P-BIOFk:1wuy8G:pDYIOznlkG0_uwIDtKSbEyI37aqe_Z2BZgPbQuVC664', '2026-08-28 20:04:00.093507');

-- --------------------------------------------------------

--
-- Table structure for table `django_site`
--

DROP TABLE IF EXISTS `django_site`;
CREATE TABLE IF NOT EXISTS `django_site` (
  `id` int NOT NULL AUTO_INCREMENT,
  `domain` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `django_site_domain_a2e37b91_uniq` (`domain`)
) ENGINE=MyISAM AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `django_site`
--

INSERT INTO `django_site` (`id`, `domain`, `name`) VALUES
(1, 'example.com', 'example.com');

-- --------------------------------------------------------

--
-- Table structure for table `orders_coupon`
--

DROP TABLE IF EXISTS `orders_coupon`;
CREATE TABLE IF NOT EXISTS `orders_coupon` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `code` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `discount_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `discount_value` decimal(10,2) NOT NULL,
  `minimum_order_amount` decimal(12,2) NOT NULL,
  `usage_limit` int UNSIGNED DEFAULT NULL,
  `times_used` int UNSIGNED NOT NULL,
  `valid_from` datetime(6) DEFAULT NULL,
  `valid_until` datetime(6) DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `code` (`code`)
) ;

--
-- Dumping data for table `orders_coupon`
--

INSERT INTO `orders_coupon` (`id`, `code`, `discount_type`, `discount_value`, `minimum_order_amount`, `usage_limit`, `times_used`, `valid_from`, `valid_until`, `is_active`, `created_at`) VALUES
(1, 'SAVE10', 'percentage', 9.88, -0.02, 0, 1, NULL, NULL, 1, '2026-08-13 07:01:43.918271');

-- --------------------------------------------------------

--
-- Table structure for table `orders_deliveryarea`
--

DROP TABLE IF EXISTS `orders_deliveryarea`;
CREATE TABLE IF NOT EXISTS `orders_deliveryarea` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `county` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `fee` decimal(10,2) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `orders_deliveryarea_county_name_61689d1a_uniq` (`county`,`name`)
) ENGINE=MyISAM AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `orders_deliveryarea`
--

INSERT INTO `orders_deliveryarea` (`id`, `county`, `name`, `fee`, `is_active`) VALUES
(1, 'Nairobi', 'Westlands', 250.00, 1),
(2, 'Nairobi', 'Kilimani', 200.00, 1),
(3, 'Nairobi', 'Kileleshwa', 200.00, 1),
(4, 'Nairobi', 'Karen', 400.00, 1),
(5, 'Nairobi', 'Lang\'ata', 300.00, 1),
(6, 'Nairobi', 'South B', 150.00, 1),
(7, 'Nairobi', 'South C', 150.00, 1),
(8, 'Nairobi', 'Embakasi', 300.00, 1),
(9, 'Nairobi', 'Kasarani', 350.00, 1),
(10, 'Nairobi', 'Roysambu', 300.00, 1);

-- --------------------------------------------------------

--
-- Table structure for table `orders_order`
--

DROP TABLE IF EXISTS `orders_order`;
CREATE TABLE IF NOT EXISTS `orders_order` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `order_number` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL,
  `full_name` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `phone` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `email` varchar(254) COLLATE utf8mb4_unicode_ci NOT NULL,
  `county` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `city` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `estate` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `house_number` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `landmark` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `delivery_notes` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `subtotal` decimal(12,2) NOT NULL,
  `shipping_cost` decimal(12,2) NOT NULL,
  `discount` decimal(12,2) NOT NULL,
  `total_amount` decimal(12,2) NOT NULL,
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `payment_status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `payment_method` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `user_id` bigint NOT NULL,
  `latitude` decimal(9,6) DEFAULT NULL,
  `longitude` decimal(9,6) DEFAULT NULL,
  `coupon_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `order_number` (`order_number`),
  KEY `orders_order_user_id_e9b59eb1` (`user_id`),
  KEY `orders_order_coupon_id_5bddb887` (`coupon_id`)
) ENGINE=MyISAM AUTO_INCREMENT=13 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `orders_order`
--

INSERT INTO `orders_order` (`id`, `order_number`, `full_name`, `phone`, `email`, `county`, `city`, `estate`, `house_number`, `landmark`, `delivery_notes`, `subtotal`, `shipping_cost`, `discount`, `total_amount`, `status`, `payment_status`, `payment_method`, `created_at`, `updated_at`, `user_id`, `latitude`, `longitude`, `coupon_id`) VALUES
(1, 'ORD-358812E3B9', 'Austine', '0115650092', 'madyaustine@gmail.com', 'Nairobi', 'Nairobi', 'South B', '14', '-', 'come with you', 74999.98, 150.00, 0.00, 75149.98, 'pending', 'pending', 'mpesa', '2026-08-11 09:05:41.106861', '2026-08-11 09:05:41.106880', 1, NULL, NULL, NULL),
(2, 'ORD-F4B277F8AE', 'Austine', '254708374149', 'madyaustine@gmail.com', 'Nairobi', 'Nairobi', 'Westlands', '15', 'opapo', 'delivery it well', 74999.98, 250.00, 0.00, 75249.98, 'pending', 'pending', 'mpesa', '2026-08-11 11:25:47.504521', '2026-08-11 11:25:47.504552', 1, NULL, NULL, NULL),
(3, 'ORD-222B415233', 'Austine Moody', '+254708374149', 'madyaustine@gmail.com', 'Nairobi', 'Nairobi', 'Westlands', '41', 'kinyanjui', 'come with dem', 74999.98, 250.00, 0.00, 75249.98, 'pending', 'pending', 'mpesa', '2026-08-11 11:40:44.918764', '2026-08-11 11:40:44.918785', 1, NULL, NULL, NULL),
(4, 'ORD-3DA6ACE175', 'Austine', '+254708374149', 'madyaustine@gmail.com', 'Nairobi', 'Nairobi', 'Embakasi', '11', 'kwg', 'come with dera', 74999.98, 300.00, 0.00, 75299.98, 'pending', 'pending', 'mpesa', '2026-08-11 11:49:19.763517', '2026-08-11 11:49:19.763545', 1, NULL, NULL, NULL),
(5, 'ORD-AD5AF3DCA0', 'Austine', '0115650092', 'madyaustine@gmail.com', 'Nairobi', 'Nairobi', 'Westlands', '11', 'near gol', 'come at ninght', 74999.98, 250.00, 0.00, 75249.98, 'pending', 'pending', 'mpesa', '2026-08-11 14:15:49.856535', '2026-08-11 14:15:49.856589', 1, NULL, NULL, NULL),
(6, 'ORD-B8EAD27BBE', 'AV', '0115650092', 'madyaustine@gmail.com', 'Nairobi', 'Nairobi', 'South C', '23', 'BINGO', 'COME WITH TISSUE', 74999.98, 150.00, 0.00, 75149.98, 'pending', 'pending', 'mpesa', '2026-08-11 14:27:09.542594', '2026-08-11 14:27:09.542629', 1, NULL, NULL, NULL),
(7, 'ORD-762A2F48F9', 'aba', '0115650092', 'madyaustine@gmail.com', 'Nairobi', 'Nairobi', 'Westlands', '11', 'ober', 'come with nice stuff', 74999.98, 250.00, 0.00, 75249.98, 'pending', 'pending', 'mpesa', '2026-08-13 07:05:06.442415', '2026-08-13 07:05:06.442430', 1, NULL, NULL, NULL),
(8, 'ORD-8FD9C79107', 'Austine aba', '0115650092..a', 'madyaustine@gmail.com', 'Nairobi', 'Nairobi', 'South B', '11', 'near ongata', 'come with njoki', 524999.86, 150.00, 0.00, 525149.86, 'pending', 'pending', 'mpesa', '2026-08-15 06:53:38.858390', '2026-08-15 06:53:38.858410', 1, NULL, NULL, NULL),
(9, 'ORD-E4BA86DFBC', 'aba', '0115650092', 'madyaustine@gmail.com', 'Nairobi', 'Nairobi', 'Westlands', '11', '0', 'cngt', 74999.98, 250.00, 0.00, 75249.98, 'pending', 'pending', 'mpesa', '2026-08-15 15:35:01.859868', '2026-08-15 15:35:01.859884', 1, NULL, NULL, NULL),
(10, 'ORD-9341FC5CC6', 'auma', '254708374149', 'madyaustine@gmail.com', 'Nairobi', 'Nairobi', 'Westlands', '1', 'bim', 'gft', 74999.98, 250.00, 0.00, 75249.98, 'pending', 'pending', 'mpesa', '2026-08-15 15:41:45.935909', '2026-08-15 15:41:45.935935', 1, NULL, NULL, NULL),
(11, 'ORD-D6817AA669', 'Austine', '0115650092', 'madyaustine@gmail.com', 'Nairobi', 'Nairobi', 'South C', '1', '-', 'keg', 74999.98, 150.00, 0.00, 75149.98, 'pending', 'pending', 'mpesa', '2026-08-15 15:50:55.983580', '2026-08-15 15:50:55.983597', 1, NULL, NULL, NULL),
(12, 'ORD-23A0467886', 'Austine', '0115650092', 'madyaustine@gmail.com', 'Nairobi', 'Nairobi', 'Westlands', '11', '-', 'bring it', 149999.96, 250.00, 0.00, 150249.96, 'pending', 'pending', 'mpesa', '2026-08-15 19:48:48.769916', '2026-08-15 19:48:48.769942', 1, NULL, NULL, NULL);

-- --------------------------------------------------------

--
-- Table structure for table `orders_orderitem`
--

DROP TABLE IF EXISTS `orders_orderitem`;
CREATE TABLE IF NOT EXISTS `orders_orderitem` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `product_name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `price` decimal(12,2) NOT NULL,
  `quantity` int UNSIGNED NOT NULL,
  `subtotal` decimal(12,2) NOT NULL,
  `order_id` bigint NOT NULL,
  `product_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `orders_orderitem_order_id_fe61a34d` (`order_id`),
  KEY `orders_orderitem_product_id_afe4254a` (`product_id`)
) ;

--
-- Dumping data for table `orders_orderitem`
--

INSERT INTO `orders_orderitem` (`id`, `product_name`, `price`, `quantity`, `subtotal`, `order_id`, `product_id`) VALUES
(1, 'Gaming Laptop', 74999.98, 1, 74999.98, 1, 1),
(2, 'Gaming Laptop', 74999.98, 1, 74999.98, 2, 1),
(3, 'Gaming Laptop', 74999.98, 1, 74999.98, 3, 1),
(4, 'Gaming Laptop', 74999.98, 1, 74999.98, 4, 1),
(5, 'Gaming Laptop', 74999.98, 1, 74999.98, 5, 1),
(6, 'Gaming Laptop', 74999.98, 1, 74999.98, 6, 1),
(7, 'Gaming Laptop', 74999.98, 1, 74999.98, 7, 1),
(8, 'Gaming Laptop', 74999.98, 7, 524999.86, 8, 1),
(9, 'Gaming Laptop', 74999.98, 1, 74999.98, 9, 1),
(10, 'Gaming Laptop', 74999.98, 1, 74999.98, 10, 1),
(11, 'Gaming Laptop', 74999.98, 1, 74999.98, 11, 1),
(12, 'Gaming Laptop', 74999.98, 2, 149999.96, 12, 1);

-- --------------------------------------------------------

--
-- Table structure for table `payments_mpesatransaction`
--

DROP TABLE IF EXISTS `payments_mpesatransaction`;
CREATE TABLE IF NOT EXISTS `payments_mpesatransaction` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `phone_number` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `amount` decimal(12,2) NOT NULL,
  `merchant_request_id` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `checkout_request_id` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `mpesa_receipt_number` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `result_code` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL,
  `result_description` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `order_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `payments_mpesatransaction_checkout_request_id_07dd7cd4` (`checkout_request_id`),
  KEY `payments_mpesatransaction_order_id_eca2799f` (`order_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `products_brand`
--

DROP TABLE IF EXISTS `products_brand`;
CREATE TABLE IF NOT EXISTS `products_brand` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `slug` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `logo` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `slug` (`slug`),
  UNIQUE KEY `products_brand_name_8e67b7a6_uniq` (`name`)
) ENGINE=MyISAM AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `products_brand`
--

INSERT INTO `products_brand` (`id`, `name`, `slug`, `logo`) VALUES
(1, 'Samsung', 'smsg', ''),
(2, 'Apple', 'apl', ''),
(3, 'nike', 'nk', ''),
(4, 'HP', 'hp', ''),
(5, 'Lenovo', 'lnv', ''),
(6, 'mercedes', 'mercedes', ''),
(7, 'glowe', 'glowe', '');

-- --------------------------------------------------------

--
-- Table structure for table `products_product`
--

DROP TABLE IF EXISTS `products_product`;
CREATE TABLE IF NOT EXISTS `products_product` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `slug` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `price` decimal(10,2) NOT NULL,
  `discount_price` decimal(10,2) DEFAULT NULL,
  `stock` int UNSIGNED NOT NULL,
  `sku` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `image` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `featured` tinyint(1) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `brand_id` bigint DEFAULT NULL,
  `category_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `slug` (`slug`),
  UNIQUE KEY `sku` (`sku`),
  KEY `products_product_brand_id_3e2e8fd1` (`brand_id`),
  KEY `products_product_category_id_9b594869` (`category_id`)
) ;

--
-- Dumping data for table `products_product`
--

INSERT INTO `products_product` (`id`, `name`, `slug`, `description`, `price`, `discount_price`, `stock`, `sku`, `image`, `featured`, `is_active`, `created_at`, `updated_at`, `brand_id`, `category_id`) VALUES
(1, 'Gaming Laptop', 'gaming-laptop', 'ram 1tb\r\nbangers and loosen speakers\r\n512 nvme ssd', 80000.00, 74999.98, 196, 'glAHP1', 'products/gaming_laptop.jpeg', 1, 1, '2026-07-25 03:54:29.077463', '2026-08-16 09:48:23.420349', 5, 1),
(2, 'glowe radiance', 'glowe-radiance', 'a premium beauty care collection designed to cleanse hydrate nourish and refresh your skin', 2799.99, 2499.95, 100, 'GLO-BEAUTY-001', 'products/glowe_image.jpeg', 1, 1, '2026-08-16 10:04:57.911131', '2026-08-16 10:04:57.911153', 7, 2);

-- --------------------------------------------------------

--
-- Table structure for table `products_productimage`
--

DROP TABLE IF EXISTS `products_productimage`;
CREATE TABLE IF NOT EXISTS `products_productimage` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `image` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `product_id` bigint NOT NULL,
  `alt_text` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  KEY `products_productimage_product_id_e747596a` (`product_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `reviews_review`
--

DROP TABLE IF EXISTS `reviews_review`;
CREATE TABLE IF NOT EXISTS `reviews_review` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `rating` smallint UNSIGNED NOT NULL,
  `comment` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `verified_purchase` tinyint(1) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `product_id` bigint NOT NULL,
  `user_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `reviews_review_product_id_user_id_96befe71_uniq` (`product_id`,`user_id`),
  KEY `reviews_review_product_id_ce2fa4c6` (`product_id`),
  KEY `reviews_review_user_id_875caff2` (`user_id`)
) ;

-- --------------------------------------------------------

--
-- Table structure for table `socialaccount_socialaccount`
--

DROP TABLE IF EXISTS `socialaccount_socialaccount`;
CREATE TABLE IF NOT EXISTS `socialaccount_socialaccount` (
  `id` int NOT NULL AUTO_INCREMENT,
  `provider` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL,
  `uid` varchar(191) COLLATE utf8mb4_unicode_ci NOT NULL,
  `last_login` datetime(6) NOT NULL,
  `date_joined` datetime(6) NOT NULL,
  `extra_data` json NOT NULL,
  `user_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `socialaccount_socialaccount_provider_uid_fc810c6e_uniq` (`provider`,`uid`),
  KEY `socialaccount_socialaccount_user_id_8146e70c` (`user_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `socialaccount_socialapp`
--

DROP TABLE IF EXISTS `socialaccount_socialapp`;
CREATE TABLE IF NOT EXISTS `socialaccount_socialapp` (
  `id` int NOT NULL AUTO_INCREMENT,
  `provider` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(40) COLLATE utf8mb4_unicode_ci NOT NULL,
  `client_id` varchar(191) COLLATE utf8mb4_unicode_ci NOT NULL,
  `secret` varchar(191) COLLATE utf8mb4_unicode_ci NOT NULL,
  `key` varchar(191) COLLATE utf8mb4_unicode_ci NOT NULL,
  `provider_id` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL,
  `settings` json NOT NULL DEFAULT (_utf8mb4'{}'),
  PRIMARY KEY (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `socialaccount_socialapp_sites`
--

DROP TABLE IF EXISTS `socialaccount_socialapp_sites`;
CREATE TABLE IF NOT EXISTS `socialaccount_socialapp_sites` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `socialapp_id` int NOT NULL,
  `site_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `socialaccount_socialapp_sites_socialapp_id_site_id_71a9a768_uniq` (`socialapp_id`,`site_id`),
  KEY `socialaccount_socialapp_sites_socialapp_id_97fb6e7d` (`socialapp_id`),
  KEY `socialaccount_socialapp_sites_site_id_2579dee5` (`site_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `socialaccount_socialtoken`
--

DROP TABLE IF EXISTS `socialaccount_socialtoken`;
CREATE TABLE IF NOT EXISTS `socialaccount_socialtoken` (
  `id` int NOT NULL AUTO_INCREMENT,
  `token` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `token_secret` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `expires_at` datetime(6) DEFAULT NULL,
  `account_id` int NOT NULL,
  `app_id` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `socialaccount_socialtoken_app_id_account_id_fca4e0ac_uniq` (`app_id`,`account_id`),
  KEY `socialaccount_socialtoken_account_id_951f210e` (`account_id`),
  KEY `socialaccount_socialtoken_app_id_636a42d7` (`app_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `wishlist_wishlist`
--

DROP TABLE IF EXISTS `wishlist_wishlist`;
CREATE TABLE IF NOT EXISTS `wishlist_wishlist` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `created_at` datetime(6) NOT NULL,
  `product_id` bigint NOT NULL,
  `user_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `wishlist_wishlist_user_id_product_id_57695ed7_uniq` (`user_id`,`product_id`),
  KEY `wishlist_wishlist_product_id_2d08b75d` (`product_id`),
  KEY `wishlist_wishlist_user_id_13f28b16` (`user_id`)
) ENGINE=MyISAM AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `wishlist_wishlist`
--

INSERT INTO `wishlist_wishlist` (`id`, `created_at`, `product_id`, `user_id`) VALUES
(2, '2026-07-31 11:30:52.896746', 1, 1);
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
