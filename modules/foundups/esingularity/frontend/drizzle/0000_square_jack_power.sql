CREATE TABLE `reddog_web_budget_v2` (
	`bucket` text NOT NULL,
	`day` integer NOT NULL,
	`used` integer NOT NULL,
	`maximum` integer NOT NULL,
	`updated` integer NOT NULL,
	PRIMARY KEY(`bucket`, `day`),
	CONSTRAINT "reddog_web_budget_v2_bounds" CHECK("reddog_web_budget_v2"."used" >= 0 AND "reddog_web_budget_v2"."maximum" > 0 AND "reddog_web_budget_v2"."used" <= "reddog_web_budget_v2"."maximum")
);
--> statement-breakpoint
CREATE TABLE `reddog_web_clock_v2` (
	`id` integer PRIMARY KEY NOT NULL,
	`last_seen` integer NOT NULL,
	CONSTRAINT "reddog_web_clock_v2_bounds" CHECK("reddog_web_clock_v2"."id" = 1 AND "reddog_web_clock_v2"."last_seen" >= 0)
);
--> statement-breakpoint
CREATE TABLE `reddog_web_lick_v1` (
	`token_hash` text PRIMARY KEY NOT NULL,
	`profile_id` text NOT NULL,
	`display_name` text,
	`challenge_hash` text NOT NULL,
	`challenge_complete` integer DEFAULT 0 NOT NULL,
	`consent_version` text NOT NULL,
	FOREIGN KEY (`token_hash`) REFERENCES `reddog_web_session_v2`(`token_hash`) ON UPDATE no action ON DELETE cascade,
	CONSTRAINT "reddog_web_lick_v1_challenge" CHECK(("reddog_web_lick_v1"."challenge_complete" = 0 AND length("reddog_web_lick_v1"."challenge_hash") = 64) OR ("reddog_web_lick_v1"."challenge_complete" = 1 AND "reddog_web_lick_v1"."challenge_hash" = '')),
	CONSTRAINT "reddog_web_lick_v1_display" CHECK("reddog_web_lick_v1"."display_name" IS NULL OR length("reddog_web_lick_v1"."display_name") <= 80)
);
--> statement-breakpoint
CREATE UNIQUE INDEX `idx_reddog_web_lick_v1_profile` ON `reddog_web_lick_v1` (`profile_id`);--> statement-breakpoint
CREATE TABLE `reddog_web_session_v2` (
	`token_hash` text PRIMARY KEY NOT NULL,
	`encounter` text NOT NULL,
	`surface` text NOT NULL,
	`origin` text NOT NULL,
	`subject` text NOT NULL,
	`actor_claim` text NOT NULL,
	`created` integer NOT NULL,
	`last_seen` integer NOT NULL,
	`revision` integer NOT NULL,
	`nonce` text NOT NULL,
	`busy` text,
	`busy_until` integer,
	`closing` integer DEFAULT 0 NOT NULL,
	CONSTRAINT "reddog_web_session_v2_token" CHECK(length("reddog_web_session_v2"."token_hash") = 64),
	CONSTRAINT "reddog_web_session_v2_revision" CHECK("reddog_web_session_v2"."revision" >= 0 AND "reddog_web_session_v2"."revision" <= 10),
	CONSTRAINT "reddog_web_session_v2_clock" CHECK("reddog_web_session_v2"."created" >= 0 AND "reddog_web_session_v2"."last_seen" >= "reddog_web_session_v2"."created"),
	CONSTRAINT "reddog_web_session_v2_closing" CHECK("reddog_web_session_v2"."closing" IN (0, 1)),
	CONSTRAINT "reddog_web_session_v2_busy_pair" CHECK(("reddog_web_session_v2"."busy" IS NULL AND "reddog_web_session_v2"."busy_until" IS NULL) OR ("reddog_web_session_v2"."busy" IS NOT NULL AND "reddog_web_session_v2"."busy_until" IS NOT NULL))
);
--> statement-breakpoint
CREATE UNIQUE INDEX `idx_reddog_web_session_v2_encounter` ON `reddog_web_session_v2` (`encounter`);--> statement-breakpoint
CREATE INDEX `idx_reddog_web_session_v2_expiry` ON `reddog_web_session_v2` (`created`,`last_seen`);--> statement-breakpoint
CREATE INDEX `idx_reddog_web_session_v2_busy_until` ON `reddog_web_session_v2` (`busy_until`);