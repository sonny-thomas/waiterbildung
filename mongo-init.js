const dbName = process.env.DATABASE_NAME;
const username = process.env.MONGO_INITDB_ROOT_USERNAME;
const password = process.env.MONGO_INITDB_ROOT_PASSWORD;

db = db.getSiblingDB(dbName);

db.createUser({
    user: username,
    pwd: password,
    roles: [
        {
            role: "readWrite",
            db: dbName
        }
    ]
});
