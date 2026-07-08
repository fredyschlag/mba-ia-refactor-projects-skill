const { db } = require('../database/connection');

class Enrollment {
    static create(userId, courseId) {
        return new Promise((resolve, reject) => {
            db.run(
                'INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)',
                [userId, courseId],
                function (err) {
                    if (err) return reject(err);
                    resolve(this.lastID);
                }
            );
        });
    }

    static findByUserId(userId) {
        return new Promise((resolve, reject) => {
            db.all('SELECT * FROM enrollments WHERE user_id = ?', [userId], (err, rows) => {
                if (err) return reject(err);
                resolve(rows);
            });
        });
    }

    static deleteByUserId(userId) {
        return new Promise((resolve, reject) => {
            db.run('DELETE FROM enrollments WHERE user_id = ?', [userId], function (err) {
                if (err) return reject(err);
                resolve(this.changes);
            });
        });
    }
}

module.exports = Enrollment;
