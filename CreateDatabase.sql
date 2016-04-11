
create role xovis with login password 'xovis' ;

create database xovis with owner xovis ;

\c xovis xovis

create table xovis_status (
	macaddress character varying(18) NOT NULL,
	sensorgroup character varying(256),
	sensorname character varying(256),
	lastseen bigint,
	ipaddress character varying(15),
	timezone character varying(36),
	devicetype character varying(10),
	firmware character varying(32),
	registered boolean,
	alive boolean,
	connected boolean,
	countmode character varying(15),
	coordinatemode character varying(10),
	onpremenabled boolean,
	onprempushstatus boolean,
	cloudenabled boolean,
	cloudcountpushstatus boolean,
	cloudsensorpushstatus boolean,
	ntpenabled boolean,
	ntpstatus boolean,
	config character varying(16384)
);

alter table only xovis_status add constraint xovis_status_pkey PRIMARY KEY (macaddress);
