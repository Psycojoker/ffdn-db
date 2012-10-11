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

INSERT INTO fai VALUES (1, "Aquilenet", "Aquilenet",  "Aquitaine", "10:10", "Fournisseur d'accès Internet en Aquitaine", "ADSL", "http://www.aquilenet.fr", "contact@aquilenet.fr", "freenode.net", "#aquilenet", 7, 1);
INSERT INTO fai VALUES (2, "FaiMaison", "FaiMaison",  "Nantes", "10:10", "", "ADSL", "http://faimaison.net/", "", "", "", 7, 1);
INSERT INTO fai VALUES (3, "Ilico",     "Ilico",      "Corrèze", "", "", "ADSL", "http://www.ilico.org/", "", "", "", 7, 1);
INSERT INTO fai VALUES (4, "Illyse",    "Illyse",     "Lyon - St Étienne", "", "", "ADSL", "http://www.illyse.net/", "", "", "", 5, 1);
INSERT INTO fai VALUES (5, "Iloth",     "Iloth",      "Hérault", "", "", "ADSL", "http://iloth.net/", "", "", "", 5, 1);
INSERT INTO fai VALUES (6, "Netopi",    "Netopi",     "Seine-et-Marne", "", "", "ADSL", "http://www.netopi.fr/", "", "", "", 6, 1);
INSERT INTO fai VALUES (7, "Rézine",    "Rézine",     "Région grenobloise", "", "", "", "http://www.rezine.org/", "", "", "", 5, 1);
INSERT INTO fai VALUES (8, "Rhizome",   "Rhizome",    "Compiègne (Oise)", "", "", "Wifi d'initiative étudiante", "http://rhizome-fai.net/", "", "", "", 7, 1);
INSERT INTO fai VALUES (9, "French Data Network",     "FDN", "France entière", "", "", "ADSL", "http://www.fdn.fr/", "", "", "", 7, 1);
INSERT INTO fai VALUES (10, "Loraine Data Network",    "LDN", "Lorraine", "", "", "ADSL", "http://ldn-fai.net/", "", "", "", 7, 1);
INSERT INTO fai VALUES (11, "Nice Data Network",       "NDN", "Alpes-Maritimes", "", "", "ADSL", "http://www.ndn-fai.net/", "", "", "", 7, 1);
INSERT INTO fai VALUES (12, "Sallanches Data Network", "SDN", "Sallanches (Haut-Savoie)", "", "", "", "http://www.sdnet.info/", "", "", "", 5, 1);
INSERT INTO fai VALUES (13, "Sames Wireless",  "Sames",       "village de Sames (Pyrénées-Atlantiques)", "", "", "Wifi zone blanche", "http://www.sameswireless.fr/", "", "", "", 7, 1);
INSERT INTO fai VALUES (14, "tetaneutral.net", "ttnn",        "Toulouse", "", "", "ADSL et Wifi en zones blanches et denses", "http://tetaneutral.net/", "", "", "", 7, 1);
INSERT INTO fai VALUES (15, "Franciliens.net", "Franciliens.net", "Île-de-France", "", "", "ADSL et VPN", "http://www.franciliens.net", "", "", "", 7, 1);
