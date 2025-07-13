CREATE TABLE "HomeAssistantEntity" (
	"app_unique_id" text NOT NULL,
	"application_name" text NOT NULL,
	"base_state" text NOT NULL,
	"entity_id" text NOT NULL,
	"first_observed" timestamp DEFAULT now() NOT NULL,
	"id" serial PRIMARY KEY NOT NULL,
	"last_modified" text NOT NULL,
	"last_reported" text NOT NULL,
	"state_json" jsonb NOT NULL,
	"unique_id" text NOT NULL,
	CONSTRAINT "HomeAssistantEntity_unique_id_unique" UNIQUE("unique_id")
);
--> statement-breakpoint
CREATE TABLE "HomeAssistantEntityLocals" (
	"app_unique_id" text NOT NULL,
	"id" serial PRIMARY KEY NOT NULL,
	"key" text NOT NULL,
	"last_modified" timestamp DEFAULT now() NOT NULL,
	"unique_id" integer NOT NULL,
	"value_json" jsonb NOT NULL
);
