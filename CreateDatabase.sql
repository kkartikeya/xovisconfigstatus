
create schema xovis;

alter schema xovis owner to xovis ;

create table xovis.xovis_status (
	sensor_id character varying(36) NOT NULL,
	macaddress character varying(18),
	sensorgroup character varying(256),
	sensorname character varying(256),
	lastseen bigint,
	ipaddress character varying(15),
	timezone character varying(36),
	devicetype character varying(10),
	firmware character varying(32),
	connected boolean,
	countmode character varying(15),
	coordinatemode character varying(10),
	onpremenabled boolean,
	onpremagentid smallint,
	onprempushstatus boolean,
	cloudenabled boolean,
	cloudcountagentid smallint,
	cloudsensorstatusagentid smallint,
	cloudcountpushstatus boolean,
	cloudsensorpushstatus boolean,
	ntpenabled boolean,
	ntpstatus boolean,
	config character varying(16384)
);

alter table only xovis.xovis_status add constraint xovis_status_pkey PRIMARY KEY (sensor_id);
alter table xovis.xovis_status owner to xovis;
