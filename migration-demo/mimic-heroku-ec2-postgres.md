
# Switch Rando Numba Heroku DB to a EC2 Postgres 10 Instance Pushing WAL/ Backups to S3

## Explain Heroku Architecture and Problematic Contraints

-- Heroku utilizes Dynos (aka EC2 Instances) for apps

-- Heroku utilizes EC2 + Postgres Instances for their Heroku Postgres Service
  -- will not allow access to DB superuser or replication user (so how to get data?)
  -- upon several requests they agreeded to "ship" physical backup and WAL to S3 which I can make a Log Shipped Replica Hot Standby from

## Demo RandoNumba App running on Heroku but with an EC2 + Postgres 10 I control to emulate Heroku

https://murmuring-chamber-40073.herokuapp.com/

or 

```
heroku open -a murmuring-chamber-40073
```


## Demo How to use WAL-E to Ship Physical Base Backups and WAL to S3

1. Spin up EC2 with Dedicated Database Volume (Heroku-Postgres)

- Amazon Linux 2 AMI (t3.medium)
- Default VPC
- Security Group Allowing SSH and Postgres Access
- 16 GB Volume


2. Update Server / Install Dependencies

```
sudo yum update -y
sudo amazon-linux-extras install epel -y
sudo amazon-linux-extras install postgresql10 -y
sudo yum install postgresql-server postgresql-contrib python3 lzop pv -y
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
sudo python3 get-pip.py
sudo python3 -m pip install envdir wal-e[aws]
``` 

3. Mount Database Volume

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

4. Create WAL-E Env Var Directory

pg-migration-demo 
access_key_id = AKIAYLT5Q4YRSONEZMOH
secret_key = 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

```
sudo mkdir -p /etc/wal-e/env
sudo chown -R ec2-user:ec2-user /etc/wal-e
echo "AKIAYLT5Q4YRSONEZMOH" > /etc/wal-e/env/AWS_ACCESS_KEY_ID
echo "us-east-2" > /etc/wal-e/env/AWS_REGION
echo "2dYoyT/RI49Z42pq8caGp8Y0yzzqW7vBGHCdAfel" > /etc/wal-e/env/AWS_SECRET_ACCESS_KEY
echo "s3://wal-3-trial/heroku-postgres-demo" > /etc/wal-e/env/WALE_S3_PREFIX
sudo chown -R postgres:postgres /etc/wal-e
sudo chmod -R 755 /etc/wal-e/env
```

5. Initialize Postgres Pointing to Database Directory

```
sudo su -
su - postgres
pg_ctl init -D /database
```

6. Setup Custom Systemd Service for Postgres

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

7. create app user and database

```
sudo su -
su - postgres
createuser -e -l --pwprompt pguser
createdb -e --owner=pguser pgdb
psql -d pgdb -f dbdump.sql
```

8. Update postgresql.conf config

```
listen_addresses = '*'
wal_level = replica
archive_mode = on
archive_command = 'envdir /etc/wal-e/env wal-e wal-push %p'
archive_timeout = 60
```

9. Update pg_hba.conf

```
host    pgdb            pguser          0.0.0.0/0               md5
```

10. Remove Existing DB Addon in Heroku

```
$ heroku addons -a murmuring-chamber-40073                                                       

Add-on                                      Plan       Price  State  
──────────────────────────────────────────  ─────────  ─────  ───────
heroku-postgresql (postgresql-cubed-92606)  hobby-dev  free   created
 └─ as DATABASE
$ heroku addons:destroy DATABASE -a murmuring-chamber-40073      
```

11. Update heroku app and restart

flip on maintenance mode

```
heroku maintenance:on -a murmuring-chamber-40073 
```

update the DATABASE_URL config to the new database (EC2 heroku-postgres)

```
heroku config:set DATABASE_URL=postgres://pguser:develop3r@3.128.133.211:5432/pgdb -a murmuring-chamber-40073
heroku ps:restart -a murmuring-chamber-40073
```

turn maintenance off

```
heroku maintenance:off -a murmuring-chamber-40073 
```

12. push a base backup

vi /

```
mkdir /var/lib/pgsql/scripts
vi /var/lib/pgsql/scripts/wal-e-push-backup.sh
chmod +x /var/lib/pgsql/scripts/wal-e-push-backup.sh
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
nohup ./wal-e-push-backup.sh &
```













## Create Log Shipped Replica

1. Spin up EC2 Instance

- Amazon Linux 2 AMI (t3.medium)
- Default VPC
- Security Group Allowing SSH and Postgres Access
- 16 GB Volume

2. Update Server and Install Linux Package Dependencies

ssh -i ~/.ssh/ga-us-east-2.pem ec2-user@ec2-postgres-lsr

```
sudo yum update -y
sudo amazon-linux-extras install epel postgresql10 -y
sudo yum install postgresql-server postgresql-contrib python3 lzop -y
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
sudo python3 get-pip.py
sudo python3 -m pip install envdir wal-e[aws]
```

3. Mount Database Volume

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

4. Create WAL-E Env Var Directory

pg-migration-demo 
access_key_id = AKIAYLT5Q4YRSONEZMOH
secret_key = 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

```
sudo mkdir -p /etc/wal-e/env
sudo chown -R ec2-user:ec2-user /etc/wal-e
echo "AKIAYLT5Q4YRSONEZMOH" > /etc/wal-e/env/AWS_ACCESS_KEY_ID
echo "us-east-2" > /etc/wal-e/env/AWS_REGION
echo "2dYoyT/RI49Z42pq8caGp8Y0yzzqW7vBGHCdAfel" > /etc/wal-e/env/AWS_SECRET_ACCESS_KEY
echo "s3://wal-3-trial/heroku-postgres-demo" > /etc/wal-e/env/WALE_S3_PREFIX
sudo chown -R postgres:postgres /etc/wal-e
sudo chmod -R 755 /etc/wal-e/env
```

helpful to list available backups to make sure wal-e and envdir is setup right

```
sudo su - 
su - postgres
envdir /etc/wal-e/env wal-e backup-list
```

6. initialize the default db just for the sake of getting defualt configs

```
pg_ctl init
cd /var/lib/pgsql
cp /var/lib/pgsql/data/postgresql.conf .
cp /var/lib/pgsql/data/pg_hba.conf .
```

Use these configs to overwrite those that come in from pulling the base backup using wal-e

7. Pull Base Backup from S3 using WAL-E

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

8. Update postgresql.conf

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

9. update pg_hba.conf to allow for pguser to auth with password and postgres trusted from streaming replica ip (3.138.210.34)

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
host    all             postgres        3.138.210.34/32         trust
host    all             all             127.0.0.1/32            trust
# IPv6 local connections:
host    all             all             ::1/128                 trust
# Allow replication connections from localhost, by a user with the
# replication privilege.
host    replication     postgres        3.138.210.34/32         trust
local   replication     all                                     trust
host    replication     all             127.0.0.1/32            trust
host    replication     all             ::1/128                 trust
```

10. Create recovery.conf to sync the log shipped replica

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

11. Setup Systemd Service and start the DB to initiate recovery

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







## Create Streaming Replica for the Event that 


1. Spin up EC2 Instance

- Amazon Linux 2 AMI (t3.medium)
- Default VPC
- Security Group Allowing SSH and Postgres Access
- 16 GB Volume

2. Update Server and Install Linux Package Dependencies

ssh -i ~/.ssh/ga-us-east-2.pem ec2-user@ec2-postgres-sr

```
sudo yum update -y
sudo amazon-linux-extras install epel postgresql10 -y
sudo yum install postgresql-server postgresql-contrib -y
```

3. Mount Database Volume

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

4. Initialize the Default Data Directory to Grab Default Configs

```
sudo su -
su - postgres
pg_ctl init
cp data/postgresql.conf .
cp data/pg_hba.conf .
```

5. Pull Physical Base Backup from EC2 Postgres LSR

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

pg_basebackup -h 3.137.115.23 -D /database --progress --verbose

ended=`date +%s`

duration=$((ended - started))

echo "physical backup completed after $duration seconds"
```

run it

```
chmod +x physical_backup.sh
nohup ./physical_backup.sh &
```

6. Update postgresql.conf

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

7. Update pg_hba.conf to allow for connecting from anywhere

copy default

```
cd /database
cp /var/lib/pgsql/pg_hba.conf .
```

update it

```
host    pgdb            pguser          0.0.0.0/0               md5
```


7. Make recovery.conf

```
standby_mode = on
primary_conninfo = 'host=3.137.115.23 port=5432 user=postgres'
recovery_target_timeline = 'latest'
```

8. Setup Systemd Service and Start Postgres to it Syncs as a Replica

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


## Fire Up Aurora Postgres and Configure to allow Logical Replication

1. Need to Add Cluster Param Group for Aurora to do Locial Replication


* logical_replication = 1
* Security Group: Postgres-Public-Aurora

2. Create user and db

```
psql ...
CREATE ROLE pguser LOGIN CREATEDB PASSWORD 'develop3r';
GRANT pguser TO postgres;
CREATE DATABASE pgdb OWNER pguser;
```

3. Dump Schema from EC2-Postgres LSR

```
pg_dump -h 3.137.115.23 -U pguser -d pgdb --schema-only > schema.sql
```

4. Load the Schema into Aurora

```
psql -U postgres -h ... -d pgdb -f schema.sql
```

## Promote EC2 Postgres LSR and Switch Heroku App to Promoted DB

1. Turn Heroku App maintenance mode on

```
heroku maintenance:on -a murmuring-chamber-40073
```

2. Promote EC2 Postgres LSR

```
ssh -i ~/.ssh/ga-us-east-2.pem ec2-user@ec2-postgres-lsr
sudo su -
su - postgres
pg_ctl promote -D /database
```

3. Flip Database URL

## Verify Ec2 Postgres is Synced and Switch Heroku App to Aurora Postgres






