CREATE TABLE `HomeAssistantEntity` (
	`application_name` text NOT NULL,
	`base_state` text NOT NULL,
	`entity_id` text NOT NULL,
	`first_observed` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`last_modified` text NOT NULL,
	`last_reported` text NOT NULL,
	`state_json` text NOT NULL,
	`unique_id` text NOT NULL
);
--> statement-breakpoint
CREATE UNIQUE INDEX `HomeAssistantEntity_unique_id_unique` ON `HomeAssistantEntity` (`unique_id`);--> statement-breakpoint
CREATE TABLE `HomeAssistantEntityLocals` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`key` text NOT NULL,
	`last_modified` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
	`unique_id` integer NOT NULL,
	`value_json` text NOT NULL
);
