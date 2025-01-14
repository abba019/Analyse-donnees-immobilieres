# MIG8110

## Setup

Launch Docker Desktop, and make your current repository the one for
this project.

## Launch

### 1. Check Port Availability

```bash
$ netsat -aon | findstr: 5432       # Windows
$ sudo lsof -iTCP:5432 -sTCP:LISTEN # Linux/Mac
```

If the port is not available, run `sudo kill <PID>`.

### 2. Launch the Containers for the First Time

If this is the first time you work with these containers, you will
need to create and load the database and the datawarehouse first.
Make sure you have all the relevant files in the `create-db/dbfiles`
folder. You can then use the `create-db-dw` docker-compose profile to
do it:
```bash
$ docker-compose --profile create-db-dw up -d --build # to start
$ docker-compose --profile create-db-dw down          # to end
```

### 3. Launch the Containers for all Subsequent Times

Once the database has been loaded, the containers are build to save
it directly into a Docker volume. This means that you do not have to
reload it everytime, you can just write this:
```bash
$ docker-compose up -d # to start
$ docker-compose down  # to end
```

You can now access all the services with these URLs:
1. [dashboard web inteface](http://localhost:8501)
1. [PostgreSQL database](http://localhost:5050)
1. [PostgreSQL management tool](http://localhost:5050)

## Update the Database and the Datawarehouse

The database that you will generate is not automatically refreshed.
Instead, to allow more control over this component, it is upon the
explicit command of the user that it will be updated. To do so, the
containers need to be launched with the `update-db-dw` profile:
```bash
$ docker-compose --profile update-db-dw up -d --build # to start
$ docker-compose --profile update-db-dw down          # to end
```

This will both start the application and update the database and the
datawarehouse.
