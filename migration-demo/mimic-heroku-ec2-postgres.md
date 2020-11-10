
# Demo Migrating Heroku Postgres to Aurora Postgres

### TOC

1. [Heroku Architecture and Problematic Constraints](#Heroku-Architecture-and-Problematic-Constraints)
2. [RandoNumba App on Heroku](#rando-numba-app)
3. [Establishing Shipping Physical Base Backups and WAL to S3](#log-shipping-replica)
4. [Create Log Shipped Replica](#log-shipped-replica)
5. [Create Streaming Replica (the diasaster saver)](#log-streamed-replica)
6. [Configure Aurora Postgres to allow Logical Replication](#aurora-configuration)
7. [Promote EC2 Postgres LSR and Switch Heroku App to Promoted DB](#promote-ec2-postgres)
8. [Verify EC2 Postgres is Synced and Switch Heroku App to Aurora Postgres](#aurora-switch)


<hr>

### <a id="Heroku-Architecture-and-Problematic-Constraints">Heroku Architecture and Problematic Constraints</a>

<img src="./Heroku-Postgres-Migration.png">

- Heroku utilizes Dynos (aka EC2 Instances) for apps

- Heroku utilizes EC2 + Postgres Instances for their Heroku Postgres Service
  - pg_dump takes 24+ hours to generate and another 24+ hours to ingest into new DB for multi TB DB
  - will not allow access to DB superuser or replication user (so how to get data?)
  - upon several requests Heroku agreeded to "ship" physical backup and WAL to S3 which I used to make a Hot Standby Log Shipped Replica

<hr>

### <a id="rando-numba-app">RandoNumba App on Heroku</a>

[https://murmuring-chamber-40073.herokuapp.com](https://murmuring-chamber-40073.herokuapp.com)

or 

```
heroku open -a murmuring-chamber-40073
```

<hr>

### <a id="log-shipping-replica">Establishing Shipping Physical Base Backups and WAL to S3</a>

#### 1) Spin up EC2 with Dedicated Database Volume (Heroku-Postgres)

- Amazon Linux 2 AMI (t3.medium)
- Default VPC
- Security Group Allowing SSH and Postgres Access
- 16 GB Volume


#### 2) Update Server / Install Dependencies

```
sudo yum update -y
sudo amazon-linux-extras install epel -y
sudo amazon-linux-extras install postgresql10 -y
sudo yum install postgresql-server postgresql-contrib python3 lzop pv -y
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
sudo python3 get-pip.py
sudo python3 -m pip install envdir wal-e[aws]
``` 

#### 3) Mount Database Volume

see what volumes exists

```
$ lsblk
NAME    MAJ:MIN RM SIZE RO TYPE MOUNTPOINT
xvda    202:0    0   8G  0 disk
└─xvda1 202:1    0   8G  0 part /
xvdb    202:16   0  16G  0 disk
```

format db volume into an xfs filesystem

```
$ sudo mkfs -t xfs /dev/xvdb
meta-data=/dev/xvdb              isize=512    agcount=4, agsize=1048576 blks
         =                       sectsz=512   attr=2, projid32bit=1
         =                       crc=1        finobt=1, sparse=0
data     =                       bsize=4096   blocks=4194304, imaxpct=25
         =                       sunit=0      swidth=0 blks
naming   =version 2              bsize=4096   ascii-ci=0 ftype=1
log      =internal log           bsize=4096   blocks=2560, version=2
         =                       sectsz=512   sunit=0 blks, lazy-count=1
realtime =none                   extsz=4096   blocks=0, rtextents=0
```

make a directory to mount volume to

```
sudo mkdir /database
```

mount volume to directory

```
sudo mount /dev/xvdb /database
```

get the volume block id and use it to permanantly mount to directory

```
sudo blkid
```
example with UUID=19ee2212-7fa0-4c9a-bcbf-cd7019d50fd6 

```
# UUID=b24eb1ea-ab1c-47bd-8542-3fd6059814ae     /           xfs    defaults,noatime  1   1
# UUID=19ee2212-7fa0-4c9a-bcbf-cd7019d50fd6     /database   xfs    defaults,nofail   0   2
```

test the mount is /etc/fstab (no news is good news)

```
sudo mount -a
```

update perms and ownership for database directory

```
sudo chown -R postgres:postgres /database
sudo chmod -R 700 /database
```

#### 4) Create WAL-E Env Var Directory

IAM demo-user

```
sudo mkdir -p /etc/wal-e/env
sudo chown -R ec2-user:ec2-user /etc/wal-e
echo "INSERT-VALUE-HERE" > /etc/wal-e/env/AWS_ACCESS_KEY_ID
echo "REGION-HERE" > /etc/wal-e/env/AWS_REGION
echo "INSERT-VALUE-HERE" > /etc/wal-e/env/AWS_SECRET_ACCESS_KEY
echo "S3-BUCKET-URL-HERE" > /etc/wal-e/env/WALE_S3_PREFIX
sudo chown -R postgres:postgres /etc/wal-e
sudo chmod -R 755 /etc/wal-e/env
```

#### 5) Initialize Postgres Pointing to Database Directory

```
sudo su -
su - postgres
pg_ctl init -D /database
```

#### 6) Setup Custom Systemd Service for Postgres

/etc/systemd/system/postgresql.service

```
.include /lib/systemd/system/postgresql.service

[Service]
Environment=PGDATA=/database
```

Reload Systemd then Start & Enable Postgres

```
sudo systemctl daemon-reload
sudo systemctl start postgresql
sudo systemctl status postgresql
sudo systemctl enable postgresql
```

#### 7) create app user and database

```
sudo su -
su - postgres
createuser -e -l --pwprompt pguser
createdb -e --owner=pguser pgdb
psql -d pgdb -f dbdump.sql
```

#### 8) Update postgresql.conf config

```
listen_addresses = '*'
wal_level = replica
archive_mode = on
archive_command = 'envdir /etc/wal-e/env wal-e wal-push %p'
archive_timeout = 60
```

#### 9) Update pg_hba.conf

```
host    pgdb            pguser          0.0.0.0/0               md5
```

#### 10) Remove Existing DB Addon in Heroku

```
$ heroku addons -a murmuring-chamber-40073                                                       

Add-on                                      Plan       Price  State  
──────────────────────────────────────────  ─────────  ─────  ───────
heroku-postgresql (postgresql-cubed-92606)  hobby-dev  free   created
 └─ as DATABASE
$ heroku addons:destroy DATABASE -a murmuring-chamber-40073      
```

#### 11) Update heroku app and restart

flip on maintenance mode

```
heroku maintenance:on -a murmuring-chamber-40073 
```

update the DATABASE_URL config to the new database (EC2 heroku-postgres)

```
heroku config:set DATABASE_URL=postgres://pguser:develop3r@IP-ADDRESS-HERE:5432/pgdb -a murmuring-chamber-40073
heroku ps:restart -a murmuring-chamber-40073
```

turn maintenance off

```
heroku maintenance:off -a murmuring-chamber-40073 
```

#### 12) push a base backup

```
mkdir /var/lib/pgsql/scripts
vi /var/lib/pgsql/scripts/wal-e-push-backup.sh
```

with contents

```
#!/bin/bash

echo "starting wal-e backup-push"

envdir /etc/wal-e/env wal-e backup-push /database

echo "wal-e backup-push complete"
```

run it

```
cd /var/lib/pgsql/scripts
chmod +x /var/lib/pgsql/scripts/wal-e-push-backup.sh
nohup ./wal-e-push-backup.sh &
```










<hr>


### <a id="log-shipped-replica">Create Log Shipped Replica</a>

#### 1) Spin up EC2 Instance

- Amazon Linux 2 AMI (t3.medium)
- Default VPC
- Security Group Allowing SSH and Postgres Access
- 16 GB Volume

#### 2) Update Server and Install Linux Package Dependencies


```
sudo yum update -y
sudo amazon-linux-extras install epel postgresql10 -y
sudo yum install postgresql-server postgresql-contrib python3 lzop -y
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
sudo python3 get-pip.py
sudo python3 -m pip install envdir wal-e[aws]
```

#### 3) Mount Database Volume

see what volumes exists

```
$ lsblk
NAME    MAJ:MIN RM SIZE RO TYPE MOUNTPOINT
xvda    202:0    0   8G  0 disk
└─xvda1 202:1    0   8G  0 part /
xvdb    202:16   0  16G  0 disk
```

format db volume into an xfs filesystem

```
$ sudo mkfs -t xfs /dev/xvdb
meta-data=/dev/xvdb              isize=512    agcount=4, agsize=1048576 blks
         =                       sectsz=512   attr=2, projid32bit=1
         =                       crc=1        finobt=1, sparse=0
data     =                       bsize=4096   blocks=4194304, imaxpct=25
         =                       sunit=0      swidth=0 blks
naming   =version 2              bsize=4096   ascii-ci=0 ftype=1
log      =internal log           bsize=4096   blocks=2560, version=2
         =                       sectsz=512   sunit=0 blks, lazy-count=1
realtime =none                   extsz=4096   blocks=0, rtextents=0
```

make a directory to mount volume to

```
sudo mkdir /database
```

mount volume to directory

```
sudo mount /dev/xvdb /database
```

get the volume block id and use it to permanantly mount to directory

```
sudo blkid
```
example with UUID=19ee2212-7fa0-4c9a-bcbf-cd7019d50fd6 

```
# UUID=b24eb1ea-ab1c-47bd-8542-3fd6059814ae     /           xfs    defaults,noatime  1   1
# UUID=19ee2212-7fa0-4c9a-bcbf-cd7019d50fd6     /database   xfs    defaults,nofail   0   2
```

test the mount is /etc/fstab (no news is good news)

```
sudo mount -a
```

update perms and ownership for database directory

```
sudo chown -R postgres:postgres /database
sudo chmod -R 700 /database
```

#### 4) Create WAL-E Env Var Directory

* IAM demo-user

```
sudo mkdir -p /etc/wal-e/env
sudo chown -R ec2-user:ec2-user /etc/wal-e
echo "INSERT-VALUE-HERE" > /etc/wal-e/env/AWS_ACCESS_KEY_ID
echo "REGION-HERE" > /etc/wal-e/env/AWS_REGION
echo "INSERT-VALUE-HERE" > /etc/wal-e/env/AWS_SECRET_ACCESS_KEY
echo "S3-BUCKET-URL-HERE" > /etc/wal-e/env/WALE_S3_PREFIX
sudo chown -R postgres:postgres /etc/wal-e
sudo chmod -R 755 /etc/wal-e/env
```

helpful to list available backups to make sure wal-e and envdir is setup right

```
sudo su - 
su - postgres
envdir /etc/wal-e/env wal-e backup-list
```

#### 5) initialize the default db just for the sake of getting defualt configs

```
pg_ctl init
cd /var/lib/pgsql
cp /var/lib/pgsql/data/postgresql.conf .
cp /var/lib/pgsql/data/pg_hba.conf .
```

Use these configs to overwrite those that come in from pulling the base backup using wal-e

#### 6) Pull Base Backup from S3 using WAL-E

wrap command in shell script to enable nohup backgrounding in the event of connection timeout

```
mkdir /var/lib/pgsql/scripts
vi /var/lib/pgsql/scripts/wal-e-fetch-backup.sh
```

script contents

```
#!/bin/bash

echo "starting wal-e backup-fetch"

started=`date +%s`

envdir /etc/wal-e/env wal-e backup-fetch --blind-restore /database LATEST

ended=`date +%s`

duration=$((ended - started))

echo "wal-e backup-fetch completed after $duration seconds"
```

run it 

```
cd /var/lib/pgsql/scripts
chmod +x wal-e-fetch-backup.sh
nohup ./wal-e-fetch-backup.sh &
```

#### 7) Update postgresql.conf

pull over default config

```
cd /database
cp /var/lib/pgsql/postgresql.conf .
```

then set the following

```
listen_address = '*'

hot_standby = on

data_directory = '/database'

wal_level = logical

max_wal_senders = 10
max_replication_slots = 10
wal_keep_segments=1000
wal_sender_timeout=60
```

#### 8) update pg_hba.conf to allow for pguser to auth with password and postgres trusted from streaming replica ip

pull over default config

```
cd /database
cp /var/lib/pgsql/pg_hba.conf .
```

then set the following

```
# "local" is for Unix domain socket connections only
local   all             all                                     trust
# IPv4 local connections:
host    pgdb            pguser          0.0.0.0/0               md5
host    all             rds_replication 0.0.0.0/0               md5
host    all             postgres        IP-ADDRESS-HERE/32      trust
host    all             all             127.0.0.1/32            trust
# IPv6 local connections:
host    all             all             ::1/128                 trust
# Allow replication connections from localhost, by a user with the
# replication privilege.
host    replication     postgres        IP-ADDRESS-HERE/32      trust
host    replication     rds_replication 0.0.0.0/0               md5
local   replication     all                                     trust
host    replication     all             127.0.0.1/32            trust
host    replication     all             ::1/128                 trust
```

#### 9) Create recovery.conf to sync the log shipped replica

create file

```
vi /database/recovery.conf
```

put the following in it

```
restore_command = 'envdir /etc/wal-e/env wal-e wal-fetch %f %p'
standby_mode = on
recovery_target_timeline = 'latest'
```

#### 10) Setup Systemd Service and start the DB to initiate recovery

create the service file

```
sudo vi /etc/systemd/system/postgresql.service
```

with the following

```
.include /lib/systemd/system/postgresql.service

[Service]
Environment=PGDATA=/database
```

turn it on

```
sudo systemctl daemon-reload
sudo systemctl start postgresql
sudo systemctl status postgresql
sudo systemctl enable postgresql
```





<hr>

### <a id="log-streamed-replica">Create Streaming Replica (the diasaster saver)</a>


#### 1) Spin up EC2 Instance

- Amazon Linux 2 AMI (t3.medium)
- Default VPC
- Security Group Allowing SSH and Postgres Access
- 16 GB Volume

#### 2) Update Server and Install Linux Package Dependencies


```
sudo yum update -y
sudo amazon-linux-extras install epel postgresql10 -y
sudo yum install postgresql-server postgresql-contrib -y
```

#### 3) Mount Database Volume

see what volumes exists

```
$ lsblk
NAME    MAJ:MIN RM SIZE RO TYPE MOUNTPOINT
xvda    202:0    0   8G  0 disk
└─xvda1 202:1    0   8G  0 part /
xvdb    202:16   0  16G  0 disk
```

format db volume into an xfs filesystem

```
$ sudo mkfs -t xfs /dev/xvdb
meta-data=/dev/xvdb              isize=512    agcount=4, agsize=1048576 blks
         =                       sectsz=512   attr=2, projid32bit=1
         =                       crc=1        finobt=1, sparse=0
data     =                       bsize=4096   blocks=4194304, imaxpct=25
         =                       sunit=0      swidth=0 blks
naming   =version 2              bsize=4096   ascii-ci=0 ftype=1
log      =internal log           bsize=4096   blocks=2560, version=2
         =                       sectsz=512   sunit=0 blks, lazy-count=1
realtime =none                   extsz=4096   blocks=0, rtextents=0
```

make a directory to mount volume to

```
sudo mkdir /database
```

mount volume to directory

```
sudo mount /dev/xvdb /database
```

get the volume block id and use it to permanantly mount to directory

```
sudo blkid
```
example with UUID=19ee2212-7fa0-4c9a-bcbf-cd7019d50fd6 

```
# UUID=b24eb1ea-ab1c-47bd-8542-3fd6059814ae     /           xfs    defaults,noatime  1   1
# UUID=19ee2212-7fa0-4c9a-bcbf-cd7019d50fd6     /database   xfs    defaults,nofail   0   2
```

test the mount is /etc/fstab (no news is good news)

```
sudo mount -a
```

update perms and ownership for database directory

```
sudo chown -R postgres:postgres /database
sudo chmod -R 700 /database
```

#### 4) Initialize the Default Data Directory to Grab Default Configs

```
sudo su -
su - postgres
pg_ctl init
cp data/postgresql.conf .
cp data/pg_hba.conf .
```

#### 5) Pull Physical Base Backup from EC2 Postgres LSR

Create a shell script to wrap the command

```
mkdir /var/lib/pgsql/scripts && cd /var/lib/pgsql/scripts
vi physical_backup.sh
```

with contents

```
#!/bin/bash

echo "starting physical backup"

started=`date +%s`

pg_basebackup -h IP-ADDRESS-HERE -D /database --progress --verbose

ended=`date +%s`

duration=$((ended - started))

echo "physical backup completed after $duration seconds"
```

run it

```
chmod +x physical_backup.sh
nohup ./physical_backup.sh &
```

#### 6) Update postgresql.conf

copy default

```
cd /database
cp /var/lib/pgsql/postgresql.conf .
```

update

```
listen_address = '*'

hot_standby = on

data_directory = '/database'

wal_level = replica

max_logical_replication_workers = 4
max_sync_workers_per_subscription = 2
max_replication_slots = 10
```

#### 7) Update pg_hba.conf to allow for connecting from anywhere

copy default

```
cd /database
cp /var/lib/pgsql/pg_hba.conf .
```

update it

```
host    pgdb            pguser          0.0.0.0/0               md5
```


#### 8) Make recovery.conf

```
standby_mode = on
primary_conninfo = 'host=IP-ADDRESS-HERE port=5432 user=postgres'
recovery_target_timeline = 'latest'
```

#### 9) Setup Systemd Service and Start Postgres to it Syncs as a Replica

 /etc/systemd/system/postgresql.service

```
.include /lib/systemd/system/postgresql.service

[Service]
Environment=PGDATA=/database
```

Start the database

```
systemctl daemon-reload
systemctl start postgresql
systemctl status postgresql
systemctl enable postgresql
```


<hr>

### <a id="aurora-configuration">Configure Aurora Postgres to allow Logical Replication</a>

#### 1) Need to Add Cluster Param Group for Aurora to do Locial Replication


* logical_replication = 1
* Security Group: Postgres-Public-Aurora

#### 2) Create user and db

```
psql ...
CREATE ROLE pguser LOGIN CREATEDB PASSWORD 'develop3r';
GRANT pguser TO postgres;
CREATE DATABASE pgdb OWNER pguser;
```

#### 3) Dump Schema from EC2-Postgres LSR

```
pg_dump -h IP-ADDRESS-HERE -U pguser -d pgdb --schema-only > schema.sql
```

#### 4) Load the Schema into Aurora

```
psql -U postgres -h ... -d pgdb -f schema.sql
```

<hr>

### <a id="promote-ec2-postgres">Promote EC2 Postgres LSR and Switch Heroku App to Promoted DB</a>

#### 1) Turn Heroku App maintenance mode on

```
heroku maintenance:on -a murmuring-chamber-40073
```

#### 2) Promote EC2 Postgres LSR

```
sudo su -
su - postgres
pg_ctl promote -D /database
```

#### 3) Flip Database URL env var and restart

```
heroku config:set AURORA_MASTER_DATABASE_URL=postgres://pguser:develop3r@IP-ADDRESS-HERE:5432/pgdb -a murmuring-chamber-40073
heroku ps:restart -a murmuring-chamber-40073
```

#### 4) Turn off maintenance mode

```
heroku maintenance:off -a murmuring-chamber-40073
```

#### 5) Create a replication user, on EC2 Postgres LSR, to perform Logical Replication with 

```
sudo su -
su - postgres
psql -d pgdb
CREATE ROLE rds_replication REPLICATION LOGIN SUPERUSER PASSWORD 'develop3r';
```


#### 6) Create A Replication Slot on EC2 Postgres LSR (aka Publication)

```
CREATE PUBLICATION big_kahuna FOR ALL TABLES;
```

#### 7) Create A Replication Slot on Aurora Postgres (aka Subscription)

```
psql -U postgres -d pgdb -h .....

CREATE SUBSCRIPTION big_kahuna
CONNECTION 'host=IP-ADDRESS-HERE port=5432 dbname=pgdb user=rds_replication password=develop3r'
PUBLICATION big_kahuna;
```

<hr>

### <a id="aurora-switch">Verify EC2 Postgres is Synced and Switch Heroku App to Aurora Postgres</a>

#### 1) On Master you can check replication status with

```
psql -U postgres -d pgdb -h .....
\x
select * from pg_stat_replication;
```


#### 2) Once synced, turn heroku maintenance mode on

```
heroku maintenance:on -a murmuring-chamber-40073
```

#### 3) On aurora drop the subscription

```
DROP SUBSCRIPTION big_kahuna;
```

#### 4) On Aurora Update the Sequences

* custom sql for alter_sequences.sql

```
psql -U pguser -d pgdb -h AURORA-WRITER-CLUSTER-HERE -f alter_sequences.sql
psql -U pguser -d pgdb -h AURORA-WRITER-CLUSTER-HERE -f check_sequences.sql
```

#### 5) Update AURORA_MASTER_DATABASE_URL Config Var

```
heroku config:set AURORA_MASTER_DATABASE_URL=postgres://pguser:develop3r@AURORA-WRITER-CLUSTER-HERE -a murmuring-chamber-40073
heroku ps:restart -a murmuring-chamber-40073
```


#### 6) Turn off Maintenance Mode

```
heroku maintenance:off -a murmuring-chamber-40073
```

<img src="./oh-yeah.jpg">





