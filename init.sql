DROP TABLE IF EXISTS Users;
DROP TABLE IF EXISTS Forums;
DROP TABLE IF EXISTS Threads;
DROP TABLE IF EXISTS Posts;

CREATE TABLE Users
(
  `UserId` INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
  `Username` TEXT NOT NULL UNIQUE,
  `Password` TEXT NOT NULL
);

CREATE TABLE Forums
(
  `ForumId` INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
  `CreatorId` INTEGER NOT NULL,
  `ForumsName` TEXT NOT NULL UNIQUE,
  FOREIGN KEY(`CreatorId`) REFERENCES `Users`(`UserId`) ON DELETE CASCADE
);

CREATE TABLE Threads
(
  `ThreadId` INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
  `ForumId` INTEGER NOT NULL,
  `CreatorId` INTEGER NOT NULL,
  `ThreadsTitle` TEXT NOT NULL,
  `RecentPostTimeStamp` TEXT NOT NUll,
  FOREIGN KEY(`ForumId`) REFERENCES `Forums`(`ForumId`) ON DELETE CASCADE
);

CREATE INDEX `UserId`
ON `Users`
(
  `UserId` ASC
);

INSERT INTO Users
  (`Username`, `Password`)
VALUES
    ('cameron', 'test'),
    ('brian', 'test'),
    ('elmer', 'test');

INSERT INTO Forums
  (`CreatorId`, `ForumsName`)
VALUES
  (1, 'Forum Test 1'),
  (2, 'Forum Test 2'),
  (3, 'Forum Test 3');

INSERT INTO Threads
  (`ForumId`, `CreatorId`, `ThreadsTitle`, `RecentPostTimeStamp`)
VALUES
  (1, 2, 'Post Test - Author=2 Thread=1', '2018-08-25 05:23:25'), --id=1 'Tue, 02 Sep 2018 15:42:28 GMT' 1535927520
  (1, 1, 'Post Test - Author=1 Thread=1', '2018-08-26 05:23:25'), --id=2  1536100920
  (2, 3, 'Post Test - Author=3 Thread=2','2018-08-24 05:23:25' ), --id=3  1536100920
  (3, 1, 'Post Test - Author=1 Thread=3', '2018-08-26 06:23:25'); --id=4  1536100920
