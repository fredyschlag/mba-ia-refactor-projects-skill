const { db } = require('../database/connection');

class AuditLog {
    static record(action) {
        return new Promise((resolve, reject) => {
            db.run(
                "INSERT INTO audit_logs (action, created_at) VALUES (?, datetime('now'))",
                [action],
                function (err) {
                    if (err) return reject(err);
                    resolve(this.lastID);
                }
            );
        });
    }
}

module.exports = AuditLog;
