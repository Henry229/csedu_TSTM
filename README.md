# Environment
## Server OS
Ubuntu 18.04 LTS
## Core Software & Library
### Python
Python 3.6
### Database
PostgreSQL 11
### Http Server
nginx

# Installation
### Update system
```
$ sudo apt update

```
### Install kernel compile tools
```
$ sudo apt install gcc make perl
```
### Install Guest Addition Tools
1. Use Devices >  Insert Guest Additions CD Image...
2. Proceed install by following on screen instructions
### Install packages
```
$ sudo apt-get -y install python3-venv python3-dev python3-wheel python3-distutils python3-pip php php7.2-dom
```
### Git
```
$ sudo apt install git
And a GUI git client
$ sudo apt install git-cola
OR
$ wget https://release.gitkraken.com/linux/gitkraken-amd64.deb
$ sudo apt install ./gitkraken-amd64.deb
```
### PostgreSQL
```
# add the repository
sudo tee /etc/apt/sources.list.d/pgdg.list <<END
deb http://apt.postgresql.org/pub/repos/apt/ bionic-pgdg main
END

# get the signing key and import it
wget https://www.postgresql.org/media/keys/ACCC4CF8.asc
sudo apt-key add ACCC4CF8.asc

# fetch the metadata from the new repo
sudo apt-get update

# Install PostgreSql 11
$ sudo apt install postgresql-11 postgresql-server-dev-11

# Install DB manager
$ sudo apt install pgadmin3
OR
https://dbeaver.io/download/ 

# Create an admin user
$ sudo -u postgres createuser --interactive --pwprompt
Enter name of role to add: dbadmin
Enter password for new role: 
Enter it again: 
Shall the new role be a superuser? (y/n) y

# Create DB and a user
$ sudo -u postgres psql
psql (10.8 (Ubuntu 10.8-0ubuntu0.18.04.1))
Type "help" for help.

postgres=# create database tailored;
CREATE DATABASE
postgres=# create user tailored with encrypted password 'P@ssword1';
CREATE ROLE
postgres=# grant all privileges on database tailored to tailored;
GRANT
postgres=# \c tailored
postgres=# CREATE EXTENSION IF NOT EXISTS tablefunc;

# Create a readonly user for debugging
-- Change to the db
postgres=# \c tailored;
-- Create a group
postgres=# CREATE ROLE readaccess;
-- Grant access to existing tables
postgres=# GRANT USAGE ON SCHEMA public TO readaccess;
postgres=# GRANT SELECT ON ALL TABLES IN SCHEMA public TO readaccess;
-- Grant access to future tables
postgres=# ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO readaccess;
-- Create a final user with password
postgres=# CREATE USER tailored_readonly WITH PASSWORD 'P@ssword1';
postgres=# GRANT readaccess TO tailored_readonly;

postgres=# \q
```
#### Enable password login
```
$ sudo find / -name pg_hba.conf
$ sudo vim ./var/lib/pgsql/data/pg_hba.conf

Change Ident to md5 for the local connection
# IPv4 local connections:
host    all             all             127.0.0.1/32            md5
```
#### SQLALCHEMY_DATABASE_URI 
```
postgresql+psycopg2://tailored:P@ssword1@localhost/tailored
```
# Application
#### Clone the repo
```
$ git clone https://flashcharity_org@bitbucket.org/csedutailored/tailored.git
```
#### Create Python venv
```
$ cd csedu
~/csedu$ python3 -m venv venv
~/csedu$ source venv/bin/activate
(venv) ~/csedu$ pip install -r requirements/dev.txt
```
#### Run the app
```
(venv) ~/csedu$ export FLASK_APP=tailored.py
(venv) ~/csedu$ export SQLALCHEMY_DATABASE_URI=postgresql+psycopg2://tailored:P@ssword1@localhost/tailored

(venv) ~/csedu$ flask db init
(venv) ~/csedu$ flask db migrate
(venv) ~/csedu$ flask db upgrade
(venv) ~/csedu$ flask deploy

(venv) ~/csedu$ export TEMP=/tmp

Run the app on port 8000
(venv) ~/csedu$ gunicorn -b localhost:8000 -w 4 csedu:app
```
# Production Deployment
### gunicorn
```
(venv) ~/csedu$ pip install gunicorn
```
### Supervisor
```
$ sudo apt install postfix supervisor
$ sudo vim /etc/supervisord.d/csedu.ini
[program:csedu]
command=/home/ec2-user/csedu/venv/bin/gunicorn -b 0.0.0.0:8000 -w 4 csedu:app
directory=/home/ec2-user/csedu
environment=FLASK_DEBUG="1",TEMP="/tmp",QT_QPA_PLATFORM="offscreen"
user=ec2-user
autostart=true
autorestart=true
stopasgroup=true
killasgroup=true

```
### nginx
```
$ vi /etc/nginx/nginx.conf
# Upload size
        client_max_body_size 50M;
$ sudo apt install nginx
$ sudo ufw app list
$ sudo ufw allow 'Nginx HTTP'
$ sudo ufw status
$ sudo systemctl status nginx
$ sudo systemctl start supervisord
```
