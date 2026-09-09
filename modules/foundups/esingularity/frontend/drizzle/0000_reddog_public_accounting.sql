CREATE TABLE `reddog_web_budget_v1` (
	`bucket` text NOT NULL,
	`day` integer NOT NULL,
	`used` integer NOT NULL,
	`maximum` integer NOT NULL,
	PRIMARY KEY(`bucket`, `day`),
	CONSTRAINT "reddog_budget_bounds" CHECK("reddog_web_budget_v1"."used" >= 0 AND "reddog_web_budget_v1"."used" <= "reddog_web_budget_v1"."maximum")
);
--> statement-breakpoint
CREATE TABLE `reddog_web_clock_v1` (
	`id` integer PRIMARY KEY NOT NULL,
	`last_seen` integer NOT NULL,
	CONSTRAINT "reddog_clock_bounds" CHECK("reddog_web_clock_v1"."id" = 1 AND "reddog_web_clock_v1"."last_seen" >= 0)
);
--> statement-breakpoint
CREATE TABLE `reddog_web_session_v1` (
	`token_hash` text PRIMARY KEY NOT NULL,
	`surface` text NOT NULL,
	`origin` text NOT NULL,
	`subject` text NOT NULL,
	`created` integer NOT NULL,
	`last_seen` integer NOT NULL,
	`revision` integer NOT NULL,
	`nonce` text NOT NULL,
	`busy` text,
	`closed` integer DEFAULT 0 NOT NULL,
	CONSTRAINT "reddog_revision_bounds" CHECK("reddog_web_session_v1"."revision" >= 0 AND "reddog_web_session_v1"."revision" <= 10)
);
