drop table if exists fai;

create table fai (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    shortname TEXT UNIQUE NOT NULL,
    zone TEXT NOT NULL,
    gps TEXT,
    description TEXT,
    services TEXT,
    website TEXT,
    email TEXT,
    irc_server TEXT,
    irc_channel TEXT,
    step INTEGER NOT NULL,
    is_member BOOLEAN DEFAULT 0 NOT NULL, 
    CHECK (is_member IN (0,1)) 
);

INSERT INTO fai VALUES (1, "Aquilenet", "Aquilenet", "Aquitaine", "10:10", "Fournisseur d'accès Internet en Aquitaine", "ADSL", "http://www.aquilenet.fr", "contact@aquilenet.fr", "freenode.net", "#aquilenet", 7, 1);
INSERT INTO fai VALUES (2, "FaiMaison", "FaiMaison", "Nantes", "10:10", "", "ADSL", "http://faimaison.net/", "", "", "", 7, 1);
