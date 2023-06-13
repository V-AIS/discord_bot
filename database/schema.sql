CREATE TABLE IF NOT EXISTS `blacklist` (
  `user_id` varchar(20) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS `warns` (
  `id` int(11) NOT NULL,
  `user_id` varchar(20) NOT NULL,
  `server_id` varchar(20) NOT NULL,
  `moderator_id` varchar(20) NOT NULL,
  `reason` varchar(255) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS `channel_list` (
  `channel_name` varchar(20) NOT NULL,
  `channel_id` varchar(20) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS `youtube_channel` (
  `channel_name` varchar(50) NOT NULL,
  `rss_link` varchar(50) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS `youtube_video` (
  `channel_name` varchar(50) NOT NULL,
  `video_id` varchar(50) NOT NULL,
  `video_link` varchar(255) NOT NULL,
  `published` varchar(50) NOT NULL,
  `send` BIT NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS `log` (
  `channel_name` varchar(20) NOT NULL,
  `channel_id` varchar(20) NOT NULL,
  `message_author` varchar(20) NOT NULL,
  `message_author_id` varchar(20) NOT NULL,
  `message_content` varchar(255) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS `github` (
  `channel_name` varchar(20) NOT NULL,
  `channel_id` varchar(20) NOT NULL,
  `message_author` varchar(20) NOT NULL,
  `message_author_id` varchar(20) NOT NULL,
  `github_username` varchar(20) NOT NULL,
  `repository_name` varchar(50) NOT NULL,
  `description` varchar(255) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS `paper` (
  `channel_name` varchar(20) NOT NULL,
  `channel_id` varchar(20) NOT NULL,
  `message_author` varchar(20) NOT NULL,
  `message_author_id` varchar(20) NOT NULL,
  `source` varchar(20) NOT NULL,
  `title` varchar(255) NOT NULL,
  `authors` varchar(255) NOT NULL,
  `url` varchar(255) NOT NULL,
  `conference` varchar(255) NOT NULL,
  `year` varchar(10) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);