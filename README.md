# app-view Dashboards

This is a set of three dashboards to present the data by plots, charts and maps for the Users' Tokens (Android and iOS) and the legacy data that comes from app users for reported EQ and Silent Notifications. The information is stored in two SQLite databases: one contains the users tokens data and the second one contains EQ and Silent Notif. information.
# Users Token Information - dashboard_users
The *sctokenmanager* seiscomp module is in charge of adding/updating/removing the otken info in this database and stores the data within the DB in two main tables: *fcmTokens* and *apnsTokens*. The dashboard named "*dashboard_users.py*" is just a client that reads and presents the data visually. 
## How to run it
It is necessary to have a json file that contains the path to the users token SQLite DB. An example is below:

> dashboard_users.json
> {
>     "database_path": "/Path/to/SQLiteDB/tokens.db"
> }

The json file containing the path to the SQLite DB must be in the same folder where the dashboard_users.py is and its name must be ***dashboard_users.json***.
In order to run it you just need to use python and it will run on port 8050:

> python
> python dashboard_users.py

# EQ info and Silent Notification dashboards
Both dashboards: EQ info (whose python script is *dashboard_events.py*) and Silent Notifications (whose python script is *dashboard_silent.py*) use the same database. The data that contains this database comes from app clients who write the information in the Firestore collections: *eventnotifications* and *silentnotifications*.
## How to run them
In order to run is just necessary to have the path to the SQLite DB in a json file. Below there is an example:

> Filename dashboard_silent.json and dashboard_events.py 
> {
>     "database_path": "/Path/To/SQLiteDB/dashboard.db"
> }

Each dashboard can run independently through the next commands:

> python dashboard_silent.py
> python dashboard_events.py

By default the port on which the dashboards run is 8050. The json file containing the path to the SQLite DB must be in the same folder where the dashboard_silent.py and dashboard_events.py scripts are and their names must be ***dashboard_silent.json*** and ***dashboard_events.json***
# Run the three dashboards at the same time
In order to run the three dashboards, and having just one control by tabs, use the *main.py* script. No need to modify this control script unless you want to change the port. **By default the port that uses this script is 8055**.
## How to run the three dashboards
In order to run the three dashboards just run:

> python main.py

Make sure that the corresponding json files, that contain the SQLite DB paths for the three dashboard, are properly set up for each dashboard (see more details above).


