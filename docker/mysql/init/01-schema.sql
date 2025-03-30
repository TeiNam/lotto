-- docker/mysql/init/01-schema.sql
CREATE TABLE IF NOT EXISTS `result` (
  `no` int unsigned NOT NULL AUTO_INCREMENT COMMENT 'PK',
  `1` tinyint unsigned NOT NULL,
  `2` tinyint unsigned NOT NULL,
  `3` tinyint unsigned NOT NULL,
  `4` tinyint unsigned NOT NULL,
  `5` tinyint unsigned NOT NULL,
  `6` tinyint unsigned NOT NULL,
  `create_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`no`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='결과';

CREATE TABLE IF NOT EXISTS `recommand` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT 'PK',
  `next_no` int unsigned NOT NULL,
  `1` tinyint unsigned NOT NULL,
  `2` tinyint unsigned NOT NULL,
  `3` tinyint unsigned NOT NULL,
  `4` tinyint unsigned NOT NULL,
  `5` tinyint unsigned NOT NULL,
  `6` tinyint unsigned NOT NULL,
  `create_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;