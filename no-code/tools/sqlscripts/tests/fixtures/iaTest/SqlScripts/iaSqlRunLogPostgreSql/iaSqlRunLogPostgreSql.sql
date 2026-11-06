create table if not exists "iaSqlRunLog" ("At" timestamp not null default now(), "Note" varchar(50));
insert into "iaSqlRunLog" ("Note") values ('v2');
