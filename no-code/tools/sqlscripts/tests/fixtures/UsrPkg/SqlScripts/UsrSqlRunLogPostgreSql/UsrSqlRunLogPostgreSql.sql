create table if not exists "UsrSqlRunLog" ("At" timestamp not null default now(), "Note" varchar(50));
insert into "UsrSqlRunLog" ("Note") values ('v2');
