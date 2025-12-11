
-- Warns Table
CREATE TABLE IF NOT EXISTS `warns` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `user_id` varchar(20) NOT NULL,
  `server_id` varchar(20) NOT NULL,
  `moderator_id` varchar(20) NOT NULL,
  `reason` varchar(255) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Economy: Users
CREATE TABLE IF NOT EXISTS `economy_users` (
  `user_id` varchar(20) NOT NULL,
  `server_id` varchar(20) NOT NULL,
  `wallet` BIGINT DEFAULT 0,
  `bank` BIGINT DEFAULT 0,
  `last_daily` timestamp,
  `last_work` timestamp,
  PRIMARY KEY (`user_id`, `server_id`)
);

-- Economy: Shop Items
CREATE TABLE IF NOT EXISTS `shop_items` (
  `item_id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `server_id` varchar(20) NOT NULL,
  `name` varchar(50) NOT NULL,
  `description` varchar(200),
  `price` BIGINT NOT NULL,
  `role_id` varchar(20), 
  `stock` INTEGER DEFAULT -1
);

-- Economy: Inventory
CREATE TABLE IF NOT EXISTS `inventory` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `user_id` varchar(20) NOT NULL,
  `server_id` varchar(20) NOT NULL,
  `item_id` INTEGER NOT NULL,
  `quantity` INTEGER DEFAULT 1,
  FOREIGN KEY(`item_id`) REFERENCES `shop_items`(`item_id`) ON DELETE CASCADE
);

-- Leveling: Users
CREATE TABLE IF NOT EXISTS `levels` (
  `user_id` varchar(20) NOT NULL,
  `server_id` varchar(20) NOT NULL,
  `xp` BIGINT DEFAULT 0,
  `level` INTEGER DEFAULT 0,
  `last_message` timestamp,
  PRIMARY KEY (`user_id`, `server_id`)
);

-- Leveling: Rewards
CREATE TABLE IF NOT EXISTS `level_rewards` (
  `server_id` varchar(20) NOT NULL,
  `level_req` INTEGER NOT NULL,
  `role_id` varchar(20) NOT NULL,
  PRIMARY KEY (`server_id`, `level_req`)
);

-- Settings: Guild Configuration (NEW)
CREATE TABLE IF NOT EXISTS `guild_settings` (
  `server_id` varchar(20) PRIMARY KEY,
  `xp_rate_text` INTEGER DEFAULT 1,     -- Multiplier for Text XP
  `xp_rate_voice` INTEGER DEFAULT 10,   -- XP per minute in Voice
  `level_difficulty` INTEGER DEFAULT 100 -- Base XP for level 1 (Formula: base * level^2)
);